from datetime import datetime

class JDAnalyzer:
    def __init__(self, generate_completion_fn, mysql_connector):
        """
        Initialize the Job Description Analyzer
        
        Args:
            generate_completion_fn: Function that calls the Groq API
            mysql_connector: Connector to the MySQL database
        """
        self.generate_completion = generate_completion_fn
        self.mysql_connector = mysql_connector
    
    def analyze_job_description(self, job_title, job_description):
        """
        Analyze a job description using the Groq API
        
        Args:
            job_title: The title of the job
            job_description: The text of the job description to analyze
            
        Returns:
            dict: The analysis results
        """
        # Create the prompt for Groq
        messages = [
            {
                "role": "system",
                "content": "You are an expert HR recruiter specializing in job description analysis. Extract key information from job descriptions."
            },
            {
                "role": "user",
                "content": f"Analyze the following job description for '{job_title}':\n\n{job_description}\n\nExtract the following information: required skills, required experience, education requirements, responsibilities, and key qualifications. Format your response as JSON."
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
                "error": response.get("error", "Unknown error analyzing job description"),
                "timestamp": datetime.now().isoformat()
            }
        
        # Return the analysis results
        return {
            "analysis": response["content"],
            "model": "llama-3.3-70b-versatile",
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_job(self, job_id):
        """
        Analyze a job description and store the results
        
        Args:
            job_id: The ID of the job to analyze
            
        Returns:
            dict: The analysis results
        """
        # Get job data from MySQL
        job_data = self.mysql_connector.get_job_by_id(job_id)
        
        if not job_data:
            return {
                "success": False,
                "error": f"Job with ID {job_id} not found"
            }
        
        # Extract job title and description
        job_title = job_data.get('job_title', 'Unknown Position')
        job_description = job_data.get('job_description', '')
        
        if not job_description:
            return {
                "success": False,
                "error": "No job description found for this job"
            }
        
        # Analyze job description using Groq API
        analysis_result = self.analyze_job_description(job_title, job_description)
        
        # Store analysis results in MySQL
        storage_success = self.mysql_connector.store_job_analysis(
            job_id, analysis_result
        )
        
        return {
            "success": storage_success,
            "job_id": job_id,
            "job_title": job_title,
            "analysis_result": analysis_result
        }
    
    def analyze_all_jobs(self, limit=None):
        """
        Analyze all job descriptions and store the results
        
        Args:
            limit: Optional limit on number of jobs to analyze
            
        Returns:
            dict: Summary of the analysis results
        """
        # Get all jobs from MySQL
        all_jobs = self.mysql_connector.get_all_jobs()
        
        if limit:
            all_jobs = all_jobs[:limit]
        
        results = {
            "total": len(all_jobs),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for job in all_jobs:
            result = self.analyze_job(job['id'])
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                "job_id": job['id'],
                "job_title": job['job_title'],
                "success": result['success'],
                "error": result.get('error', None)
            })
        
        return results