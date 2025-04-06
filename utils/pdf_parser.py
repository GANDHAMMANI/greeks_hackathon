# utils/pdf_parser.py
import PyPDF2
import io
import re
import spacy
from datetime import datetime

# Try to load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except:
    print("SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
    # Create a minimal NLP function if spaCy is not available
    def nlp(text):
        return text

def extract_text_from_pdf(pdf_file):
    """
    Extract text from uploaded PDF file
    
    Args:
        pdf_file: File object from request.files
    
    Returns:
        Extracted text as string
    """
    # Reset the file pointer to the start of the file
    pdf_file.seek(0)
    
    # Read the PDF file
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
    
    # Extract text from all pages
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text() + "\n"
    
    return text

def extract_structured_info(resume_text):
    """
    Extract structured information from resume text
    
    Args:
        resume_text: Text extracted from resume
    
    Returns:
        Dictionary with structured information
    """
    structured_info = {
        "skills": extract_skills(resume_text),
        "education": extract_education(resume_text),
        "experience": extract_experience(resume_text),
        "contact": extract_contact_info(resume_text)
    }
    
    return structured_info

def extract_skills(text):
    """Extract skills from resume text"""
    # Common skill keywords to look for
    programming_languages = [
        "Python", "Java", "JavaScript", "C\\+\\+", "C#", "Ruby", "PHP", "Swift", "Kotlin", 
        "Go", "Rust", "Scala", "Perl", "TypeScript", "HTML", "CSS", "SQL", "R"
    ]
    
    frameworks = [
        "React", "Angular", "Vue", "Django", "Flask", "Spring", "Express", "Node\\.js",
        "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy",
        "Bootstrap", "jQuery", "Laravel", "ASP\\.NET", "Ruby on Rails"
    ]
    
    databases = [
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "SQL Server",
        "Redis", "Cassandra", "ElasticSearch", "DynamoDB", "Firebase"
    ]
    
    tools = [
        "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Jira",
        "Jenkins", "Travis CI", "CircleCI", "Ansible", "Terraform", "Webpack"
    ]
    
    # Combine all skill categories
    all_skills = programming_languages + frameworks + databases + tools
    
    # Skills section extraction
    skills_section = extract_section(text, ["skills", "technical skills", "technologies"])
    
    # If a skills section is found, extract skills from it
    extracted_skills = []
    if skills_section:
        # Look for list items or comma-separated skills
        skill_items = re.findall(r'(?:^|\n)[\s•\-*•]+(.*?)(?:\n|$)', skills_section)
        if skill_items:
            for item in skill_items:
                item = item.strip()
                if item and len(item) > 1:  # Ignore single characters
                    extracted_skills.append(item)
        else:
            # Try comma-separated skills
            skill_items = re.split(r',|;', skills_section)
            for item in skill_items:
                item = item.strip()
                if item and len(item) > 1:
                    extracted_skills.append(item)
    
    # If no skills were found in a dedicated section, search throughout the text
    if not extracted_skills:
        for skill in all_skills:
            pattern = r'\b' + skill + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Use the case from the original skill list
                extracted_skills.append(skill)
    
    # Remove duplicates while preserving order
    unique_skills = []
    for skill in extracted_skills:
        if skill not in unique_skills:
            unique_skills.append(skill)
    
    return unique_skills

def extract_education(text):
    """Extract education information from resume text"""
    education_section = extract_section(text, ["education", "academic", "qualification"])
    if not education_section:
        education_section = text  # Fall back to full text if no education section found
    
    # Common degree patterns
    degree_patterns = [
        r"(?:B\.?S\.?|Bachelor of Science|Bachelor's)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:B\.?A\.?|Bachelor of Arts|Bachelor's)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:M\.?S\.?|Master of Science|Master's)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:M\.?A\.?|Master of Arts|Master's)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:Ph\.?D\.?|Doctor of Philosophy|Doctorate)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:B\.?Tech\.?|Bachelor of Technology)[^\n.]*?(?:in|,)?\s*([^\n.]*)",
        r"(?:M\.?Tech\.?|Master of Technology)[^\n.]*?(?:in|,)?\s*([^\n.]*)"
    ]
    
    # Common university/college pattern
    university_pattern = r'([A-Z][a-zA-Z\s&]+(?:University|College|Institute|School))'
    
    # Date patterns
    date_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)[a-z]*\.?[\s,-]+\d{4}'
    year_range_pattern = r'(?:20|19)\d{2}\s*(?:-|–|to)\s*(?:(?:20|19)\d{2}|Present|Current|Now)'
    
    # GPA pattern
    gpa_pattern = r'(?:GPA|Grade Point Average|CGPA)[\s:]*([0-9.]+)(?:\s*\/\s*([0-9.]+))?'
    percentage_pattern = r'(?:Percentage|marks)[\s:]*([0-9.]+)\s*%'
    
    # Structured education entries
    education_entries = []
    
    # Look for education paragraphs or bullet points
    education_items = re.findall(r'(?:^|\n)(?:[•\-*]\s*|\d+\.\s*|)([^\n]+(?:university|college|institute|school|degree|bachelor|master|phd|b\.s|m\.s|b\.a|m\.a)[^\n]+)(?:\n|$)', education_section, re.IGNORECASE)
    
    # Process each education item
    for item in education_items:
        education_entry = {"degree": "", "field": "", "university": "", "date_range": "", "gpa": ""}
        
        # Extract degree and field
        for pattern in degree_patterns:
            degree_match = re.search(pattern, item, re.IGNORECASE)
            if degree_match:
                degree_type = re.match(r"([^,]*)", pattern).group(1)
                education_entry["degree"] = degree_type.strip()
                education_entry["field"] = degree_match.group(1).strip()
                break
        
        # Extract university
        uni_match = re.search(university_pattern, item)
        if uni_match:
            education_entry["university"] = uni_match.group(1).strip()
        
        # Extract date range
        date_match = re.search(date_pattern, item)
        if date_match:
            education_entry["date_range"] = date_match.group(0).strip()
        else:
            year_match = re.search(year_range_pattern, item)
            if year_match:
                education_entry["date_range"] = year_match.group(0).strip()
        
        # Extract GPA or percentage
        gpa_match = re.search(gpa_pattern, item)
        if gpa_match:
            if gpa_match.group(2):  # If there's a denominator
                education_entry["gpa"] = f"{gpa_match.group(1)}/{gpa_match.group(2)}"
            else:
                education_entry["gpa"] = gpa_match.group(1)
        else:
            percentage_match = re.search(percentage_pattern, item)
            if percentage_match:
                education_entry["gpa"] = f"{percentage_match.group(1)}%"
        
        # Only add non-empty entries
        if education_entry["degree"] or education_entry["university"]:
            education_entries.append(education_entry)
    
    # If no structured entries were found, try a simpler approach
    if not education_entries:
        # Look for university mentions
        universities = re.findall(university_pattern, education_section)
        for university in universities:
            # Find nearby degree mentions
            university_idx = education_section.find(university)
            context = education_section[max(0, university_idx - 100):min(len(education_section), university_idx + 100)]
            
            education_entry = {"degree": "", "field": "", "university": university.strip(), "date_range": "", "gpa": ""}
            
            # Try to find degree in context
            for pattern in degree_patterns:
                degree_match = re.search(pattern, context, re.IGNORECASE)
                if degree_match:
                    degree_type = re.match(r"([^,]*)", pattern).group(1)
                    education_entry["degree"] = degree_type.strip()
                    education_entry["field"] = degree_match.group(1).strip() if degree_match.group(1) else ""
                    break
            
            # Try to find date in context
            date_match = re.search(date_pattern, context)
            if date_match:
                education_entry["date_range"] = date_match.group(0).strip()
            else:
                year_match = re.search(year_range_pattern, context)
                if year_match:
                    education_entry["date_range"] = year_match.group(0).strip()
            
            education_entries.append(education_entry)
    
    return education_entries

def extract_experience(text):
    """Extract work experience information from resume text"""
    experience_section = extract_section(text, ["experience", "work experience", "employment", "professional experience"])
    if not experience_section:
        experience_section = text  # Fall back to full text if no experience section found
    
    # Job title pattern - common job titles followed by common seniority indicators
    title_pattern = r'(?:Software|Senior|Junior|Lead|Principal|Full Stack|Backend|Frontend|Data|Machine Learning|DevOps|QA|Product|Project|Program|Technical|Chief|Director|VP|Head|Manager|Engineer|Developer|Scientist|Analyst|Specialist|Consultant|Architect|Administrator|Designer)'
    
    # Company pattern - look for Pvt Ltd, Inc, LLC, etc. or capitalized words
    company_pattern = r'([A-Z][a-zA-Z\s&]+(?:Pvt\.?|Private|Inc\.?|LLC|Ltd\.?|Limited|Corp\.?|Corporation|Group|Technologies|Solutions|Systems|Company))'
    
    # Date patterns
    date_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)[a-z]*\.?[\s,-]+\d{4}'
    year_range_pattern = r'(?:20|19)\d{2}\s*(?:-|–|to)\s*(?:(?:20|19)\d{2}|Present|Current|Now)'
    
    # Structured experience entries
    experience_entries = []
    
    # Look for experience paragraphs or bullet points
    experience_items = re.findall(r'(?:^|\n)(?:[•\-*]\s*|\d+\.\s*|)([^\n]*?' + title_pattern + r'[^\n]*?)(?:\n|$)', experience_section)
    
    # Process each experience item
    for item in experience_items:
        experience_entry = {"title": "", "company": "", "date_range": "", "description": "", "responsibilities": []}
        
        # Extract job title
        title_match = re.search(title_pattern, item)
        if title_match:
            # Try to find full title (position might be longer than just the matched keyword)
            title_idx = item.find(title_match.group(0))
            # Look for separators that might indicate the end of the title
            separators = ["at", "with", "-", "|", ",", "•"]
            end_idx = len(item)
            for sep in separators:
                sep_idx = item.find(sep, title_idx)
                if sep_idx > title_idx and sep_idx < end_idx:
                    end_idx = sep_idx
            
            experience_entry["title"] = item[title_idx:end_idx].strip()
        
        # Extract company
        company_match = re.search(company_pattern, item)
        if company_match:
            experience_entry["company"] = company_match.group(1).strip()
        
        # Extract date range
        date_match = re.search(date_pattern, item)
        if date_match:
            date_idx = item.find(date_match.group(0))
            # Look for a second date to form a range
            second_date = re.search(date_pattern, item[date_idx + len(date_match.group(0)):])
            if second_date:
                experience_entry["date_range"] = item[date_idx:date_idx + len(date_match.group(0)) + second_date.span()[1]].strip()
            else:
                experience_entry["date_range"] = date_match.group(0).strip()
        else:
            year_match = re.search(year_range_pattern, item)
            if year_match:
                experience_entry["date_range"] = year_match.group(0).strip()
        
        # Look for responsibilities in bullet points following this entry
        resp_pattern = r'(?:^|\n)[•\-*]\s*([^\n]+)'
        idx = experience_section.find(item)
        if idx != -1:
            next_idx = idx + len(item)
            next_section = experience_section[next_idx:next_idx + 500]  # Look ahead for bullet points
            responsibilities = re.findall(resp_pattern, next_section)
            experience_entry["responsibilities"] = [r.strip() for r in responsibilities[:5]]  # Limit to 5 responsibilities
        
        # Only add non-empty entries
        if experience_entry["title"] or experience_entry["company"]:
            experience_entries.append(experience_entry)
    
    # If no structured entries were found, try a simpler approach
    if not experience_entries:
        # Look for company mentions
        companies = re.findall(company_pattern, experience_section)
        for company in companies:
            # Find nearby title mentions
            company_idx = experience_section.find(company)
            context = experience_section[max(0, company_idx - 100):min(len(experience_section), company_idx + 200)]
            
            experience_entry = {"title": "", "company": company.strip(), "date_range": "", "description": "", "responsibilities": []}
            
            # Try to find title in context
            title_match = re.search(title_pattern, context)
            if title_match:
                experience_entry["title"] = title_match.group(0).strip()
            
            # Try to find date in context
            date_match = re.search(date_pattern, context)
            if date_match:
                date_idx = context.find(date_match.group(0))
                # Look for a second date to form a range
                second_date = re.search(date_pattern, context[date_idx + len(date_match.group(0)):])
                if second_date:
                    experience_entry["date_range"] = context[date_idx:date_idx + len(date_match.group(0)) + second_date.span()[1]].strip()
                else:
                    experience_entry["date_range"] = date_match.group(0).strip()
            else:
                year_match = re.search(year_range_pattern, context)
                if year_match:
                    experience_entry["date_range"] = year_match.group(0).strip()
            
            experience_entries.append(experience_entry)
    
    return experience_entries

def extract_contact_info(text):
    """Extract contact information from resume text"""
    contact_info = {
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "website": ""
    }
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        contact_info["email"] = email_match.group(0)
    
    # Phone pattern - various formats
    phone_pattern = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_match = re.search(phone_pattern, text)
    if phone_match:
        contact_info["phone"] = phone_match.group(0)
    else:
        # Try another common format (e.g., 10-digit number)
        alt_phone_pattern = r'\b\d{10}\b'
        alt_phone_match = re.search(alt_phone_pattern, text)
        if alt_phone_match:
            contact_info["phone"] = alt_phone_match.group(0)
    
    # LinkedIn pattern
    linkedin_patterns = [
        r'linkedin\.com/in/([a-zA-Z0-9_-]+)',
        r'linkedin:\s*([a-zA-Z0-9_-]+)'
    ]
    for pattern in linkedin_patterns:
        linkedin_match = re.search(pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact_info["linkedin"] = f"linkedin.com/in/{linkedin_match.group(1)}"
            break
    
    # GitHub pattern
    github_patterns = [
        r'github\.com/([a-zA-Z0-9_-]+)',
        r'github:\s*([a-zA-Z0-9_-]+)'
    ]
    for pattern in github_patterns:
        github_match = re.search(pattern, text, re.IGNORECASE)
        if github_match:
            contact_info["github"] = f"github.com/{github_match.group(1)}"
            break
    
    # Website pattern
    website_pattern = r'https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/\S*)?'
    website_match = re.search(website_pattern, text)
    if website_match:
        # Exclude LinkedIn and GitHub
        if "linkedin.com" not in website_match.group(0) and "github.com" not in website_match.group(0):
            contact_info["website"] = website_match.group(0)
    
    return contact_info

def extract_section(text, section_keywords):
    """
    Extract a section from the resume text based on section keywords
    
    Args:
        text: Resume text
        section_keywords: List of possible section heading keywords
    
    Returns:
        Extracted section text or empty string if not found
    """
    # Create a pattern to match section headings
    pattern = r'(?:^|\n)(?:\s*)((?:' + '|'.join(section_keywords) + r').{0,20}?)(?::|$|(?=\n))(.*?)(?:\n\s*\n|\n(?:[A-Z][a-zA-Z\s]+(?::|$))|$)'
    
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        # Return the first matching section's content
        return match.group(2).strip()
    
    return ""

def extract_structured_info_with_llm(resume_text, llm_client):
    """
    Extract structured information from resume text using LLM
    
    Args:
        resume_text: Text extracted from resume
        llm_client: Initialized LLM client (e.g., Groq)
    
    Returns:
        Dictionary with structured information
    """
    # Create a prompt for the LLM
    prompt = f"""Parse the following resume and extract structured information.
Return the result as a JSON object with these keys:
- skills: Array of technical and professional skills
- education: Array of education entries, each with: degree, field, university, start_date, end_date, gpa (if available)
- experience: Array of work experience entries, each with: title, company, start_date, end_date, is_current, description, responsibilities (array)
- contact: Object with email, phone, linkedin, github, website

Here is the resume text:

{resume_text}

Respond ONLY with valid JSON.
"""
    
    # Call the LLM
    try:
        messages = [{"role": "user", "content": prompt}]
        completion = llm_client.chat.completions.create(
            model="gemma2-9b-it",  # Or your preferred model
            messages=messages,
            temperature=0.2,  # Lower temperature for more structured output
            max_tokens=2048,
        )
        
        response_text = completion.choices[0].message.content
        
        # Try to extract JSON from the response
        import json
        import re
        
        # Look for JSON block
        json_match = re.search(r'```json\n([\s\S]+?)\n```', response_text)
        if json_match:
            response_text = json_match.group(1)
        
        # Remove any non-JSON text
        json_str = re.search(r'(\{[\s\S]+\})', response_text)
        if json_str:
            response_text = json_str.group(1)
        
        # Parse the JSON
        structured_info = json.loads(response_text)
        
        return structured_info
    except Exception as e:
        print(f"Error extracting structured info with LLM: {str(e)}")
        # Fall back to regex-based extraction
        from utils.pdf_parser import extract_structured_info
        return extract_structured_info(resume_text)