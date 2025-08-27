import sqlite3
import os
from datetime import datetime
import PyPDF2
import io
import base64

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "hr_applications.db")

def init_hr_db():
    """Initialize the HR applications database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create job_applications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            position TEXT NOT NULL,
            resume_filename TEXT NOT NULL,
            resume_content TEXT,
            file_path TEXT,
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # Create job_openings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_openings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            department TEXT,
            description TEXT,
            requirements TEXT,
            location TEXT DEFAULT 'Indore',
            employment_type TEXT DEFAULT 'Full-time',
            posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def add_job_opening(title, department, description, requirements, location="Indore", employment_type="Full-time"):
    """Add a new job opening."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO job_openings (title, department, description, requirements, location, employment_type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, department, description, requirements, location, employment_type))
    
    conn.commit()
    conn.close()

def get_active_job_openings():
    """Get all active job openings."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, department, description, requirements, location, employment_type, posted_date
        FROM job_openings 
        WHERE is_active = 1
        ORDER BY posted_date DESC
    ''')
    
    jobs = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": job[0],
            "title": job[1],
            "department": job[2],
            "description": job[3],
            "requirements": job[4],
            "location": job[5],
            "employment_type": job[6],
            "posted_date": job[7]
        }
        for job in jobs
    ]

def extract_text_from_pdf(pdf_content):
    """Extract text from PDF content using PyPDF2 with optimized performance."""
    try:
        # Convert base64 to bytes if needed
        if isinstance(pdf_content, str):
            pdf_bytes = base64.b64decode(pdf_content)
        else:
            pdf_bytes = pdf_content
            
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Check if PDF is encrypted
        if pdf_reader.is_encrypted:
            try:
                pdf_reader.decrypt("")  # Try empty password
            except:
                return "Error: PDF is password protected and cannot be read."
        
        text = ""
        total_pages = len(pdf_reader.pages)
        
        # Limit to first 3 pages for speed (most resumes are 1-2 pages)
        max_pages = min(total_pages, 3)
        
        # Extract text from pages
        for page_num in range(max_pages):
            try:
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text.strip():  # Only add non-empty pages
                    text += page_text + "\n"
            except Exception as page_error:
                print(f"Error reading page {page_num + 1}: {page_error}")
                continue
        
        # Basic text cleanup
        if text.strip():
            # Remove excessive whitespace
            import re
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Limit text length for processing speed (first 5000 characters)
            if len(text) > 5000:
                text = text[:5000] + "..."
            
            return text
        else:
            return "Error: No readable text found in PDF. The PDF might be image-based or corrupted."
            
    except Exception as e:
        print(f"PDF extraction error: {str(e)}")
        return f"Error extracting text from PDF: {str(e)}"

def clean_extracted_text(text):
    """Clean and format extracted text for better processing."""
    if not text:
        return ""
    
    # Remove excessive whitespace and newlines
    import re
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove empty lines at the beginning and end
    text = text.strip()
    
    return text

def analyze_resume_text(extracted_text):
    """Analyze extracted resume text and extract key information."""
    if not extracted_text or "Error" in extracted_text:
        return {"error": extracted_text or "No text extracted"}
    
    analysis = {
        "skills": [],
        "experience_years": None,
        "education": [],
        "contact_info": {},
        "work_experience": [],
        "key_sections": {}
    }
    
    text_lower = extracted_text.lower()
    
    # Extract skills (common technical skills)
    common_skills = [
        'python', 'java', 'javascript', 'react', 'node.js', 'html', 'css', 'sql',
        'mongodb', 'postgresql', 'mysql', 'git', 'docker', 'kubernetes', 'aws',
        'azure', 'machine learning', 'ai', 'artificial intelligence', 'data science',
        'tensorflow', 'pytorch', 'flask', 'django', 'spring', 'angular', 'vue.js',
        'c++', 'c#', '.net', 'php', 'ruby', 'go', 'rust', 'scala', 'kotlin',
        'ui/ux', 'figma', 'photoshop', 'illustrator', 'sketch', 'adobe xd',
        'project management', 'agile', 'scrum', 'devops', 'ci/cd', 'jenkins',
        'linux', 'windows', 'macos', 'rest api', 'graphql', 'microservices'
    ]
    
    found_skills = []
    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    analysis["skills"] = list(set(found_skills))  # Remove duplicates
    
    # Extract email and phone (basic patterns)
    import re
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, extracted_text)
    if emails:
        analysis["contact_info"]["email"] = emails[0]
    
    phone_pattern = r'[\+]?[1-9]?[0-9]{7,15}'
    phones = re.findall(phone_pattern, extracted_text)
    if phones:
        analysis["contact_info"]["phone"] = phones[0]
    
    # Extract experience years (basic pattern)
    exp_patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'experience[:\s]*(\d+)\+?\s*years?',
        r'(\d+)\+?\s*yrs?\s*(?:of\s*)?(?:exp|experience)',
    ]
    
    for pattern in exp_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            try:
                years = int(matches[0])
                analysis["experience_years"] = years
                break
            except:
                continue
    
    # Identify key sections
    sections = {}
    section_keywords = {
        "education": ["education", "qualification", "degree", "university", "college", "school"],
        "experience": ["experience", "employment", "work history", "professional experience"],
        "skills": ["skills", "technical skills", "competencies", "technologies"],
        "projects": ["projects", "portfolio", "work samples"],
        "certifications": ["certifications", "certificates", "certified"]
    }
    
    for section_name, keywords in section_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                sections[section_name] = True
                break
    
    analysis["key_sections"] = sections
    
    return analysis

def save_job_application(name, email, phone, position, resume_filename, resume_content, file_path):
    """Save a job application with resume."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Extract text from PDF
    # extracted_text = extract_text_from_pdf(resume_content)
    
    cursor.execute('''
        INSERT INTO job_applications (name, email, phone, position, resume_filename, resume_content, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, email, phone, position, resume_filename, resume_content, file_path))
    
    application_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return application_id, file_path

# def get_job_application(application_id):
#     """Get job application by ID."""
#     conn = sqlite3.connect(DB_PATH)
#     cursor = conn.cursor()
    
#     cursor.execute('''
#         SELECT id, name, email, phone, position, resume_filename, resume_content, application_date, status
#         FROM job_applications 
#         WHERE id = ?
#     ''', (application_id,))
    
#     application = cursor.fetchone()
#     conn.close()
    
#     if application:
#         return {
#             "id": application[0],
#             "name": application[1],
#             "email": application[2],
#             "phone": application[3],
#             "position": application[4],
#             "resume_filename": application[5],
#             "resume_content": application[6],
#             "application_date": application[7],
#             "status": application[8]
#         }
#     return None

def get_job_application(application_id):
    """Get job application by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, phone, position, resume_filename, resume_content, file_path, application_date, status
        FROM job_applications 
        WHERE id = ?
    ''', (application_id,))
    
    application = cursor.fetchone()
    conn.close()
    
    if application:
        return {
            "id": application[0],
            "name": application[1],
            "email": application[2],
            "phone": application[3],
            "position": application[4],
            "resume_filename": application[5],
            "resume_content": application[6],   # ✅ FIX
            "file_path": application[7],
            "application_date": application[8],
            "status": application[9]
        }
    return None



def get_all_applications():
    """Get all job applications."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, email, phone, position, resume_filename, application_date, status
        FROM job_applications 
        ORDER BY application_date DESC
    ''')
    
    applications = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": app[0],
            "name": app[1],
            "email": app[2],
            "phone": app[3],
            "position": app[4],
            "resume_filename": app[5],
            "application_date": app[6],
            "status": app[7]
        }
        for app in applications
    ]

# Initialize the database when module is imported
init_hr_db()

# Add some sample job openings if the table is empty
def add_sample_jobs():
    """Add sample job openings if none exist."""
    jobs = get_active_job_openings()
    if not jobs:
        add_job_opening(
            "Senior Full Stack Developer",
            "Development",
            "We are looking for an experienced Full Stack Developer to join our team and work on cutting-edge web applications.",
            "3+ years experience with React, Node.js, Python, databases. Experience with cloud technologies preferred.",
            "Indore",
            "Full-time"
        )
        add_job_opening(
            "UI/UX Designer",
            "Design",
            "Seeking a creative UI/UX Designer to create intuitive and engaging user experiences for our digital products.",
            "2+ years experience in UI/UX design, Figma, Adobe Creative Suite. Portfolio required.",
            "Indore",
            "Full-time"
        )
        add_job_opening(
            "AI/ML Engineer",
            "AI/ML",
            "Join our AI team to develop innovative machine learning solutions and AI-powered applications.",
            "Strong background in Python, TensorFlow/PyTorch, machine learning algorithms. Experience with NLP preferred.",
            "Indore",
            "Full-time"
        )
        add_job_opening(
            "DevOps Engineer",
            "Operations",
            "Looking for a DevOps Engineer to manage our cloud infrastructure and deployment pipelines.",
            "Experience with AWS/Azure, Docker, Kubernetes, CI/CD pipelines. Strong scripting skills.",
            "Indore",
            "Full-time"
        )
        add_job_opening(
            "AI/ML Engineer",
            "AI/ML",
            "Join our AI team to develop innovative machine learning solutions and AI-powered applications.",
            "Strong background in Python, TensorFlow/PyTorch, machine learning algorithms. Experience with NLP preferred.",
            "Indore",
            "Full-time"
        )

# Add sample jobs
add_sample_jobs()
