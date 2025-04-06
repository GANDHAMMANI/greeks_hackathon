# db_integration.py
import os
import mysql.connector
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class MySQLConnection:
    def __init__(self):
        """Initialize MySQL connection using environment variables or default values"""
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DATABASE", "job")
        self.connection = None
    
    def connect(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("MySQL connection established successfully")
            return self.connection
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL database: {err}")
            return None
    
    def close(self):
        """Close the MySQL connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")
    
    def get_all_jobs(self):
        """Retrieve all jobs from the job_description table"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM job_description"
        cursor.execute(query)
        jobs = cursor.fetchall()
        cursor.close()
        return jobs
    
    def get_job_by_id(self, job_id):
        """Retrieve a specific job by ID"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM job_description WHERE id = %s"
        cursor.execute(query, (job_id,))
        job = cursor.fetchone()
        cursor.close()
        return job
    
    def get_job_titles_for_dropdown(self):
        """Retrieve all job titles for dropdown menu"""
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT id, `job title` FROM job_description"  # Note the backticks for column with space
        cursor.execute(query)
        job_titles = cursor.fetchall()
        cursor.close()
        return job_titles

class Neo4jConnection:
    def __init__(self):
        """Initialize Neo4j connection using environment variables"""
        self.uri = os.getenv("NEO4J_URI", "neo4j+s://aaa466f7.databases.neo4j.io")
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "7aVotGMFzl62FgbDKqFU7tunpMJOyHPxWPHTiyrWnxw")
        self.driver = None
    
    def connect(self):
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) AS count")
                count = result.single()["count"]
                print(f"Neo4j connection established successfully. Database contains {count} nodes.")
            return self.driver
        except Exception as e:
            print(f"Error connecting to Neo4j database: {e}")
            return None
    
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")
    
    def setup_database(self):
        """Setup the Neo4j database with constraints and indexes"""
        if not self.driver:
            self.connect()
        
        with self.driver.session() as session:
            # Create constraints for uniqueness
            constraints = [
                # Candidate constraints
                """CREATE CONSTRAINT candidate_email_unique IF NOT EXISTS
                   FOR (c:Candidate) REQUIRE c.email IS UNIQUE""",
                
                # Job constraints
                """CREATE CONSTRAINT job_id_unique IF NOT EXISTS
                   FOR (j:Job) REQUIRE j.job_id IS UNIQUE""",
                
                # Skill constraints
                """CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
                   FOR (s:Skill) REQUIRE s.name IS UNIQUE"""
            ]
            
            # Create indexes for faster querying
            indexes = [
                """CREATE INDEX candidate_name IF NOT EXISTS
                   FOR (c:Candidate) ON (c.name)""",
                
                """CREATE INDEX job_title IF NOT EXISTS
                   FOR (j:Job) ON (j.title)"""
            ]
            
            # Execute all constraints and indexes
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"Error creating constraint: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"Error creating index: {e}")
            
            print("Neo4j database setup completed")
    
    def sync_jobs_from_mysql(self, mysql_connection):
        """
        Sync jobs from MySQL to Neo4j
        
        Args:
            mysql_connection: MySQLConnection instance
        """
        if not self.driver:
            self.connect()
        
        jobs = mysql_connection.get_all_jobs()
        with self.driver.session() as session:
            for job in jobs:
                # Update these lines to match your actual column names
                session.run("""
                    MERGE (j:Job {job_id: $job_id})
                    SET j.title = $job_title,
                        j.description = $job_description,
                        j.updated_at = datetime()
                """, job_id=str(job["id"]), 
                    job_title=job["job title"],  # Note the space instead of underscore
                    job_description=job["job_description"])
            
            print(f"Synced {len(jobs)} jobs from MySQL to Neo4j")


class CandidateManager:
    """Manages candidate data in Neo4j database"""
    
    def __init__(self, neo4j_driver):
        """Initialize with Neo4j driver"""
        self.driver = neo4j_driver
    
    def store_candidate(self, form_data, resume_text, linkedin_data=None, github_data=None):
        """
        Store candidate data from form submission with LLM-based parsing
        
        Args:
            form_data: Dictionary with form data (name, email, etc.)
            resume_text: Extracted text from resume PDF
            linkedin_data: Optional LinkedIn data
            github_data: Optional GitHub data
            
        Returns:
            Candidate ID
        """
        from utils.pdf_parser import extract_structured_info_with_llm
        from groq import Groq
        import os
        
        # Initialize LLM client
        llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Extract structured information from resume text using LLM
        structured_info = extract_structured_info_with_llm(resume_text, llm_client)
        
        with self.driver.session() as session:
            # Create candidate node
            result = session.run("""
                CREATE (c:Candidate {
                    id: randomUUID(),
                    name: $name,
                    email: $email,
                    phone: $phone,
                    resume_text: $resume_text,
                    created_at: datetime()
                })
                RETURN c.id as candidate_id
            """, 
                name=form_data.get("name", ""),
                email=form_data.get("email", ""),
                phone=form_data.get("phone", ""),
                resume_text=resume_text)
            
            record = result.single()
            if not record:
                return None
            
            candidate_id = record["candidate_id"]
            
            # Add skills from resume
            skills = structured_info.get("skills", [])
            for skill in skills:
                if not skill or len(skill.strip()) < 2:
                    continue
                    
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    MERGE (s:Skill {name: $skill_name})
                    ON CREATE SET s.created_at = datetime()
                    CREATE (c)-[r:HAS_SKILL {created_at: datetime()}]->(s)
                """, 
                    candidate_id=candidate_id,
                    skill_name=skill)
            
            # Add education from resume
            education_entries = structured_info.get("education", [])
            for edu in education_entries:
                if not edu or not isinstance(edu, dict):
                    continue
                    
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    MERGE (u:University {name: $university})
                    
                    CREATE (e:Education {
                        id: randomUUID(),
                        degree: $degree,
                        field: $field,
                        start_date: $start_date,
                        end_date: $end_date,
                        gpa: $gpa,
                        created_at: datetime()
                    })
                    
                    CREATE (c)-[:HAS_EDUCATION]->(e)
                    CREATE (e)-[:AT_UNIVERSITY]->(u)
                """, 
                    candidate_id=candidate_id,
                    university=edu.get("university", "Unknown"),
                    degree=edu.get("degree", ""),
                    field=edu.get("field", ""),
                    start_date=edu.get("start_date", ""),
                    end_date=edu.get("end_date", ""),
                    gpa=str(edu.get("gpa", "")))
            
            # Add experience from resume
            experience_entries = structured_info.get("experience", [])
            for exp in experience_entries:
                if not exp or not isinstance(exp, dict):
                    continue
                    
                # Get responsibilities
                responsibilities = exp.get("responsibilities", [])
                if isinstance(responsibilities, str):
                    responsibilities = [responsibilities]
                
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    MERGE (co:Company {name: $company})
                    
                    CREATE (e:Experience {
                        id: randomUUID(),
                        title: $title,
                        start_date: $start_date,
                        end_date: $end_date,
                        is_current: $is_current,
                        description: $description,
                        created_at: datetime()
                    })
                    
                    CREATE (c)-[:HAS_EXPERIENCE]->(e)
                    CREATE (e)-[:AT_COMPANY]->(co)
                    
                    WITH e, $responsibilities as responsibilities
                    UNWIND responsibilities as responsibility
                    WHERE responsibility <> ''
                    CREATE (r:Responsibility {description: responsibility})
                    CREATE (e)-[:INCLUDES]->(r)
                """, 
                    candidate_id=candidate_id,
                    company=exp.get("company", "Unknown"),
                    title=exp.get("title", ""),
                    start_date=exp.get("start_date", ""),
                    end_date=exp.get("end_date", ""),
                    is_current=exp.get("is_current", False),
                    description=exp.get("description", ""),
                    responsibilities=responsibilities)
            
            # Link to job application
            if "job_id" in form_data:
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    MATCH (j:Job {job_id: $job_id})
                    CREATE (c)-[a:APPLIED_FOR {
                        date: datetime(),
                        status: 'Applied'
                    }]->(j)
                """, candidate_id=candidate_id, job_id=form_data["job_id"])
            
            # Store LinkedIn data if available
            if linkedin_data and "url" in linkedin_data:
                linkedin_url = linkedin_data.get("url", "")
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    SET c.linkedin_url = $linkedin_url
                """, candidate_id=candidate_id, linkedin_url=linkedin_url)
                
                # Store structured LinkedIn data if available
                if not linkedin_data.get("error"):
                    self._store_linkedin_data(candidate_id, linkedin_data)
            
            # Store GitHub data if available
            if github_data and "url" in github_data:
                github_url = github_data.get("url", "")
                session.run("""
                    MATCH (c:Candidate {id: $candidate_id})
                    SET c.github_url = $github_url
                """, candidate_id=candidate_id, github_url=github_url)
                
                # Store structured GitHub data if available
                if not github_data.get("error"):
                    self._store_github_data(candidate_id, github_data)
            
            # Get contact info from structured_info
            contact_info = structured_info.get("contact", {})
            if contact_info:
                # Update missing fields
                update_fields = {}
                
                if (not form_data.get("email") or form_data.get("email") == "") and contact_info.get("email"):
                    update_fields["email"] = contact_info["email"]
                
                if (not form_data.get("phone") or form_data.get("phone") == "") and contact_info.get("phone"):
                    update_fields["phone"] = contact_info["phone"]
                
                if contact_info.get("linkedin") and not linkedin_data:
                    update_fields["linkedin_url"] = contact_info["linkedin"]
                
                if contact_info.get("github") and not github_data:
                    update_fields["github_url"] = contact_info["github"]
                
                # Update candidate if any new fields were found
                if update_fields:
                    update_query = "MATCH (c:Candidate {id: $candidate_id}) SET "
                    update_query += ", ".join([f"c.{key} = ${key}" for key in update_fields])
                    
                    # Add candidate_id to parameters
                    update_fields["candidate_id"] = candidate_id
                    
                    session.run(update_query, **update_fields)
            
            return candidate_id
    def _store_linkedin_data(self, candidate_id, linkedin_data):
        """Store LinkedIn profile data"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Candidate {id: $candidate_id})
                CREATE (l:LinkedInProfile {
                    id: randomUUID(),
                    url: $url,
                    extracted_at: datetime()
                })
                CREATE (c)-[:HAS_PROFILE]->(l)
                
                // Store additional LinkedIn data
                SET l.headline = $headline,
                    l.summary = $summary,
                    l.location = $location,
                    l.connections = $connections
            """, 
                candidate_id=candidate_id,
                url=linkedin_data.get("url", ""),
                headline=linkedin_data.get("headline", ""),
                summary=linkedin_data.get("summary", ""),
                location=linkedin_data.get("location", ""),
                connections=linkedin_data.get("connections", 0))
    
    def _store_github_data(self, candidate_id, github_data):
        """Store GitHub profile data"""
        with self.driver.session() as session:
            # Create GitHub profile node with primitive properties only
            session.run("""
                MATCH (c:Candidate {id: $candidate_id})
                CREATE (g:GitHubProfile {
                    id: randomUUID(),
                    username: $username,
                    url: $url,
                    repos_count: $repos_count,
                    followers: $followers,
                    following: $following,
                    contributions: $contributions,
                    bio: $bio,
                    extracted_at: datetime()
                })
                CREATE (c)-[:HAS_GITHUB]->(g)
            """, 
                candidate_id=candidate_id,
                username=github_data.get("username", ""),
                url=github_data.get("url", ""),
                repos_count=github_data.get("public_repos", 0),
                followers=github_data.get("followers", 0),
                following=github_data.get("following", 0),
                contributions=github_data.get("contributions", 0),
                bio=github_data.get("bio", ""))
            
            # If there are repositories, store them as separate nodes
            if "repos" in github_data and isinstance(github_data["repos"], list):
                for repo in github_data["repos"]:
                    # Skip if repo is not a dictionary or doesn't have a name
                    if not isinstance(repo, dict) or "name" not in repo:
                        continue
                        
                    session.run("""
                        MATCH (c:Candidate {id: $candidate_id})-[:HAS_GITHUB]->(g:GitHubProfile)
                        WHERE g.username = $username
                        
                        CREATE (r:Repository {
                            id: randomUUID(),
                            name: $name,
                            description: $description,
                            language: $language,
                            stars: $stars,
                            forks: $forks,
                            url: $url,
                            created_at: datetime()
                        })
                        
                        CREATE (g)-[:HAS_REPOSITORY]->(r)
                    """,
                        candidate_id=candidate_id,
                        username=github_data.get("username", ""),
                        name=repo.get("name", ""),
                        description=repo.get("description", ""),
                        language=repo.get("language", ""),
                        stars=repo.get("stars", 0),
                        forks=repo.get("forks", 0),
                        url=repo.get("url", ""))
    
    # In your llm_matching.py file or wherever your LLM matching code is located
    def _store_llm_evaluation(self, candidate_id, job_id, evaluation):
        """Store the LLM evaluation results in Neo4j"""
        with self.driver.session() as session:
            session.run("""
                MATCH (c:Candidate {id: $candidate_id})
                MATCH (j:Job {job_id: $job_id})
                
                // Create or update the MATCHES relationship
                MERGE (c)-[m:MATCHES]->(j)
                SET m.llm_score = $score,
                    m.llm_category = $category,
                    m.llm_strengths = $strengths,
                    m.llm_gaps = $gaps,
                    m.llm_recommendations = $recommendations,
                    m.score = $score,  // Set the regular score to match the LLM score
                    m.category = $category,  // Also update the regular category
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

class MatchingEngine:
    """Matches candidates to jobs using Neo4j graph algorithms"""
    
    def __init__(self, neo4j_driver):
        """Initialize with Neo4j driver"""
        self.driver = neo4j_driver
    
    def match_candidate_to_job(self, candidate_id, job_id):
        """
        Calculate match score between candidate and job
        
        Args:
            candidate_id: Candidate's ID
            job_id: Job's ID
            
        Returns:
            Dictionary with match details and score
        """
        with self.driver.session() as session:
            result = session.run("""
                // Match candidate and job
                MATCH (c:Candidate {id: $candidate_id})
                MATCH (j:Job {job_id: $job_id})
                
                // Calculate match (simplified algorithm)
                WITH c, j,
                     // Extract keywords from resume text (simplified)
                     split(toLower(c.resume_text), ' ') AS resumeWords,
                     // Extract keywords from job description (simplified)
                     split(toLower(j.description), ' ') AS jobWords
                
                WITH c, j, resumeWords, jobWords,
                     [w IN resumeWords WHERE w IN jobWords] AS matchedWords
                
                // Calculate match score (simple count-based method)
                WITH c, j, matchedWords,
                     size(matchedWords) * 1.0 / size(jobWords) AS rawScore,
                     size(matchedWords) AS matchCount,
                     size(jobWords) AS totalKeywords
                
                // Apply scoring logic (simplified)
                WITH c, j, matchedWords, rawScore, matchCount, totalKeywords,
                     CASE
                         WHEN rawScore > 0.8 THEN 'Excellent Match'
                         WHEN rawScore > 0.6 THEN 'Good Match'
                         WHEN rawScore > 0.4 THEN 'Moderate Match'
                         ELSE 'Low Match'
                     END AS matchCategory
                
                // Create or update match relationship
                MERGE (c)-[m:MATCHES]->(j)
                SET m.score = rawScore,
                    m.match_count = matchCount,
                    m.total_keywords = totalKeywords,
                    m.category = matchCategory,
                    m.updated_at = datetime()
                
                RETURN m.score AS match_score,
                       m.category AS match_category,
                       m.match_count AS match_count,
                       m.total_keywords AS total_keywords
            """, candidate_id=candidate_id, job_id=job_id)
            
            record = result.single()
            if record:
                return dict(record)
            return None
    
    def get_best_matches_for_job(self, job_id, limit=10):
        """
        Get best candidate matches for a specific job
        
        Args:
            job_id: Job's ID
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidates with match scores
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Candidate)-[m:MATCHES]->(j:Job {job_id: $job_id})
                RETURN c.id AS candidate_id,
                       c.name AS name,
                       c.email AS email,
                       m.score AS match_score,
                       m.category AS match_category
                ORDER BY m.score DESC
                LIMIT $limit
            """, job_id=job_id, limit=limit)
            
            return [dict(record) for record in result]
    
    def get_all_candidates_for_job(self, job_id):
        """
        Get all candidates who applied for a specific job
        
        Args:
            job_id: Job's ID
            
        Returns:
            List of candidates with application status
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Candidate)-[a:APPLIED_FOR]->(j:Job {job_id: $job_id})
                OPTIONAL MATCH (c)-[m:MATCHES]->(j)
                RETURN c.id AS candidate_id,
                       c.name AS name,
                       c.email AS email,
                       a.status AS application_status,
                       a.date AS application_date,
                       COALESCE(m.score, 0) AS match_score,
                       COALESCE(m.category, 'Not Evaluated') AS match_category
                ORDER BY m.score DESC
            """, job_id=job_id)
            
            return [dict(record) for record in result]


# Function to initialize database connections and setup
def initialize_databases():
    """Initialize and connect to both databases"""
    # Connect to MySQL
    mysql_conn = MySQLConnection()
    mysql_conn.connect()
    
    # Connect to Neo4j and set up schema
    neo4j_conn = Neo4jConnection()
    neo4j_conn.connect()
    neo4j_conn.setup_database()
    
    # Sync job data from MySQL to Neo4j
    neo4j_conn.sync_jobs_from_mysql(mysql_conn)
    
    return mysql_conn, neo4j_conn


# Example usage
if __name__ == "__main__":
    # Initialize databases
    mysql_conn, neo4j_conn = initialize_databases()
    
    # Create instances of helper classes
    candidate_manager = CandidateManager(neo4j_conn.driver)
    matching_engine = MatchingEngine(neo4j_conn.driver)
    
    # Close connections when done
    mysql_conn.close()
    neo4j_conn.close()