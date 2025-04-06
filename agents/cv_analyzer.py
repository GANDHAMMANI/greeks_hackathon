from datetime import datetime

class CVAnalyzer:
    def __init__(self, generate_completion_fn, neo4j_connector):
        """
        Initialize the CV Analyzer
        
        Args:
            generate_completion_fn: Function that calls the Groq API
            neo4j_connector: Connector to the Neo4j database
        """
        self.generate_completion = generate_completion_fn
        self.neo4j_connector = neo4j_connector
    
    def analyze_cv(self, cv_text, candidate_name):
        """
        Analyze a CV using the Groq API
        
        Args:
            cv_text: The text of the CV to analyze
            candidate_name: The name of the candidate
            
        Returns:
            dict: The analysis results
        """
        # Create the prompt for Groq
        messages = [
            {
                "role": "system",
                "content": "You are an expert HR recruiter and CV analyzer. Extract key information from the CV."
            },
            {
                "role": "user",
                "content": f"Analyze the following CV for {candidate_name}:\n\n{cv_text}\n\nExtract the following information: skills, experience, education, certifications, and career highlights. Format your response as JSON."
            }
        ]
        
        # Call Groq API
        response = self.generate_completion(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=1024,
            stream=False
        )
        
        if not response["success"]:
            return {
                "error": response.get("error", "Unknown error analyzing CV"),
                "timestamp": datetime.now().isoformat()
            }
        
        # Return the analysis results
        return {
            "analysis": response["content"],
            "model": "llama-3.3-70b-versatile",
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_candidate(self, candidate_id):
        """
        Analyze a candidate's CV and store the results
        
        Args:
            candidate_id: The ID of the candidate to analyze
            
        Returns:
            dict: The analysis results
        """
        # Get candidate data from Neo4j
        candidate_data = self.neo4j_connector.get_candidate_by_id(candidate_id)
        
        if not candidate_data:
            return {
                "success": False,
                "error": f"Candidate with ID {candidate_id} not found"
            }
        
        # Extract CV text and candidate name
        cv_text = candidate_data.get('cv_text', '')
        candidate_name = candidate_data.get('name', 'Unknown Candidate')
        
        if not cv_text:
            return {
                "success": False,
                "error": "No CV text found for this candidate"
            }
        
        # Analyze CV using Groq API
        analysis_result = self.analyze_cv(cv_text, candidate_name)
        
        # Store analysis results in Neo4j
        storage_success = self.neo4j_connector.store_candidate_analysis(
            candidate_id, analysis_result
        )
        
        return {
            "success": storage_success,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "analysis_result": analysis_result
        }
    
    def analyze_all_candidates(self, limit=None):
        """
        Analyze all candidates' CVs and store the results
        
        Args:
            limit: Optional limit on number of candidates to analyze
            
        Returns:
            dict: Summary of the analysis results
        """
        # Get all candidates from Neo4j
        all_candidates = self.neo4j_connector.get_all_candidates()
        
        if limit:
            all_candidates = all_candidates[:limit]
        
        results = {
            "total": len(all_candidates),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for candidate in all_candidates:
            result = self.analyze_candidate(candidate['id'])
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                "candidate_id": candidate['id'],
                "candidate_name": candidate['name'],
                "success": result['success'],
                "error": result.get('error', None)
            })
        
        return results