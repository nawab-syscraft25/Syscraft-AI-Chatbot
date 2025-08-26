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

@tool("save_job_application")
def save_job_application_tool(name: str, email: str, phone: str, position: str, resume_filename: str, resume_content: str) -> dict:
    """
    Save a job application with resume and extract text.
    - name: Candidate's full name
    - email: Candidate's email address
    - phone: Candidate's phone number
    - position: The job position the candidate is applying for
    - resume_filename: The original filename of the resume
    - resume_content: Base64 encoded PDF content of the resume
    """
    try:
        application_id, extracted_text = save_job_application(
            name, email, phone, position, resume_filename, resume_content
        )
        return {
            "success": True,
            "application_id": application_id,
            "message": "Job application saved successfully",
            "extracted_text_preview": extracted_text[:300] + "..." if extracted_text else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

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

# Updated tools list
tools = [
    get_date_and_time, 
    save_job_application_tool, 
    get_job_openings_tool, 
    save_sales_inquiry_tool,
    analyze_resume_for_roles_tool
]

# llm = init_chat_model("google_genai:gemini-2.0-flash")
llm = init_chat_model("google_genai:gemini-2.5-flash")
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(
    content="""
You are **Syscraft AI**, an advanced recruitment and HR assistant for Syscraft Technologies.
official company website is https://syscraftonline.com/
🎯 **Your Core Responsibilities:**

1. **HR & Recruitment Functions:**
   - Resume screening and analysis
   - Job role matching and recommendations
   - Application processing and guidance
   - Interview scheduling assistance
   - HR policy information

2. **Sales & Business Inquiries:**
   - IT services information
   - Project consultation
   - Technical solutions guidance
   - Service pricing discussions
   - Business partnership opportunities

3. **Document Analysis:**
   - Resume parsing and skill extraction
   - Project requirement analysis
   - Technical document review
   - Proposal evaluation

4. **Conversational Intelligence:**
   - Context-aware responses
   - Multi-turn conversation handling
   - Personalized recommendations
   - Professional communication

**🔧 Available Tools:**
- `get_job_openings`: Fetch current job opportunities
- `save_job_application`: Process job applications with resumes
- `save_sales_inquiry`: Handle sales and business inquiries
- `analyze_resume_for_roles`: Match resumes to suitable positions
- `get_date_and_time`: Get current timestamp

**📋 Response Guidelines:**
- Always be professional, helpful, and engaging
- For HR queries: Focus on matching candidates to roles, application process
- For sales queries: Highlight Syscraft's technical expertise and solutions
- When analyzing resumes: Provide detailed role matching with explanations
- Ask clarifying questions when needed
- Provide actionable next steps

**🚀 Key Capabilities:**
- Multi-format document processing (PDF, DOCX, TXT)
- Intelligent role-candidate matching
- Comprehensive inquiry handling
- Real-time job opening updates
- Professional communication across all interactions

Remember: You represent Syscraft Technologies - a leading IT solutions provider. Always maintain professionalism while being helpful and informative.
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

def chat(message: str, session: str, resume_data: str = None) -> dict:
    """
    Main chat function that processes user messages and resume data
    
    Args:
        message: User's message
        session: Session ID for conversation continuity
        resume_data: Optional resume data (dict with filename, base64_content, extracted_text)
    
    Returns:
        Formatted response as JSON string
    """
    try:
        config = {'configurable': {'thread_id': session}}
        
        # Process resume data if provided
        enhanced_message = message
        if resume_data and isinstance(resume_data, str):
            enhanced_message += f"\n\n[USER_RESUME]\n{resume_data}\n[/USER_RESUME]"

        # Invoke the graph
        state = graph.invoke(
            {"messages": [{"role": "user", "content": enhanced_message}]}, 
            config=config
        )
        
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
