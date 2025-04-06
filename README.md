# PBSC Ignite - Intelligent Recruiting Platform

## Project Overview

PBSC Ignite is an advanced recruiting platform that leverages graph databases and machine learning to match candidates with job opportunities more effectively. Built during the Accenture Hackathon, this application streamlines the hiring process by automating candidate evaluation, providing intelligent match scoring, and facilitating efficient job screening. The platform enables administrators to shortlist candidates and automatically send interview invitation emails, eliminating manual outreach efforts.


## 🚀 Key Features

- **Intelligent Candidate Matching**: Uses machine learning to match candidates to job requirements
- **Multi-Source Profile Integration**: Combines resume data with LinkedIn and GitHub profiles
- **Dual Database Architecture**: Utilizes MySQL and Neo4j for optimal data handling
- **Interactive Admin Dashboard**: Visual analytics for application tracking and candidate evaluation
- **Automated PDF Resume Parsing**: Extracts structured data from candidate resumes
- **Real-time Candidate Evaluation**: LLM-powered scoring system with detailed insights
- **Automated Interview Scheduling**: One-click functionality to send interview emails to shortlisted candidates
-**Streamlined Screening Process**: Intuitive interface for reviewing and shortlisting candidates

## 🏗️ System Architecture

SmartRecruit employs a hybrid database approach:

- **MySQL**: Stores structured data including job listings and configuration settings
- **Neo4j Graph Database**: Models complex relationships between candidates, skills, and job requirements
- **Flask Backend**: Handles business logic, API requests, and database interactions
- **Bootstrap Frontend**: Responsive user interface for both candidates and administrators

## 💻 Technical Implementation

### Backend Stack
- **Framework**: Flask (Python)
- **Databases**: Neo4j (graph database) and MySQL (relational database)
- **PDF Processing**: PyPDF2 for resume text extraction
- **Authentication**: Session-based admin authentication
- **APIs**: Integration with LinkedIn and GitHub for enhanced candidate profiles

### Data Flow
1. Candidate submits application with resume and optional social profiles
2. System extracts text from PDF resume
3. Data is processed and stored in both MySQL and Neo4j databases
4. Matching engine evaluates candidate against job requirements
5. LLM-based analysis provides comprehensive match scoring
6. Results are visualized in the admin dashboard

## 📊 Matching Algorithm

Our platform uses a sophisticated two-tier matching system:

1. **Rules-Based Matching**: Initial scoring based on keyword matching and skill requirements
2. **LLM-Enhanced Evaluation**: Deep analysis of candidate qualifications with natural language understanding
3. **Categorization**: Candidates are classified into match categories (Excellent, Good, Moderate, Low)

## Video Demo


https://github.com/user-attachments/assets/73b5bd95-6ce1-42f5-9f09-ae7077f30c7d


## 🖥️ Installation & Setup

### Prerequisites
- Python 3.8+
- Neo4j Graph Database
- MySQL Server
- Required Python packages (listed in requirements.txt)

### Setup Instructions

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/smart-recruit.git
   cd smart-recruit
   ```

2. Create and activate virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Configure database connections
   ```bash
   cp config.example.py config.py
   # Edit config.py with your database credentials
   ```

5. Initialize the database
   ```bash
   python init_db.py
   ```

6. Run the application
   ```bash
   python app.py
   ```

7. Access the application at http://localhost:5000

## 👩‍💼 User Guide

### For Candidates:
1. Navigate to the home page
2. Select a job from the dropdown menu
3. Fill in personal details and upload resume (PDF format)
4. Optionally provide LinkedIn and GitHub profile URLs
5. Submit application

### For Administrators:
1. Access admin panel at /admin/login (default credentials in config file)
2. View dashboard with application statistics and match distributions
3. Explore job-specific candidate lists
4. Review individual candidate details with match scores
5. Run LLM evaluations on candidates
6. Update candidate application status

## 🔮 Future Enhancements

- **Two-way Matching**: Match jobs to candidates based on preferences
- **Interview Scheduling**: Integrated calendar for interview management
- **Customizable Scoring**: Allow recruiters to adjust matching parameters
- **Candidate Recommendations**: Proactive suggestions for alternate positions
- **Enhanced Analytics**: Predictive analytics for hiring success rate

## 👥 Team

- [Abdul Faheem] - Machine Learning Engineer & Backend Developer 
- [Gandham Mani Saketh] - Frontend Developer & Machine Learning Engineer


## 🙏 Acknowledgments

Special thanks to Accenture for organizing this hackathon and providing the opportunity to create innovative solutions in the recruiting technology space.



https://github.com/user-attachments/assets/c7c50a5d-e85b-4973-8603-d970297f8f65

