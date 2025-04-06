# api_debug.py

from utils.api_clients import get_linkedin_data, get_github_data
import json

def test_linkedin_api():
    """Test LinkedIn API integration"""
    print("\n=== Testing LinkedIn API Integration ===\n")
    
    test_profiles = [
        "https://www.linkedin.com/in/satyanadella/",  # Microsoft CEO
        # Add other profiles you want to test
    ]
    
    for profile_url in test_profiles:
        print(f"Fetching data for: {profile_url}")
        try:
            result = get_linkedin_data(profile_url)
            
            # Check if there's an error
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print("✅ Successfully fetched LinkedIn data:")
                # Print key information
                print(f"  Name: {result.get('name', 'N/A')}")
                print(f"  Headline: {result.get('headline', 'N/A')}")
                print(f"  Location: {result.get('location', 'N/A')}")
                
                # Print number of skills
                skills = result.get('skills', [])
                print(f"  Skills: {len(skills)} found")
                if skills:
                    print(f"  Sample skills: {', '.join(skills[:5])}")
                
                # Print number of experiences
                experiences = result.get('experience', [])
                print(f"  Experience entries: {len(experiences)}")
                
                # Print the full response in JSON format
                print("\nFull response:")
                print(json.dumps(result, indent=2))
        
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        print("\n" + "-" * 50 + "\n")

def test_github_api():
    """Test GitHub API integration"""
    print("\n=== Testing GitHub API Integration ===\n")
    
    test_profiles = [
        "https://github.com/torvalds",  # Linus Torvalds
        # Add other profiles you want to test
    ]
    
    for profile_url in test_profiles:
        print(f"Fetching data for: {profile_url}")
        try:
            result = get_github_data(profile_url)
            
            # Check if there's an error
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print("✅ Successfully fetched GitHub data:")
                # Print key information
                print(f"  Name: {result.get('name', 'N/A')}")
                print(f"  Bio: {result.get('bio', 'N/A')}")
                print(f"  Location: {result.get('location', 'N/A')}")
                print(f"  Public repos: {result.get('public_repos', 'N/A')}")
                print(f"  Followers: {result.get('followers', 'N/A')}")
                
                # Print repository information
                repos = result.get('repos', [])
                print(f"  Repositories: {len(repos)} fetched")
                if repos:
                    print("\n  Top repositories:")
                    for i, repo in enumerate(repos[:3]):
                        print(f"    {i+1}. {repo.get('name', 'N/A')}: {repo.get('stars', 0)} stars, {repo.get('language', 'N/A')}")
                
                # Print the full response in JSON format
                print("\nFull response:")
                print(json.dumps(result, indent=2))
        
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        print("\n" + "-" * 50 + "\n")

if __name__ == "__main__":
    print("API Integration Test Script")
    print("==========================\n")
    
    # Test LinkedIn API
    test_linkedin_api()
    
    # Test GitHub API
    test_github_api()