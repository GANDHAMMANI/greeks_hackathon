import google.generativeai as genai
import json
from datetime import datetime

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def analyze_cv(self, cv_text, candidate_name):
        """
        Analyze a CV using Gemini API to extract structured information
        
        Args:
            cv_text: The text content of the CV
            candidate_name: The name of the candidate
            
        Returns:
            dict: Structured information extracted from the CV
        """
        try:
            prompt = f"""
            I need you to analyze this CV/resume for {candidate_name} and extract the following information in JSON format:
            
            1. Skills (technical and soft skills as a list of strings)
            2. Years of experience (total professional experience as a number)
            3. Education level (highest degree: e.g., "Bachelor's", "Master's", "PhD", etc.)
            4. Key technologies or tools the candidate is proficient with (as a list of strings)
            5. Previous job titles (as a list of strings)
            
            Return ONLY the JSON object without any explanations or markdown. Format should be:
            {{
                "skills": ["skill1", "skill2", ...],
                "experience_years": X,
                "education": "Highest degree",
                "technologies": ["tech1", "tech2", ...],
                "job_titles": ["title1", "title2", ...]
            }}
            
            Here is the CV text:
            {cv_text}
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract the JSON object from the response
            try:
                # Try to parse the response as JSON
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text (in case there's additional text)
                import re
                json_match = re.search(r'({.*})', response.text.replace('\n', ''), re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    raise Exception("Failed to extract JSON from response")
            
            # Add timestamp
            result['timestamp'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            print(f"Error analyzing CV with Gemini API: {str(e)}")
            # Return a minimal structure in case of error
            return {
                "skills": [],
                "experience_years": 0,
                "education": "Unknown",
                "technologies": [],
                "job_titles": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_job_description(self, job_title, job_description):
        """
        Analyze a job description using Gemini API to extract requirements
        
        Args:
            job_title: The title of the job
            job_description: The text of the job description
            
        Returns:
            dict: Structured requirements extracted from the job description
        """
        try:
            prompt = f"""
            I need you to analyze this job description for a {job_title} position and extract the following information in JSON format:
            
            1. Required skills (as a list of strings)
            2. Preferred/nice-to-have skills (as a list of strings)
            3. Years of experience required (as a number, use the minimum if a range is specified)
            4. Education level required (e.g., "Bachelor's", "Master's", "PhD", etc.)
            5. Key technologies or tools mentioned (as a list of strings)
            
            Return ONLY the JSON object without any explanations or markdown. Format should be:
            {{
                "required_skills": ["skill1", "skill2", ...],
                "preferred_skills": ["skill1", "skill2", ...],
                "experience_years": X,
                "education_level": "Required degree",
                "technologies": ["tech1", "tech2", ...]
            }}
            
            Here is the job description:
            {job_description}
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract the JSON object from the response
            try:
                # Try to parse the response as JSON
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the text (in case there's additional text)
                import re
                json_match = re.search(r'({.*})', response.text.replace('\n', ''), re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    raise Exception("Failed to extract JSON from response")
            
            # Add timestamp
            result['timestamp'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            print(f"Error analyzing job description with Gemini API: {str(e)}")
            # Return a minimal structure in case of error
            return {
                "required_skills": [],
                "preferred_skills": [],
                "experience_years": 0,
                "education_level": "Unknown",
                "technologies": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }