# app.py - Main Flask application

from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from werkzeug.utils import secure_filename
from db.db_integration import initialize_databases, CandidateManager, MatchingEngine
from utils.pdf_parser import extract_text_from_pdf
from utils.api_clients import get_linkedin_data, get_github_data
from utils.llm_matching import LLMMatchingEngine
import PyPDF2
import io
from datetime import datetime

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Set secret key for sessions
app.secret_key = app.config.get('SECRET_KEY', 'dev_secret_key')

# Initialize databases
mysql_conn, neo4j_conn = initialize_databases()
candidate_manager = CandidateManager(neo4j_conn.driver)
matching_engine = MatchingEngine(neo4j_conn.driver)
llm_matching_engine = LLMMatchingEngine(neo4j_conn.driver)

# Home page route
@app.route('/')
def index():
    # Get list of jobs for the dropdown
    jobs = mysql_conn.get_job_titles_for_dropdown()
    return render_template('index.html', jobs=jobs)

# Application form route
@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'GET':
        # Get job ID from query parameter
        job_id = request.args.get('job_id')
        
        # Get list of jobs for the dropdown
        jobs = mysql_conn.get_job_titles_for_dropdown()
        
        # Get specific job details if job_id is provided
        job = None
        if job_id:
            job = mysql_conn.get_job_by_id(job_id)
        
        return render_template('apply.html', jobs=jobs, job=job)
    
    elif request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        job_id = request.form.get('job_id')
        linkedin_url = request.form.get('linkedin_url')
        github_url = request.form.get('github_url')
        
        # Process resume file
        if 'resume' not in request.files:
            flash('No resume file uploaded')
            return redirect(request.url)
        
        resume_file = request.files['resume']
        if resume_file.filename == '':
            flash('No resume file selected')
            return redirect(request.url)
        
        # Extract text from resume PDF
        try:
            resume_text = extract_text_from_pdf(resume_file)
        except Exception as e:
            flash(f'Error extracting text from PDF: {str(e)}')
            return redirect(request.url)
        
        # Get LinkedIn data if URL provided
        linkedin_data = None
        if linkedin_url:
            try:
                linkedin_data = get_linkedin_data(linkedin_url)
            except Exception as e:
                flash(f'Error fetching LinkedIn data: {str(e)}')
        
        # Get GitHub data if URL provided
        github_data = None
        if github_url:
            try:
                github_data = get_github_data(github_url)
            except Exception as e:
                flash(f'Error fetching GitHub data: {str(e)}')
        
        # Store candidate data
        form_data = {
            'name': name,
            'email': email,
            'phone': phone,
            'job_id': job_id
        }
        
        try:
            candidate_id = candidate_manager.store_candidate(
                form_data, resume_text, linkedin_data, github_data
            )
            
            if candidate_id:
                # Calculate match score
                match_result = matching_engine.match_candidate_to_job(candidate_id, job_id)
                
                flash('Application submitted successfully!')
                return redirect(url_for('index'))
            else:
                flash('Error storing candidate data')
                return redirect(request.url)
        except Exception as e:
            flash(f'Error processing application: {str(e)}')
            return redirect(request.url)

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple authentication for demo purposes
        if username == app.config.get('ADMIN_USERNAME', 'admin') and password == app.config.get('ADMIN_PASSWORD', 'password'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get list of jobs with application counts and match scores
    jobs = []
    job_titles = []
    applicant_counts = []
    total_applicants = 0
    
    # Variables for statistics
    avg_match_score = 0
    new_applications = 0
    match_distribution = [0, 0, 0, 0]  # Excellent, Good, Moderate, Low
    
    # Get date for today
    today = datetime.now().date()
    
    # Get jobs from MySQL
    mysql_jobs = mysql_conn.get_all_jobs()
    
    # Fetch application data for each job
    with neo4j_conn.driver.session() as session_db:
        # Get total applicants count
        result = session_db.run("""
            MATCH (c:Candidate)-[a:APPLIED_FOR]->(:Job)
            RETURN count(c) AS total
        """)
        record = result.single()
        if record:
            total_applicants = record["total"]
        
        # Get today's applications count
        result = session_db.run("""
            MATCH (c:Candidate)-[a:APPLIED_FOR]->(:Job)
            WHERE date(a.date) = date($today)
            RETURN count(c) AS new_count
        """, today=today.isoformat())
        record = result.single()
        if record:
            new_applications = record["new_count"]
        
        # Get average match score - using LLM score as priority
        result = session_db.run("""
            MATCH (c:Candidate)-[m:MATCHES]->(:Job)
            RETURN avg(COALESCE(m.llm_score, m.score, 0)) AS avg_score
        """)
        record = result.single()
        if record and record["avg_score"] is not None:
            avg_match_score = record["avg_score"]
        
        # Get match distribution - using LLM score as priority
        result = session_db.run("""
            MATCH (c:Candidate)-[m:MATCHES]->(:Job)
            WITH COALESCE(m.llm_score, m.score, 0) AS final_score
            RETURN 
                sum(CASE WHEN final_score > 0.8 THEN 1 ELSE 0 END) AS excellent,
                sum(CASE WHEN final_score > 0.6 AND final_score <= 0.8 THEN 1 ELSE 0 END) AS good,
                sum(CASE WHEN final_score > 0.4 AND final_score <= 0.6 THEN 1 ELSE 0 END) AS moderate,
                sum(CASE WHEN final_score <= 0.4 THEN 1 ELSE 0 END) AS low
        """)
        record = result.single()
        if record:
            match_distribution = [
                int(record["excellent"]),
                int(record["good"]),
                int(record["moderate"]),
                int(record["low"])
            ]
        
        # Get applicant details for each job
        for mysql_job in mysql_jobs:
            job_id = str(mysql_job["id"])
            
            # Get applicant count for this job
            result = session_db.run("""
                MATCH (c:Candidate)-[:APPLIED_FOR]->(j:Job {job_id: $job_id})
                RETURN count(c) AS applicant_count
            """, job_id=job_id)
            record = result.single()
            applicant_count = record["applicant_count"] if record else 0
            
            # Get average match score for this job - using LLM score as priority
            result = session_db.run("""
                MATCH (c:Candidate)-[m:MATCHES]->(j:Job {job_id: $job_id})
                RETURN avg(COALESCE(m.llm_score, m.score, 0)) AS avg_match
            """, job_id=job_id)
            record = result.single()
            avg_match = record["avg_match"] if record and record["avg_match"] is not None else 0
            
            # Add application count and match score to job data
            job_data = dict(mysql_job)
            job_data["applicant_count"] = applicant_count
            job_data["avg_match"] = avg_match
            
            # Add job to list
            jobs.append(job_data)
            
            # Add to chart data
            job_titles.append(mysql_job["job title"])
            applicant_counts.append(applicant_count)
    
    # Get recent applications
    recent_applications = []
    with neo4j_conn.driver.session() as session_db:
        result = session_db.run("""
            MATCH (c:Candidate)-[a:APPLIED_FOR]->(j:Job)
            OPTIONAL MATCH (c)-[m:MATCHES]->(j)
            RETURN 
                c.id AS candidate_id,
                c.name AS name,
                j.title AS job_title,
                a.date AS date,
                COALESCE(m.llm_score, m.score, 0) AS match_score
            ORDER BY a.date DESC
            LIMIT 5
        """)
        
        for record in result:
            recent_applications.append({
                "candidate_id": record["candidate_id"],
                "name": record["name"],
                "job_title": record["job_title"],
                "date": record["date"].iso_format().split('T')[0] if record["date"] else "N/A",
                "match_score": record["match_score"] 
            })
    
    return render_template(
        'admin/dashboard.html', 
        jobs=jobs,
        total_applicants=total_applicants,
        avg_match_score=avg_match_score,
        new_applications=new_applications,
        recent_applications=recent_applications,
        job_titles=job_titles,
        applicant_counts=applicant_counts,
        match_distribution=match_distribution
    )

@app.route('/admin/job/<job_id>')
def admin_job_candidates(job_id):
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get job details
    job = mysql_conn.get_job_by_id(job_id)
    
    # Get all candidates for this job with LLM scores
    with neo4j_conn.driver.session() as session_db:
       # For the admin_job_candidates function:
        result = session_db.run("""
            MATCH (c:Candidate)-[a:APPLIED_FOR]->(j:Job {job_id: $job_id})
            OPTIONAL MATCH (c)-[m:MATCHES]->(j)
            RETURN 
                c.id AS candidate_id,
                c.name AS name,
                c.email AS email,
                a.date AS application_date,
                a.status AS application_status,
                COALESCE(m.llm_score, m.score, 0) AS match_score,
                COALESCE(m.llm_category, m.category, 'Not Evaluated') AS match_category
            ORDER BY match_score DESC
        """, job_id=job_id)
        
        candidates = [dict(record) for record in result]
    
    return render_template(
        'admin/job_candidates.html', 
        job=job, 
        candidates=candidates
    )

@app.route('/admin/candidate/<candidate_id>')
def admin_candidate_details(candidate_id):
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get comprehensive candidate details from Neo4j
    with neo4j_conn.driver.session() as session_db:
        # Get basic candidate information with job match
       # Replace the query in admin_candidate_details
        result = session_db.run("""
            MATCH (c:Candidate {id: $candidate_id})
            OPTIONAL MATCH (c)-[a:APPLIED_FOR]->(j:Job)
            OPTIONAL MATCH (c)-[m:MATCHES]->(j)
            OPTIONAL MATCH (c)-[:HAS_PROFILE]->(l:LinkedInProfile)
            OPTIONAL MATCH (c)-[:HAS_GITHUB]->(g:GitHubProfile)
            RETURN c, m, j, l, g, a
            ORDER BY CASE WHEN m.llm_score IS NULL THEN 0 ELSE m.llm_score END DESC
            LIMIT 1
        """, candidate_id=candidate_id)
        
        record = result.single()
        if not record:
            flash("Candidate not found", "danger")
            return redirect(url_for('admin_dashboard'))
        
        # Extract candidate details
        c_node = record["c"]
        m_rel = record["m"] if record["m"] else {}
        j_node = record["j"] if record["j"] else {}
        l_node = record["l"] if record["l"] else {}
        g_node = record["g"] if record["g"] else {}
        a_rel = record["a"] if record["a"] else {}
        
        # Format basic candidate data using llm_score instead of score
        candidate = {
            "id": c_node["id"],
            "name": c_node.get("name", ""),
            "email": c_node.get("email", ""),
            "phone": c_node.get("phone", ""),
            "resume_text": c_node.get("resume_text", ""),
            "match_score": m_rel.get("llm_score", m_rel.get("score", 0)),  # Prefer llm_score, fall back to score
            "match_category": m_rel.get("llm_category", m_rel.get("category", "Not evaluated")),
            "job_title": j_node.get("title", ""),
            "job_id": j_node.get("job_id", ""),
            "application_status": a_rel.get("status", "Applied"),
            "matched_skills": m_rel.get("llm_strengths", m_rel.get("matched_skills", [])),
            "skills": [],
            "linkedin_url": c_node.get("linkedin_url", ""),
            "github_url": c_node.get("github_url", "")
        }
        
        # Rest of the function remains the same
        # ...
    return render_template('admin/candidate.html', candidate=candidate)

@app.route('/admin/evaluate/<candidate_id>/<job_id>')
def evaluate_candidate(candidate_id, job_id):
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Run LLM evaluation
    evaluation = llm_matching_engine.evaluate_candidate_for_job(candidate_id, job_id)
    
    # Get candidate details
    with neo4j_conn.driver.session() as session_db:
        candidate_result = session_db.run("""
            MATCH (c:Candidate {id: $candidate_id})
            RETURN c.name AS name, c.email AS email, c.phone AS phone
        """, candidate_id=candidate_id)
        candidate = candidate_result.single()
        if not candidate:
            flash("Candidate not found", "danger")
            return redirect(url_for('admin_dashboard'))
        
        # Get job details
        job_result = session_db.run("""
            MATCH (j:Job {job_id: $job_id})
            RETURN j.title AS title, j.job_id AS id
        """, job_id=job_id)
        job = job_result.single()
        if not job:
            flash("Job not found", "danger")
            return redirect(url_for('admin_dashboard'))
    
    # Convert database records to dictionaries
    candidate_dict = dict(candidate)
    job_dict = dict(job)
    
    return render_template(
        'admin/evaluation.html',
        candidate=candidate_dict,
        job=job_dict,
        evaluation=evaluation
    )


@app.route('/admin/candidate/<candidate_id>/job/<job_id>/status/<status>')
def update_candidate_status(candidate_id, job_id, status):
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Update candidate status in Neo4j
    with neo4j_conn.driver.session() as session_db:
        session_db.run("""
            MATCH (c:Candidate {id: $candidate_id})-[a:APPLIED_FOR]->(j:Job {job_id: $job_id})
            SET a.status = $status,
                a.updated_at = datetime()
        """, candidate_id=candidate_id, job_id=job_id, status=status)
    
    # Flash a message
    flash(f"Candidate has been {status}", "success")
    
    # Redirect back to the job candidates page
    return redirect(url_for('admin_job_candidates', job_id=job_id))


# Clean up database connections when the application exits
@app.teardown_appcontext
def cleanup_connections(exception=None):
    """Close database connections when the application context ends"""
    if hasattr(mysql_conn, 'close'):
        mysql_conn.close()
    if hasattr(neo4j_conn, 'close'):
        neo4j_conn.close()
    print("Database connections closed")

if __name__ == '__main__':
    app.run(debug=True)