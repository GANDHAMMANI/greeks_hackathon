import numpy as np
from datetime import datetime
import json
import os

class MatchingEngine:
    def __init__(self, neo4j_connector, mysql_connector, generate_completion_fn, cache_dir="./.cache/matches"):
        self.neo4j_connector = neo4j_connector
        self.mysql_connector = mysql_connector
        self.generate_completion = generate_completion_fn
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # Matching weights for different criteria
        self.weights = {
            'skills': 0.5,
            'experience': 0.3,
            'education': 0.2
        }
        
        # Education level mapping for comparison
        self.education_levels = {
            'high school': 1,
            'diploma': 2,
            'associate': 2,
            'bachelor': 3,
            "bachelor's": 3,
            'undergraduate': 3,
            'master': 4,
            "master's": 4,
            'phd': 5,
            'doctorate': 5
        }
    
    def _get_cache_path(self, candidate_id, job_id):
        """Get path to cache file for a specific match"""
        return os.path.join(self.cache_dir, f"match_{candidate_id}_{job_id}.json")
    
    def _check_match_cache(self, candidate_id, job_id):
        """Check if we have a cached match result"""
        cache_path = self._get_cache_path(candidate_id, job_id)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def _save_match_cache(self, candidate_id, job_id, result):
        """Save match result to cache"""
        cache_path = self._get_cache_path(candidate_id, job_id)
        try:
            with open(cache_path, 'w') as f:
                json.dump(result, f)
        except Exception as e:
            print(f"Error saving match cache: {str(e)}")
    
    def analyze_job_description(self, job_title, job_description, force_cache=False):
        """
        Analyze a job description using LLM
        
        Args:
            job_title: The title of the job
            job_description: The text of the job description
            force_cache: Whether to force use of cache even if API is available
            
        Returns:
            dict: The analysis results
        """
        # Create the prompt for LLM
        messages = [
            {
                "role": "system",
                "content": "You are an expert HR recruiter. Extract key information from job descriptions."
            },
            {
                "role": "user",
                "content": f"Analyze the following job description for '{job_title}':\n\n{job_description}\n\nExtract the following key information as JSON: required_skills (as a list), experience_years (as a number), education_level (as text), and responsibilities (as a list)."
            }
        ]
        
        # Call LLM API
        response = self.generate_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            stream=False,
            force_cache=force_cache
        )
        
        if not response.get("success", False):
            return {
                "error": response.get("error", "Unknown error analyzing job description"),
                "required_skills": [],
                "experience_years": 0,
                "education_level": ""
            }
        
        # Try to parse as JSON
        try:
            content = response.get("content", "{}")
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            # If it's not valid JSON, extract what we can using simple parsing
            content = response.get("content", "")
            # Simple extraction logic for non-JSON response
            import re
            
            skills = []
            skills_match = re.search(r'"required_skills"\s*:.*?\[(.*?)\]', content, re.DOTALL)
            if skills_match:
                skills_text = skills_match.group(1)
                skills = [s.strip().strip('"\'') for s in skills_text.split(',')]
            
            experience = 0
            exp_match = re.search(r'"experience_years"\s*:\s*(\d+)', content)
            if exp_match:
                experience = int(exp_match.group(1))
            
            education = ""
            edu_match = re.search(r'"education_level"\s*:\s*"(.*?)"', content)
            if edu_match:
                education = edu_match.group(1)
            
            return {
                "required_skills": skills,
                "experience_years": experience,
                "education_level": education
            }
    
    def analyze_cv(self, cv_text, candidate_name, force_cache=False):
        """
        Analyze a CV using LLM
        
        Args:
            cv_text: The text of the CV
            candidate_name: The name of the candidate
            force_cache: Whether to force use of cache even if API is available
            
        Returns:
            dict: The analysis results
        """
        # Create the prompt for LLM
        messages = [
            {
                "role": "system",
                "content": "You are an expert HR recruiter. Extract key information from CVs."
            },
            {
                "role": "user",
                "content": f"Analyze the following CV for {candidate_name}:\n\n{cv_text}\n\nExtract the following key information as JSON: skills (as a list), experience_years (as a number), and education (as text)."
            }
        ]
        
        # Call LLM API
        response = self.generate_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            stream=False,
            force_cache=force_cache
        )
        
        if not response.get("success", False):
            return {
                "error": response.get("error", "Unknown error analyzing CV"),
                "skills": [],
                "experience_years": 0,
                "education": ""
            }
        
        # Try to parse as JSON
        try:
            content = response.get("content", "{}")
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            # If it's not valid JSON, extract what we can using simple parsing
            content = response.get("content", "")
            # Simple extraction logic for non-JSON response
            import re
            
            skills = []
            skills_match = re.search(r'"skills"\s*:.*?\[(.*?)\]', content, re.DOTALL)
            if skills_match:
                skills_text = skills_match.group(1)
                skills = [s.strip().strip('"\'') for s in skills_text.split(',')]
            
            experience = 0
            exp_match = re.search(r'"experience_years"\s*:\s*(\d+)', content)
            if exp_match:
                experience = int(exp_match.group(1))
            
            education = ""
            edu_match = re.search(r'"education"\s*:\s*"(.*?)"', content)
            if edu_match:
                education = edu_match.group(1)
            
            return {
                "skills": skills,
                "experience_years": experience,
                "education": education
            }
    
    def _get_education_level_score(self, required_level, candidate_level):
        """Calculate match score for education levels"""
        if not required_level or not candidate_level:
            return 1.0  # Default if no information
        
        # Convert to lowercase for matching
        required_lower = required_level.lower()
        candidate_lower = candidate_level.lower()
        
        # Get numeric levels
        required_value = 0
        candidate_value = 0
        
        for key, value in self.education_levels.items():
            if key in required_lower:
                required_value = max(required_value, value)
            if key in candidate_lower:
                candidate_value = max(candidate_value, value)
        
        # If no match found, default to values
        if required_value == 0:
            required_value = 2  # Default to Associate level if unknown
        if candidate_value == 0:
            candidate_value = 2  # Default to Associate level if unknown
        
        # Calculate score
        if candidate_value >= required_value:
            return 1.0
        elif candidate_value == required_value - 1:
            return 0.7
        else:
            return 0.4
    
    def _get_experience_score(self, required_years, candidate_years):
        """Calculate match score for years of experience"""
        if required_years is None or candidate_years is None:
            return 1.0  # Default if no information
            
        try:
            required = float(required_years)
            candidate = float(candidate_years)
            
            if candidate >= required:
                return 1.0
            elif candidate >= required * 0.7:
                return 0.8
            elif candidate >= required * 0.5:
                return 0.5
            else:
                return 0.3
        except (ValueError, TypeError):
            return 0.5  # Default if conversion fails
    
    def _get_skills_score(self, required_skills, candidate_skills):
        """Calculate match score for skills"""
        if not required_skills or not candidate_skills:
            return 0.5  # Default score if no skills data
        
        # Convert lists to strings if needed
        if isinstance(required_skills, list):
            required_skills = ', '.join(required_skills)
        if isinstance(candidate_skills, list):
            candidate_skills = ', '.join(candidate_skills)
        
        # Convert to string to be safe
        required_skills = str(required_skills).lower()
        candidate_skills = str(candidate_skills).lower()
        
        # Check for direct keyword matches
        required_keywords = set(required_skills.replace(',', ' ').split())
        candidate_keywords = set(candidate_skills.replace(',', ' ').split())
        
        if not required_keywords:
            return 0.5
            
        # Calculate direct keyword match ratio
        matches = len(required_keywords.intersection(candidate_keywords))
        direct_match_score = matches / len(required_keywords) if required_keywords else 0
        
        # For more sophisticated matching, we could add TF-IDF similarity
        # But for hackathon purposes, direct matching is sufficient
        
        return direct_match_score
    
    def calculate_match_score(self, job_analysis, candidate_analysis):
        """
        Calculate match score between job and candidate analyses
        
        Args:
            job_analysis: Analysis of job requirements
            candidate_analysis: Analysis of candidate skills
            
        Returns:
            dict: Match scores and details
        """
        # Calculate individual match scores
        skills_score = self._get_skills_score(
            job_analysis.get('required_skills', []), 
            candidate_analysis.get('skills', [])
        )
        
        experience_score = self._get_experience_score(
            job_analysis.get('experience_years', 0),
            candidate_analysis.get('experience_years', 0)
        )
        
        education_score = self._get_education_level_score(
            job_analysis.get('education_level', ''),
            candidate_analysis.get('education', '')
        )
        
        # Calculate weighted overall score
        overall_score = (
            skills_score * self.weights['skills'] +
            experience_score * self.weights['experience'] +
            education_score * self.weights['education']
        )
        
        return {
            'overall_score': round(overall_score, 2),
            'skills_score': round(skills_score, 2),
            'experience_score': round(experience_score, 2),
            'education_score': round(education_score, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    def match_candidate_to_job(self, candidate_id, job_id, use_cache=True, force_cache=False):
        """
        Match a specific candidate to a specific job
        
        Args:
            candidate_id: ID of the candidate
            job_id: ID of the job
            use_cache: Whether to check for cached match results
            force_cache: Whether to force use of cache even if API is available
            
        Returns:
            dict: Match results with scores
        """
        # Check if we have a cached match result
        if use_cache:
            cached_result = self._check_match_cache(candidate_id, job_id)
            if cached_result:
                print(f"Using cached match result for candidate {candidate_id} and job {job_id}")
                return cached_result
        
        # Get candidate data from Neo4j
        candidate_data = self.neo4j_connector.get_candidate_by_id(candidate_id)
        
        if not candidate_data:
            return {
                "success": False,
                "error": f"Candidate with ID {candidate_id} not found"
            }
        
        # Get job data from MySQL
        job_data = self.mysql_connector.get_job_by_id(job_id)
        
        if not job_data:
            return {
                "success": False,
                "error": f"Job with ID {job_id} not found"
            }
        
        # Get job analysis
        job_analysis = self.analyze_job_description(
            job_data.get('job_title', ''), 
            job_data.get('job_description', ''),
            force_cache=force_cache
        )
        
        # Get candidate analysis
        candidate_analysis = self.analyze_cv(
            candidate_data.get('cv_text', ''),
            candidate_data.get('name', ''),
            force_cache=force_cache
        )
        
        # Calculate match scores
        match_scores = self.calculate_match_score(job_analysis, candidate_analysis)
        
        # Prepare result
        result = {
            "success": True,
            "candidate_id": candidate_id,
            "candidate_name": candidate_data.get('name', 'Unknown'),
            "job_id": job_id,
            "job_title": job_data.get('job_title', 'Unknown'),
            "overall_score": match_scores['overall_score'],
            "skills_score": match_scores['skills_score'],
            "experience_score": match_scores['experience_score'],
            "education_score": match_scores['education_score']
        }
        
        # Store results in cache
        self._save_match_cache(candidate_id, job_id, result)
        
        # Store match results in database
        self.mysql_connector.store_match_results(
            candidate_id, job_id, match_scores['overall_score'], match_scores
        )
        
        return result
    
    def match_candidate_to_all_jobs(self, candidate_id, batch_size=5, force_cache=False):
        """Match a candidate to all available jobs with batch processing
        
        Args:
            candidate_id: ID of the candidate
            batch_size: Number of jobs to process per batch
            force_cache: Whether to force use of cache even if API is available
            
        Returns:
            dict: Match results for all jobs
        """
        # Get all jobs
        all_jobs = self.mysql_connector.get_all_jobs()
        
        results = {
            "candidate_id": candidate_id,
            "total_jobs": len(all_jobs),
            "matches": [],
            "pending_jobs": 0
        }
        
        # Process jobs in batches
        for i in range(0, len(all_jobs), batch_size):
            batch = all_jobs[i:i+batch_size]
            print(f"Processing job batch {i//batch_size + 1} of {(len(all_jobs) // batch_size) + 1} ({len(batch)} jobs)")
            
            for job in batch:
                # First check if we already have this match cached
                cached_result = self._check_match_cache(candidate_id, job['id'])
                if cached_result:
                    if cached_result.get("success", False):
                        results['matches'].append(cached_result)
                    continue
                
                match_result = self.match_candidate_to_job(
                    candidate_id, job['id'], use_cache=True, force_cache=force_cache
                )
                
                if match_result.get('success', False):
                    results['matches'].append(match_result)
        
        # Sort matches by score (descending)
        results['matches'].sort(key=lambda x: x['overall_score'], reverse=True)
        
        return results
    
    def match_all_candidates_to_job(self, job_id, batch_size=5, force_cache=False):
        """Match all candidates to a specific job with batch processing
        
        Args:
            job_id: ID of the job
            batch_size: Number of candidates to process per batch  
            force_cache: Whether to force use of cache even if API is available
            
        Returns:
            dict: Match results for all candidates
        """
        # Get all candidates
        all_candidates = self.neo4j_connector.get_all_candidates()
        
        results = {
            "job_id": job_id,
            "total_candidates": len(all_candidates),
            "matches": [],
            "pending_candidates": 0
        }
        
        # Process candidates in batches
        for i in range(0, len(all_candidates), batch_size):
            batch = all_candidates[i:i+batch_size]
            print(f"Processing candidate batch {i//batch_size + 1} of {(len(all_candidates) // batch_size) + 1} ({len(batch)} candidates)")
            
            for candidate in batch:
                # First check if we already have this match cached
                cached_result = self._check_match_cache(candidate['id'], job_id)
                if cached_result:
                    if cached_result.get("success", False):
                        results['matches'].append(cached_result)
                    continue
                
                match_result = self.match_candidate_to_job(
                    candidate['id'], job_id, use_cache=True, force_cache=force_cache
                )
                
                if match_result.get('success', False):
                    results['matches'].append(match_result)
        
        # Sort matches by score (descending)
        results['matches'].sort(key=lambda x: x['overall_score'], reverse=True)
        
        return results