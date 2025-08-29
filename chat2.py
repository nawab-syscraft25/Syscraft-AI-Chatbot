from langchain.chat_models import init_chat_model
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
import re
from datetime import datetime
import base64

from typing import List, Dict
import httpx
import requests
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

from tools.enquiry import add_contact
import os
api_key = os.getenv("GOOGLE_API_KEY")

import dateparser  
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

from tools.hr_jobs import save_job_application, get_active_job_openings


import base64

def safe_extract_text(resume_content: str) -> str:
    """
    Try to decode PDF base64 content. If it's not valid base64, 
    just return the plain text (resume_content).
    """
    try:
        # Try to decode base64
        decoded = base64.b64decode(resume_content, validate=True)
        # If decode worked, try to parse PDF here (PyPDF2 / pdfminer)
        # For now just return raw bytes decoded to string fallback
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        # Not base64 → assume it's already plain text
        return resume_content



@tool("save_job_application")
def save_job_application_tool(
    name: str, email: str, phone: str, position: str, 
    resume_filename: str, resume_content: str, file_path: str
) -> dict:
    """
    Save a job application with resume and extract text.
    - name: Candidate's full name
    - email: Candidate's email address
    - phone: Candidate's phone number
    - position: The job position the candidate is applying for
    - resume_filename: The original filename of the resume
    - resume_content: Summary of the resume content like "Experienced software developer with a background in building scalable applications."
    - file_path: The file path where the resume is stored 
    """
    print("nawab ye Resume:-", resume_content)

    try:
        resume_content = safe_extract_text(resume_content)

        application_id, _ = save_job_application(
            name, email, phone, position, resume_filename, resume_content, file_path
        )

        return {
            "status": "success",
            "application_id": application_id,
            "file_path": file_path
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

@tool("get_job_openings")
def get_job_openings_tool() -> list:
    """
    Get all active job openings available in the system.
    Returns a list of job openings with title, department, description, requirements, location, employment_type, and posted_date.
    """
    try:
        jobs = get_active_job_openings()
        return jobs
    except Exception as e:
        return {"success": False, "error": str(e)}

@tool("save_sales_inquiry")
def save_sales_inquiry_tool(name: str, email: str, phone_number: str, subject: str, message: str) -> dict:
    """
    Save a sales-related inquiry into the contacts database.
    
    Args:
        name: Full name of the inquirer
        email: Email address of the inquirer
        phone_number: Phone number of the inquirer
        subject: Subject of the inquiry (e.g., 'Sales Inquiry', 'Service Request')
        message: Message body of the inquiry
    """
    try:
        add_contact(name, email, phone_number, subject, message)
        return {
            "success": True,
            "message": f"Sales inquiry saved successfully for {name} ({email})",
            "details": {
                "name": name,
                "email": email,
                "phone_number": phone_number,
                "subject": subject,
                "message": message
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@tool("analyze_resume_for_roles")
def analyze_resume_for_roles_tool(resume_text: str) -> dict:
    """
    Analyze resume text and match it against available job openings.
    
    Args:
        resume_text: The extracted text from the resume
    
    Returns:
        dict: Analysis results with role recommendations
    """
    try:
        # Get active job openings
        jobs = get_active_job_openings()
        
        if not jobs:
            return {
                "success": False,
                "error": "No active job openings found"
            }
        
        # Simple keyword matching (you can enhance this with ML/NLP)
        resume_lower = resume_text.lower()
        role_matches = []
        
        for job in jobs:
            score = 0
            matched_skills = []
            
            # Extract keywords from job requirements
            job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}".lower()
            
            # Common tech keywords for scoring
            tech_keywords = [
                'python', 'java', 'javascript', 'react', 'node', 'sql', 'mongodb', 
                'aws', 'docker', 'kubernetes', 'machine learning', 'data science',
                'frontend', 'backend', 'fullstack', 'devops', 'cloud', 'api',
                'html', 'css', 'angular', 'vue', 'express', 'django', 'flask',
                'git', 'agile', 'scrum', 'leadership', 'management'
            ]
            
            for keyword in tech_keywords:
                if keyword in resume_lower and keyword in job_text:
                    score += 1
                    matched_skills.append(keyword)
            
            if score > 0:
                role_matches.append({
                    "job": job,
                    "score": score,
                    "matched_skills": matched_skills,
                    "match_percentage": min(100, (score * 10))  # Cap at 100%
                })
        
        # Sort by score
        role_matches.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            "success": True,
            "total_jobs": len(jobs),
            "matching_roles": role_matches[:5],  # Top 5 matches
            "analysis_summary": f"Found {len(role_matches)} matching roles out of {len(jobs)} available positions"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@tool
def get_date_and_time(query: str) -> str:
    """
    Returns the current date and time in ISO format. 
    takes a query string but does not use it.
    Returns:
        str: Current date and time in ISO format.
    """
    return datetime.now().isoformat()


from tools.about_syscraft import search_company_info

@tool
def get_company_info(query: str) -> str:
    """
    Fetch company information based on the query.
    """
    results = search_company_info(query)
    return results


# Updated tools list
tools = [
    get_date_and_time, 
    save_job_application_tool, 
    get_job_openings_tool, 
    save_sales_inquiry_tool,
    analyze_resume_for_roles_tool,
    get_company_info
]

# llm = init_chat_model("google_genai:gemini-2.0-flash")
llm = init_chat_model("google_genai:gemini-2.5-flash")
llm_with_tools = llm.bind_tools(tools)

# SYSTEM_PROMPT = SystemMessage(
#     content="""
# You are **Syscraft AI**, an advanced recruitment and HR assistant for Syscraft Technologies.
# official company website is https://syscraftonline.com/
# 🎯 **Your Core Responsibilities:**

# 1. **HR & Recruitment Functions:**
#    - Resume screening and analysis
#    - Job role matching and recommendations
#    - Application processing and guidance
#    - Interview scheduling assistance
#    - HR policy information

# 2. **Sales & Business Inquiries:**
#    - IT services information
#    - Project consultation
#    - Technical solutions guidance
#    - Service pricing discussions
#    - Business partnership opportunities

# 3. **Document Analysis:**
#    - Resume parsing and skill extraction
#    - Project requirement analysis
#    - Technical document review
#    - Proposal evaluation

# 4. **Conversational Intelligence:**
#    - Context-aware responses
#    - Multi-turn conversation handling
#    - Personalized recommendations
#    - Professional communication

# **🔧 Available Tools:**
# - `get_job_openings`: Fetch current job opportunities
# - `save_job_application`: Process job applications with resumes
# - `save_sales_inquiry`: Handle sales and business inquiries
# - `analyze_resume_for_roles`: Match resumes to suitable positions
# - `get_date_and_time`: Get current timestamp

# **📋 Response Guidelines:**
# - Always be professional, helpful, and engaging
# - For HR queries: Focus on matching candidates to roles, application process
# - For sales queries: Highlight Syscraft's technical expertise and solutions
# - When analyzing resumes: Provide detailed role matching with explanations
# - Ask clarifying questions when needed
# - Provide actionable next steps
# - If User Upload the Resume
#   - Extract and analyze the resume content
#   - Match the resume with suitable job roles
#   - Provide Short feedback and next steps for the user
#   - Save the resume data for future reference

# **🚀 Key Capabilities:**
# - Multi-format document processing (PDF, DOCX, TXT)
# - Intelligent role-candidate matching
# - Comprehensive inquiry handling
# - Real-time job opening updates
# - Professional communication across all interactions

# Remember: You represent Syscraft Technologies - a leading IT solutions provider. Always maintain professionalism while being helpful and informative.
# """
# )


SYSTEM_PROMPT = SystemMessage(
    content="""
You are **Syscraft AI**, an advanced recruitment, HR, and business assistant for **Syscraft Information System Pvt. Ltd.**  
🌐 Official Website: [https://syscraftonline.com/](https://syscraftonline.com/)

---

### 🎯 Core Responsibilities

#### 1. HR & Recruitment
- Resume screening & analysis  
- Job role matching & recommendations  
- Job application processing & next steps  
- Interview scheduling assistance  
- HR policies & guidance  

#### 2. Sales & Business Inquiries
- Provide IT services & technical solution guidance  
- Clarify project requirements (budget, scope, timeline, goals) if vague  
- Suggest modern, scalable, and secure technology stacks  
- Encourage sharing of contact details (name, email, phone)  
- Save leads via `save_sales_inquiry` for sales follow-up  
- Support discussions on service pricing, partnerships, onboarding, and support  

#### 3. Document Analysis
- Resume parsing & skill extraction  
- Project requirement breakdown  
- Proposal & technical document review  

#### 4. Conversational Intelligence
- Context-aware, multi-turn handling  
- Personalized recommendations  
- Clear, professional, and engaging tone  

#### 5. About Company
- Syscraft is a **leading IT solutions provider** specializing in HR, recruitment, consulting, and business services.  
- Mission: **Connecting talent with opportunity** and driving organizational success via innovative solutions.  
- Use `get_company_info` for structured company insights.  

---

### 🔧 Available Tools
- `get_date_and_time` → Get current timestamp  
- `get_job_openings` → Fetch current job opportunities  
- `save_job_application` → Process job applications with resumes  
- `save_sales_inquiry` → Handle sales & business inquiries  
- `analyze_resume_for_roles` → Match resumes to suitable roles  
- `get_company_info` → Retrieve company information (services, mission, achievements)  

---

### 📋 Response Guidelines
- Maintain **professional, concise, and scannable responses**  
- Use **short bullet points** for listings (jobs, skills, services)  
- **HR Queries**:  
  - Suggest top matching role + % score  
  - Mention 1–2 alternative roles briefly  
  - End with next step (e.g., “Please share email & phone to proceed”)  
- **Sales Queries**:  
  - Highlight Syscraft’s expertise in **2–3 crisp sentences**  
  - Encourage lead capture (name, email, phone)  
- **Job Openings**:  
  - Always display clean bullet format with role + key skills/experience  
  - Example:  
    - 🎓 Internship (0–1 yr, Programming basics)  
    - 💻 Full Stack Developer (3+ yrs, React/Node/Python, DBs)  
- **Resume Uploads**:  
  - Extract skills  
  - Suggest top role match in 2–3 lines  
  - End with clear next step  
  - ❗ Never ask for “resume path” → If resume is not uploaded, politely request the file  
- Avoid long paragraphs unless explicitly asked  
- Always **be clear, structured, and easy to scan**  

---

### 🚀 Key Capabilities
- Multi-format document processing (PDF, DOCX, TXT)  
- AI-powered candidate-role matching  
- Business & technical inquiry handling  
- Real-time job opening insights  
- Professional, human-like conversation flow  

---

✅ **Reminder:** You represent **Syscraft Information System Pvt. Ltd.**  
Maintain professionalism while being **helpful, concise, and user-friendly**.  
"""
)

def chatbot(state: State):
    messages = state["messages"]
    
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SYSTEM_PROMPT] + messages

    return {"messages": [llm_with_tools.invoke(messages)]}

builder = StateGraph(State)
builder.add_node(chatbot)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "chatbot")

# compile without default_state
graph = builder.compile(checkpointer=memory)

import re
import json

def extract_json(text: str) -> dict:
    """Extract JSON from text, fallback to plain text if no JSON found"""
    # Try to find JSON pattern
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Return as plain text if no valid JSON
    return {"answer": text}

def extract_resume_data(resume_data: str) -> tuple:
    """Extract resume filename and base64 content from formatted data"""
    if not resume_data:
        return None, None
    
    # Check for base64 format
    if "[RESUME_DATA]" in resume_data:
        filename_match = re.search(r'Filename: (.+)', resume_data)
        content_match = re.search(r'Content: (.+)', resume_data, re.DOTALL)
        
        filename = filename_match.group(1).strip() if filename_match else "resume.pdf"
        content = content_match.group(1).strip() if content_match else ""
        
        return filename, content
    
    # Check for plain text format
    elif "[RESUME_TEXT]" in resume_data:
        text_match = re.search(r'\[RESUME_TEXT\]\n(.+)\n\[/RESUME_TEXT\]', resume_data, re.DOTALL)
        if text_match:
            return "resume.txt", text_match.group(1).strip()
    
    return None, resume_data

# def chat(message: str, session: str, resume_data: str = None) -> dict:
#     """
#     Main chat function that processes user messages and resume data
    
#     Args:
#         message: User's message
#         session: Session ID for conversation continuity
#         resume_data: Optional resume data (dict with filename, base64_content, extracted_text)
    
#     Returns:
#         Formatted response as JSON string
#     """
#     try:
#         config = {'configurable': {'thread_id': session}}
        
#         # Process resume data if provided
#         enhanced_message = message
#         if resume_data and isinstance(resume_data, str):
#             enhanced_message += f"\n\n[USER_RESUME]\n{resume_data}\n[/USER_RESUME]"

#         # Invoke the graph
#         state = graph.invoke(
#             {"messages": [{"role": "user", "content": enhanced_message}]}, 
#             config=config
#         )
        
#         response = state["messages"][-1].content
#         result = extract_json(response)
        
#         # Ensure we always return a properly formatted response
#         if isinstance(result, dict):
#             return json.dumps(result, indent=2, ensure_ascii=False)
#         else:
#             return json.dumps({"answer": str(result)}, indent=2, ensure_ascii=False)
            
#     except Exception as e:
#         error_response = {
#             "answer": f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again or contact support if the issue persists."
#         }
#         return json.dumps(error_response, indent=2, ensure_ascii=False)



def chat(message: str, session: str, resume_data: dict | str = None) -> dict:
    """
    Main chat function that processes user messages and resume data.
    
    Args:
        message: User's message
        session: Session ID for conversation continuity
        resume_data: Optional resume data (dict with filename, base64_content, extracted_text OR plain string)
    
    Returns:
        Formatted response as JSON string
    """
    try:
        config = {'configurable': {'thread_id': session}}
        
        # Process resume data if provided
        enhanced_message = message
        if resume_data:
            if isinstance(resume_data, dict):
                # Structured payload with filename and extracted text
                enhanced_message += (
                    f"\n\n[USER_RESUME]\n"
                    f"Filename: {resume_data.get('filename')}\n"
                    f"Extracted Text:\n{resume_data.get('extracted_text')}\n"
                    f"[/USER_RESUME]"
                )
            elif isinstance(resume_data, str):
                # Fallback for raw string resume data
                enhanced_message += f"\n\n[USER_RESUME]\n{resume_data}\n[/USER_RESUME]"

        # Invoke the graph (LangGraph will also handle tool calls if registered)
        state = graph.invoke(
            {"messages": [{"role": "user", "content": enhanced_message}]}, 
            config=config
        )
        
        # Extract the last assistant message
        response = state["messages"][-1].content
        result = extract_json(response)
        
        # Ensure we always return a properly formatted response
        if isinstance(result, dict):
            return json.dumps(result, indent=2, ensure_ascii=False)
        else:
            return json.dumps({"answer": str(result)}, indent=2, ensure_ascii=False)
            
    except Exception as e:
        error_response = {
            "answer": f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again or contact support if the issue persists."
        }
        return json.dumps(error_response, indent=2, ensure_ascii=False)


# Test function for debugging
if __name__ == "__main__":
    while True:
        message = input("User: ")
        if message.strip().lower() in ["exit", "quit"]:
            print("Bot: See you soon! Goodbye!")
            break
        
        # Simulate uploaded resume for testing
        dummy_resume = {
            "filename": "resume.pdf",
            "base64_content": "base64_dummy_here",
            "extracted_text": "Python developer with 3 years of experience in Flask, FastAPI, and SQL."
        }
        
        response = chat(message, "test_session", resume_data=dummy_resume)
        print("Bot:", response)
