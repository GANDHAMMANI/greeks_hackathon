import requests
import json
import os
import re
from urllib.parse import urlparse

def get_linkedin_data(linkedin_url):
    """
    Get data from LinkedIn profile using RapidAPI
    
    Args:
        linkedin_url: URL of LinkedIn profile
    
    Returns:
        Dictionary with LinkedIn profile data
    """
    # Extract username from URL
    parsed_url = urlparse(linkedin_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2 or path_parts[0] != 'in':
        return {"url": linkedin_url, "error": "Invalid LinkedIn URL format"}
    
    username = path_parts[1]
    
    # RapidAPI endpoint for LinkedIn
    url = "https://linkedin-data-api.p.rapidapi.com/profile"
    
    # RapidAPI credentials
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": "8c1df99e82mshe4bfa5155ace027p1c9102jsn300e741a9ea3"
    }
    
    # Query parameters
    querystring = {"username": username}
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        
        # Extract relevant fields
        profile_data = {
            "url": linkedin_url,
            "username": username,
            "name": data.get("full_name", ""),
            "headline": data.get("headline", ""),
            "summary": data.get("summary", ""),
            "location": data.get("location", ""),
            "connections": data.get("connections", 0),
            "skills": []
        }
        
        # Extract skills if available
        if "skills" in data and isinstance(data["skills"], list):
            profile_data["skills"] = [skill.get("name", "") for skill in data["skills"]]
            
        # Extract experience if available
        if "experiences" in data and isinstance(data["experiences"], list):
            profile_data["experience"] = []
            for exp in data["experiences"]:
                experience_entry = {
                    "title": exp.get("title", ""),
                    "company": exp.get("company", ""),
                    "description": exp.get("description", ""),
                    "date_range": exp.get("date_range", "")
                }
                profile_data["experience"].append(experience_entry)
        
        # Extract education if available
        if "education" in data and isinstance(data["education"], list):
            profile_data["education"] = []
            for edu in data["education"]:
                education_entry = {
                    "school": edu.get("school", ""),
                    "degree": edu.get("degree", ""),
                    "field_of_study": edu.get("field_of_study", ""),
                    "date_range": edu.get("date_range", "")
                }
                profile_data["education"].append(education_entry)
        
        return profile_data
    
    except Exception as e:
        # Return minimal data with error
        return {
            "url": linkedin_url,
            "username": username,
            "error": str(e)
        }

def get_linkedin_company_posts(company_username, start=0, count=10):
    """
    Get company posts from LinkedIn using RapidAPI
    
    Args:
        company_username: Company username on LinkedIn
        start: Starting index for pagination
        count: Number of posts to retrieve
        
    Returns:
        Dictionary with company posts data
    """
    url = "https://linkedin-data-api.p.rapidapi.com/get-company-posts"
    
    headers = {
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com",
        "x-rapidapi-key": "8c1df99e82mshe4bfa5155ace027p1c9102jsn300e741a9ea3"
    }
    
    querystring = {
        "username": company_username,
        "start": start
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        return {
            "company": company_username,
            "error": str(e)
        }
    

# Add this to your existing utils/api_clients.py file

import requests
import json
import os
from urllib.parse import urlparse

def get_github_data(github_url):
    """
    Get data from GitHub profile using GitHub API
    
    Args:
        github_url: URL of GitHub profile
    
    Returns:
        Dictionary with GitHub profile data
    """
    # Extract username from URL
    parsed_url = urlparse(github_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if not path_parts:
        return {"url": github_url, "error": "Invalid GitHub URL format"}
    
    username = path_parts[0]
    
    # GitHub API endpoint
    url = f"https://api.github.com/users/{username}"
    
    # GitHub token for higher rate limits (optional)
    token = os.getenv("GITHUB_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        # Get basic user info
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        # Get repositories
        repos_url = user_data.get("repos_url")
        repos_response = requests.get(repos_url, headers=headers)
        repos_response.raise_for_status()
        repos_data = repos_response.json()
        
        # Extract relevant fields
        profile_data = {
            "url": github_url,
            "username": username,
            "name": user_data.get("name", ""),
            "bio": user_data.get("bio", ""),
            "location": user_data.get("location", ""),
            "email": user_data.get("email", ""),
            "followers": user_data.get("followers", 0),
            "following": user_data.get("following", 0),
            "public_repos": user_data.get("public_repos", 0),
            "contributions": user_data.get("contributions", 0),  # This requires scraping the contributions graph
            "repos": []
        }
        
        # Add repository information
        for repo in repos_data[:10]:  # Limit to 10 repos
            profile_data["repos"].append({
                "name": repo.get("name", ""),
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "url": repo.get("html_url", "")
            })
        
        return profile_data
    
    except Exception as e:
        # Return minimal data with error
        return {
            "url": github_url,
            "username": username if 'username' in locals() else "",
            "error": str(e)
        }