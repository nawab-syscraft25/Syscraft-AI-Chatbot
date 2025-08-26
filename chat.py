from langchain.chat_models import init_chat_model
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
import re
from datetime import datetime

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


from tools.enquiry import add_contact, get_contacts, get_contact_by_id, update_contact, delete_contact
from tools.hr_jobs import get_active_job_openings, save_job_application, get_job_application

import os
api_key = os.getenv("GOOGLE_API_KEY")


serpapi_key = os.getenv("serpapi_key")

import dateparser  
class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]




@tool
def Add_enquiry_sale(name: str, email: str, phone_number: str, subject: str, message: str) -> str:
    """
    Adds a new contact inquiry to the database.
    """
    add_contact(name, email, phone_number, subject, message)
    return "Inquiry added successfully."

@tool
def get_job_openings() -> str:
    """
    Retrieves all active job openings at Syscraft.
    Returns a formatted list of available positions.
    """
    jobs = get_active_job_openings()
    if not jobs:
        return "No job openings are currently available."
    
    result = "Current Job Openings at Syscraft:\n\n"
    for job in jobs:
        result += f"Position: {job['title']}\n"
        result += f"Department: {job['department']}\n"
        result += f"Location: {job['location']}\n"
        result += f"Type: {job['employment_type']}\n"
        result += f"Description: {job['description']}\n"
        result += f"Requirements: {job['requirements']}\n"
        result += f"Posted: {job['posted_date']}\n"
        result += "-" * 50 + "\n\n"
    
    return result

@tool
def submit_job_application(name: str, email: str, phone: str, position: str, resume_base64: str, resume_filename: str) -> str:
    """
    Save a job application to the database. All arguments must be provided by the LLM from user input.
    """
    try:
        application_id, extracted_text = save_job_application(
            name, email, phone, position, resume_filename, resume_base64
        )
        return f"🎉 Application submitted for {position}! We will contact you at {email}."
    except Exception as e:
        return f"❌ Error saving application: {str(e)}"

@tool
def analyze_resume_for_role_matching(resume_base64: str, resume_filename: str) -> str:
    """
    Efficiently analyzes a resume to determine the best job role match at Syscraft.
    Uses fast pattern matching with intelligent scoring for quick response.
    """
    try:
        from tools.hr_jobs import extract_text_from_pdf, get_active_job_openings
        import re
        
        print(f"⚡ Fast resume analysis for: {resume_filename}")
        
        # Extract text from PDF using PyPDF2
        extracted_text = extract_text_from_pdf(resume_base64)
        
        if "Error" in extracted_text:
            return f"❌ Could not process resume: {extracted_text}"
        
        if not extracted_text.strip():
            return "❌ Resume appears to be empty. Please upload a valid PDF resume."
        
        # Use first 3000 characters for analysis (sufficient for most resumes)
        resume_text = extracted_text[:3000].lower()
        
        # Get current job openings
        jobs = get_active_job_openings()
        if not jobs:
            return "Currently no job openings available at Syscraft."
        
        result = f"📋 **Resume Analysis for {resume_filename}**\n\n"
        
        # Enhanced skill detection with scoring
        skill_categories = {
            'Programming': {
                'keywords': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift'],
                'weight': 1.5
            },
            'Web Development': {
                'keywords': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'laravel'],
                'weight': 1.3
            },
            'Data Science/AI': {
                'keywords': ['machine learning', 'artificial intelligence', 'data science', 'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn', 'deep learning'],
                'weight': 1.8
            },
            'Design': {
                'keywords': ['ui/ux', 'figma', 'photoshop', 'illustrator', 'sketch', 'adobe xd', 'design thinking', 'wireframe', 'prototype'],
                'weight': 1.6
            },
            'Cloud/DevOps': {
                'keywords': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd', 'terraform', 'ansible'],
                'weight': 1.4
            },
            'Database': {
                'keywords': ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'sql', 'nosql'],
                'weight': 1.2
            }
        }
        
        detected_skills = {}
        total_skill_score = 0
        
        for category, data in skill_categories.items():
            found_skills = []
            category_score = 0
            
            for keyword in data['keywords']:
                if keyword in resume_text:
                    found_skills.append(keyword.title())
                    category_score += data['weight']
            
            if found_skills:
                detected_skills[category] = {
                    'skills': found_skills[:5],  # Limit to top 5 per category
                    'score': category_score
                }
                total_skill_score += category_score
        
        # Display detected skills
        if detected_skills:
            result += "🎯 **Detected Skills:**\n"
            for category, data in detected_skills.items():
                result += f"   • **{category}:** {', '.join(data['skills'])}\n"
            result += "\n"
        
        # Experience detection with smart patterns
        experience_years = 0
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience[:\s]*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s*(?:of\s*)?(?:exp|experience)',
            r'working\s*(?:for\s*)?(\d+)\+?\s*years?'
        ]
        
        for pattern in exp_patterns:
            matches = re.findall(pattern, resume_text)
            if matches:
                try:
                    experience_years = max(experience_years, int(matches[0]))
                except:
                    continue
        
        if experience_years > 0:
            result += f"💼 **Experience:** {experience_years} years\n\n"
        
        # Intelligent job matching with scoring
        result += "🏢 **Best Job Matches at Syscraft:**\n\n"
        
        job_matches = []
        
        for job in jobs:
            match_score = 0
            match_reasons = []
            job_title_lower = job['title'].lower()
            
            # AI/ML Engineer matching
            if any(term in job_title_lower for term in ['ai', 'ml', 'machine learning', 'data scientist']):
                if 'Data Science/AI' in detected_skills:
                    match_score += detected_skills['Data Science/AI']['score'] * 20
                    match_reasons.append(f"Strong AI/ML background")
                if 'Programming' in detected_skills:
                    match_score += 25
                    match_reasons.append("Programming skills")
            
            # Full Stack Developer matching
            elif any(term in job_title_lower for term in ['full stack', 'developer', 'software engineer']):
                if 'Programming' in detected_skills:
                    match_score += detected_skills['Programming']['score'] * 15
                    match_reasons.append("Programming expertise")
                if 'Web Development' in detected_skills:
                    match_score += detected_skills['Web Development']['score'] * 18
                    match_reasons.append("Web development skills")
            
            # UI/UX Designer matching
            elif any(term in job_title_lower for term in ['ui', 'ux', 'design']):
                if 'Design' in detected_skills:
                    match_score += detected_skills['Design']['score'] * 25
                    match_reasons.append("Design expertise")
            
            # DevOps Engineer matching
            elif any(term in job_title_lower for term in ['devops', 'operations', 'infrastructure']):
                if 'Cloud/DevOps' in detected_skills:
                    match_score += detected_skills['Cloud/DevOps']['score'] * 22
                    match_reasons.append("DevOps/Cloud skills")
                if 'Programming' in detected_skills:
                    match_score += 15
                    match_reasons.append("Programming background")
            
            # Experience bonus
            if experience_years > 0:
                if experience_years >= 5:
                    match_score += 30
                    match_reasons.append(f"Senior experience ({experience_years} years)")
                elif experience_years >= 2:
                    match_score += 20
                    match_reasons.append(f"Mid-level experience ({experience_years} years)")
                else:
                    match_score += 10
                    match_reasons.append(f"Entry-level experience")
            
            # General technical background bonus
            if match_score == 0 and total_skill_score > 0:
                match_score = min(50, total_skill_score * 8)
                match_reasons.append("General technical background")
            
            if match_score > 0:
                job_matches.append({
                    'job': job,
                    'score': min(100, int(match_score)),  # Cap at 100%
                    'reasons': match_reasons
                })
        
        # Sort by match score
        job_matches.sort(key=lambda x: x['score'], reverse=True)
        
        # Display top matches
        if job_matches:
            for i, match in enumerate(job_matches[:3]):  # Top 3 matches
                job = match['job']
                score = match['score']
                reasons = match['reasons']
                
                if score >= 80:
                    match_level = "🌟 **Excellent Match**"
                elif score >= 60:
                    match_level = "✅ **Good Match**"
                else:
                    match_level = "⚡ **Potential Match**"
                
                result += f"{i+1}. {match_level}\n"
                result += f"   **Position:** {job['title']}\n"
                result += f"   **Department:** {job['department']}\n"
                result += f"   **Match Score:** {score}%\n"
                if reasons:
                    result += f"   **Why you're a fit:** {'; '.join(reasons[:2])}\n"
                result += "\n"
        else:
            result += "📋 **Available Positions:**\n"
            for job in jobs[:3]:
                result += f"• **{job['title']}** - {job['department']}\n"
            result += "\n"
        
        result += "💡 **Next Steps:**\n"
        result += "• Say 'apply for [position]' to submit application\n"
        result += "• Contact HR: hr@syscraftonline.com | +91 76949-29672\n\n"
        result += "Which position interests you? I can help with the application!"
        
        return result
        
    except Exception as e:
        print(f"Resume analysis error: {str(e)}")
        return f"❌ Analysis temporarily unavailable. Contact HR: hr@syscraftonline.com"

@tool
def analyze_resume(application_id: int) -> str:
    """
    Analyzes the extracted text from a submitted resume.
    
    Args:
        application_id: The ID of the job application
    
    Returns:
        str: Analysis of the resume content
    """
    application = get_job_application(application_id)
    if not application:
        return "Application not found."
    
    extracted_text = application.get('extracted_text', '')
    if not extracted_text:
        return "No resume text could be extracted."
    
    # This will be processed by the LLM in the conversation
    return f"Resume content for {application['name']} applying for {application['position']}:\n\n{extracted_text}"

from datetime import datetime



@tool
def get_date_and_time(queary: str) -> str:
    """
    Returns the current date and time in ISO format. 
    takes a query string but does not use it.
    Returns:
        str: Current date and time in ISO format.
    """
    return datetime.now().isoformat()



SYSTEM_PROMPT = (
    "You are Syscraft AI, a helpful assistant for IT solutions and HR applications. "
    "When a user wants to apply for a job, extract their name, email, phone, desired position, and resume info from the conversation. "
    "Once all required details are available, call the submit_job_application tool with those details. "
    "Do not hardcode any user information. Only use what the user provides in the chat. "
    "If any info is missing, ask the user for it. "
    "After calling the tool, confirm the application and offer further assistance."
)

tools = [get_date_and_time, Add_enquiry_sale, get_job_openings, submit_job_application, analyze_resume_for_role_matching, analyze_resume]

# llm = init_chat_model("google_genai:gemini-2.0-flash")
llm = init_chat_model("google_genai:gemini-2.5-flash")

# openai_api_key = os.getenv("OPENAI_API_KEY")

# llm = init_chat_model("openai:gpt-4.1")
llm_with_tools = llm.bind_tools(tools)
llm_with_tools = llm_with_tools.with_config({"system_message": SYSTEM_PROMPT})












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
    # This regex finds the first {...} block even if it's multiline
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {"answer": "Sorry, I couldn't parse the response properly."}
    return text


def chat(message: str, session: str, resume_data: dict = None) -> dict:
    config1 = { 'configurable': { 'thread_id': session} }
    
    # Define message_lower for consistent use
    message_lower = message.lower()
    
    # ROBUST RESUME HANDLING - Direct processing for speed and reliability
    if resume_data and resume_data.get('base64_content') and resume_data.get('filename'):
        print(f"Processing resume: {resume_data['filename']}")
        
        # Check if user wants resume analysis (fast path)
        resume_analysis_keywords = [
            'analyze', 'analysis', 'match', 'role', 'position', 'job', 'career', 
            'suitable', 'fit', 'which', 'best', 'recommend', 'check'
        ]
        
        if any(keyword in message_lower for keyword in resume_analysis_keywords):
            try:
                print("Direct resume analysis triggered")
                # Call the fast resume analysis function directly
                result = analyze_resume_for_role_matching.func(
                    resume_data['base64_content'], 
                    resume_data['filename']
                )
                return {"answer": result}
            except Exception as e:
                print(f"Resume analysis error: {e}")
                return {"answer": "❌ Resume analysis failed. Please try uploading again or contact HR at hr@syscraftonline.com"}
        
        # Check if user is providing personal details for application
        apply_keywords = ['apply', 'application', 'submit', 'job application', 'interested']
        
        # First, check if user is providing complete application details
        import re
        name_match = re.search(r'(?:name is |my name is |i am |i\'m )([a-z\s]+)', message_lower)
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', message)
        phone_match = re.search(r'(\+?[0-9\s\-\(\)]{10,15})', message)
        
        # Alternative name extraction - look for name before email
        if not name_match:
            words = message.split()
            for i, word in enumerate(words):
                if '@' in word and i > 0:  # Found email, name might be before it
                    potential_name = ' '.join(words[:i])
                    if len(potential_name.split()) <= 3:  # Reasonable name length
                        name_match = potential_name
                        break
        
        name = name_match.group(1).title() if isinstance(name_match, re.Match) else (name_match.title() if isinstance(name_match, str) else None)
        email = email_match.group(1) if email_match else None
        phone = phone_match.group(1) if phone_match else None
        
        # Extract position preference
        position = None
        if 'ai' in message_lower or 'ml' in message_lower or 'machine learning' in message_lower:
            position = "AI/ML Engineer"
        elif 'full stack' in message_lower or 'developer' in message_lower:
            position = "Senior Full Stack Developer"
        elif 'ui' in message_lower or 'ux' in message_lower or 'designer' in message_lower:
            position = "UI/UX Designer"
        elif 'devops' in message_lower:
            position = "DevOps Engineer"
        elif 'intern' in message_lower:
            position = "Internship Program"
        
        # If we have complete information, submit the application
        if name and email and phone and position and any(keyword in message_lower for keyword in apply_keywords):
            try:
                from tools.hr_jobs import save_job_application
                
                print(f"Submitting application for {name} - {position}")
                application_id, extracted_text = save_job_application(
                    name, email, phone, position,
                    resume_data['filename'], resume_data['base64_content']
                )
                
                return {"answer": f"""🎉 **Application Submitted Successfully!**

**Application ID:** {application_id}
**Applicant:** {name}
**Position:** {position}
**Email:** {email}
**Phone:** {phone}

✅ Your resume has been processed and stored in our system.

**Next Steps:**
• Our HR team will review your application within 2-3 business days
• You'll receive an email confirmation shortly
• If shortlisted, we'll contact you for next steps

**Contact Information:**
📧 hr@syscraftonline.com
📞 +91 76949-29672

Thank you for your interest in joining Syscraft! 🚀"""}
                
            except Exception as e:
                print(f"Application submission error: {e}")
                return {"answer": f"❌ Error submitting application. Please contact HR directly at hr@syscraftonline.com"}
        
        # Check if user wants to apply for a job
        if any(keyword in message_lower for keyword in apply_keywords):
            try:
                # Extract position preference from message
                position = None
                if 'ai' in message_lower or 'ml' in message_lower or 'machine learning' in message_lower:
                    position = "AI/ML Engineer"
                elif 'full stack' in message_lower or 'developer' in message_lower:
                    position = "Senior Full Stack Developer"
                elif 'ui' in message_lower or 'ux' in message_lower or 'designer' in message_lower:
                    position = "UI/UX Designer"
                elif 'devops' in message_lower:
                    position = "DevOps Engineer"
                elif 'intern' in message_lower:
                    position = "Internship Program"
                
                if position:
                    return {"answer": f"""🎯 **Ready to Apply for {position}!**

To complete your application, I need a few details:

📝 **Required Information:**
• Full Name
• Email Address  
• Phone Number
• Confirm Position: {position}

Please provide these details in your next message, or simply say:
"My name is [Your Name], email: [your.email@domain.com], phone: [your number]"

I already have your resume ({resume_data['filename']}) ready for submission! 🚀"""}
                else:
                    # Show available positions
                    try:
                        jobs = get_active_job_openings()
                        if jobs:
                            jobs_list = "\n".join([f"• {job['title']} ({job['department']})" for job in jobs])
                            return {"answer": f"""📋 **Available Positions at Syscraft:**

{jobs_list}

Which position would you like to apply for? Just mention the role name, and I'll help you submit your application!"""}
                        else:
                            return {"answer": "Currently no job openings available. Please check back later or contact HR."}
                    except:
                        return {"answer": "Let me help you apply! Which position are you interested in?"}
            except Exception as e:
                print(f"Application processing error: {e}")
                return {"answer": "I can help you apply! Which position interests you most?"}
    
    # FALLBACK TO LANGGRAPH for complex conversations
    try:
        # Prepare message for LangGraph
        if resume_data and resume_data.get('base64_content'):
            msg = f"""USER MESSAGE: {message}

CONTEXT: User has uploaded resume '{resume_data['filename']}' and is asking: "{message}"

INSTRUCTIONS: Respond naturally and helpfully. If they need resume analysis, job information, or want to apply, use the appropriate tools."""
        else:
            msg = message
        
        # Use LangGraph for intelligent processing
        state = graph.invoke({"messages": [{"role": "user", "content": msg}]}, config=config1)
        response = state["messages"][-1].content
        
        # Robust response handling
        if isinstance(response, str):
            if response.strip():
                return {"answer": response}
            else:
                return {"answer": "I'm here to help! What would you like to know about Syscraft?"}
        else:
            try:
                result = extract_json(response)
                if isinstance(result, dict) and result.get("answer"):
                    return result
                else:
                    return {"answer": "I'm here to help with any questions about Syscraft's services or career opportunities!"}
            except:
                return {"answer": "How can I assist you with Syscraft's services or career opportunities?"}
                
    except Exception as e:
        print(f"Chat processing error: {str(e)}")
        
        # INTELLIGENT FALLBACK - Basic responses for common queries
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return {"answer": "👋 Hello! I'm Syscraft AI assistant. I can help you with our services, career opportunities, or analyze your resume for job matching. How can I assist you today?"}
        
        elif any(word in message_lower for word in ['job', 'career', 'hiring', 'work']):
            return {"answer": """🏢 **Career Opportunities at Syscraft**

We're always looking for talented individuals! Our current focus areas include:
• Full Stack Development
• AI/ML Engineering  
• UI/UX Design
• DevOps Engineering
• Internship Programs

Would you like me to show current openings or analyze your resume for the best fit? 🚀"""}
        
        elif any(word in message_lower for word in ['service', 'product', 'solution', 'business']):
            return {"answer": """🚀 **Syscraft Services**

We specialize in:
• **Web & Mobile Development** - Custom applications
• **AI/ML Solutions** - Intelligent automation & chatbots  
• **UI/UX Design** - User-centered design
• **IoT Solutions** - Connected device ecosystems
• **DevOps & Cloud** - Infrastructure & deployment

📞 Contact us: sales@syscraftonline.com | +91-70065-38876

What specific solution can we help you with?"""}
        
        else:
            return {"answer": "I apologize for the technical difficulty. Please try rephrasing your question, or contact us directly at info@syscraftonline.com for immediate assistance."}
    
    # Final fallback
    return {"answer": "How can I help you today? I can assist with Syscraft's services, career opportunities, or resume analysis!"}
    
# Test function for debugging
# def test_chat():
#     response = chat("Hello, tell me about Syscraft", "test_session")
#     print("Response:", response)
    
# while True:
#     message = input("User: ")
#     if message.strip().lower() in "exit":
#         print("Bot: See You Soon Bye Bye!")
#         break
#     response = chat(message,1)
#     print("Bot : ",response)




