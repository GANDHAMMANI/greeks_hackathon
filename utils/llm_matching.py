# llm_matching.py

import os
from groq import Groq
import json

class LLMMatchingEngine:
    """Enhanced matching engine using LLM for unstructured data analysis"""
    
    def __init__(self, neo4j_driver):
        """Initialize with Neo4j driver and Groq client"""
        self.driver = neo4j_driver
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "gemma2-9b-it"  # Can be configured based on needs
    
    def evaluate_candidate_for_job(self, candidate_id, job_id, include_raw_response=False):
        """
        Use LLM to evaluate candidate for a specific job
        
        Args:
            candidate_id: Candidate's ID
            job_id: Job's ID
            include_raw_response: Whether to include the raw LLM response
            
        Returns:
            Dictionary with match details and score
        """
        # Get candidate and job data
        candidate_data = self._get_candidate_data(candidate_id)
        job_data = self._get_job_data(job_id)
        
        if not candidate_data or not job_data:
            return {"error": "Could not retrieve candidate or job data"}
        
        # Format the prompt for the LLM
        prompt = self._create_evaluation_prompt(candidate_data, job_data)
        
        # Call the LLM
        try:
            response = self._call_llm(prompt)
            
            # Parse the LLM response
            parsed_response = self._parse_llm_response(response)
            
            # Store the evaluation in Neo4j
            self._store_llm_evaluation(candidate_id, job_id, parsed_response)
            
            # Return the evaluation results
            result = {
                "candidate_id": candidate_id,
                "job_id": job_id,
                "match_score": parsed_response.get("overall_score", 0),
                "match_category": parsed_response.get("match_category", "Not evaluated"),
                "strengths": parsed_response.get("strengths", []),
                "gaps": parsed_response.get("gaps", []),
                "recommendations": parsed_response.get("recommendations", [])
            }
            
            # Include raw response if requested
            if include_raw_response:
                result["raw_llm_response"] = response
                
            return result
            
        except Exception as e:
            return {"error": f"LLM evaluation failed: {str(e)}"}
    
    def _get_candidate_data(self, candidate_id):
        """Retrieve comprehensive candidate data from Neo4j"""
        with self.driver.session() as session:
            # Query to get candidate data including resume, LinkedIn, and GitHub
            result = session.run("""
                MATCH (c:Candidate {id: $candidate_id})
                OPTIONAL MATCH (c)-[:HAS_PROFILE]->(l:LinkedInProfile)
                OPTIONAL MATCH (c)-[:HAS_GITHUB]->(g:GitHubProfile)
                RETURN c, l, g
            """, candidate_id=candidate_id)
            
            record = result.single()
            if not record:
                return None
                
            # Extract candidate details
            candidate = record["c"]
            linkedin = record["l"] if "l" in record and record["l"] is not None else {}
            github = record["g"] if "g" in record and record["g"] is not None else {}
            
            # Return comprehensive candidate data
            return {
                "id": candidate["id"],
                "name": candidate.get("name", ""),
                "email": candidate.get("email", ""),
                "phone": candidate.get("phone", ""),
                "resume_text": candidate.get("resume_text", ""),
                "linkedin": dict(linkedin) if linkedin else {},
                "github": dict(github) if github else {}
            }
    
    def _get_job_data(self, job_id):
        """Retrieve job data from Neo4j"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (j:Job {job_id: $job_id})
                RETURN j
            """, job_id=job_id)
            
            record = result.single()
            if not record:
                return None
                
            job = record["j"]
            return {
                "id": job["job_id"],
                "title": job.get("title", ""),
                "description": job.get("description", "")
            }
    
    def _create_evaluation_prompt(self, candidate_data, job_data):
        """
        Create a detailed prompt for the LLM to evaluate the candidate
        
        The prompt structure is critical for getting good results
        """
        prompt = f"""You are an expert AI recruitment assistant tasked with evaluating how well a candidate matches a job. 
        
# Job Details:
Title: {job_data['title']}
Description: {job_data['description']}

# Candidate Information:
Name: {candidate_data['name']}
Resume Text: {candidate_data['resume_text']}
"""

        # Add LinkedIn data if available
        if candidate_data.get('linkedin'):
            linkedin = candidate_data['linkedin']
            prompt += f"""
## LinkedIn Profile:
Headline: {linkedin.get('headline', 'N/A')}
Summary: {linkedin.get('summary', 'N/A')}
Skills: {', '.join(linkedin.get('skills', []))}
Experience: {json.dumps(linkedin.get('experience', []), indent=2)}
Education: {json.dumps(linkedin.get('education', []), indent=2)}
"""

        # Add GitHub data if available
        if candidate_data.get('github'):
            github = candidate_data['github']
            prompt += f"""
## GitHub Profile:
Username: {github.get('username', 'N/A')}
Repositories: {github.get('public_repos', 'N/A')}
Bio: {github.get('bio', 'N/A')}
Top Repositories: {json.dumps(github.get('repos', [])[:5], indent=2)}
"""

        # Add evaluation instructions
        prompt += """
# Evaluation Task:
Analyze how well the candidate's qualifications match the job requirements. Provide:

1. Skills match: Identify which skills from the job description are present in the candidate's profile.
2. Experience match: Evaluate if the candidate's experience aligns with the job requirements.
3. Education match: Determine if the candidate's education is suitable for the position.
4. Overall match: Calculate an overall match score from 0 to 1 (0 = no match, 1 = perfect match).
5. Match category: Categorize as "Excellent Match" (>0.8), "Good Match" (>0.6), "Moderate Match" (>0.4), or "Low Match".
6. Strengths: List the candidate's key strengths for this position.
7. Gaps: Identify missing skills or qualifications.
8. Recommendations: Suggest how the candidate could improve their qualifications.

Format your response as a JSON object with these keys: skills_match, experience_match, education_match, overall_score, match_category, strengths, gaps, and recommendations.
"""

        return prompt
    
    def _call_llm(self, prompt):
        """Call the LLM with the given prompt"""
        messages = [{"role": "user", "content": prompt}]
        
        completion = self.groq_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,  # Lower temperature for more consistent results
            max_tokens=1024,
        )
        
        return completion.choices[0].message.content
    
    def _parse_llm_response(self, response_text):
        """
        Parse the LLM response into a structured format
        
        Returns a dictionary with the evaluation results
        """
        try:
            # Try to parse as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON portion
            try:
                # Look for JSON-like structure
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    return json.loads(json_str)
            except:
                pass
            
            # Fallback to manual parsing
            return {
                "overall_score": 0.5,  # Default middle score
                "match_category": "Evaluation failed",
                "strengths": ["Failed to parse LLM response"],
                "gaps": ["Failed to parse LLM response"],
                "recommendations": ["Retry evaluation"]
            }
    
    def _store_llm_evaluation(self, candidate_id, job_id, evaluation):
        """Store the LLM evaluation results in Neo4j"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Candidate {id: $candidate_id})
                MATCH (j:Job {job_id: $job_id})
                
                MERGE (c)-[m:MATCHES]->(j)
                SET m.llm_score = $score,
                    m.llm_category = $category,
                    m.llm_strengths = $strengths,
                    m.llm_gaps = $gaps,
                    m.llm_recommendations = $recommendations,
                    m.updated_at = datetime()
            """, 
                candidate_id=candidate_id,
                job_id=job_id,
                score=evaluation.get("overall_score", 0),
                category=evaluation.get("match_category", ""),
                strengths=evaluation.get("strengths", []),
                gaps=evaluation.get("gaps", []),
                recommendations=evaluation.get("recommendations", [])
            )
    
    def get_best_matches_for_job(self, job_id, limit=10):
        """
        Get best candidate matches for a specific job based on LLM evaluation
        
        Args:
            job_id: Job's ID
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidates with match scores
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Candidate)-[m:MATCHES]->(j:Job {job_id: $job_id})
                WHERE m.llm_score IS NOT NULL
                RETURN c.id AS candidate_id,
                       c.name AS name,
                       c.email AS email,
                       m.llm_score AS match_score,
                       m.llm_category AS match_category,
                       m.llm_strengths AS strengths,
                       m.llm_gaps AS gaps
                ORDER BY m.llm_score DESC
                LIMIT $limit
            """, job_id=job_id, limit=limit)
            
            return [dict(record) for record in result]