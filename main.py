import os
import base64
import json
import sqlite3
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    redirect, url_for, flash, Response
)

# Document parsing
# import fitz  # PyMuPDF
from docx import Document

# Import chat function
from chat2 import chat
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
# Import tools
from tools.enquiry import get_contacts, get_contact_by_id, delete_contact, update_contact, add_contact
from tools.hr_jobs import (
    get_active_job_openings, get_all_applications, get_job_application,
    add_job_opening, init_hr_db
)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "syscraft_secret_key_2025"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("admin_templates", exist_ok=True)


# ---------------------------
# Utility functions
# ---------------------------
import pdfplumber
from docx import Document

def extract_text_from_file(file_path: str) -> str:
    text = ""
    try:
        if file_path.lower().endswith(".pdf"):
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"
        elif file_path.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            text = "[Unsupported file type uploaded]"
    except Exception as e:
        text = f"[Error extracting text: {str(e)}]"
    return text.strip()



def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# Chat Routes
# ---------------------------
@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    payload = request.get_json(force=True)
    message = payload.get("message")
    session_id = payload.get("session_id", "default_session")
    resume_data = payload.get("resume_data")

    if not message:
        return jsonify({"error": "Missing 'message'"}), 400

    try:
        save_message(session_id, "user", message)
        ai_reply = chat(message=message, session=session_id, resume_data=resume_data)
        try:
            data = json.loads(ai_reply)
            save_message(session_id, "ai", str(data))
        except Exception:
            data = {"answer": str(ai_reply)}
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        app.logger.exception("Error in chat")
        return jsonify({"status": "error", "error": str(e)}), 500






def init_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    message TEXT,
                    timestamp TEXT
                )''')
    conn.commit()
    conn.close()

def save_message(session_id, role, message):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO chat_history (session_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
              (session_id, role, message, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def fetch_history(session_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT role, message, timestamp FROM chat_history WHERE session_id=? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "message": r[1], "time": r[2]} for r in rows]


def fetch_all_sessions():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT DISTINCT session_id FROM chat_history ORDER BY session_id ASC")
    sessions = [row[0] for row in c.fetchall()]
    conn.close()
    return sessions

def fetch_all_history():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT session_id, role, message, timestamp FROM chat_history ORDER BY session_id, id ASC")
    rows = c.fetchall()
    conn.close()

    history = {}
    for session_id, role, message, timestamp in rows:
        if session_id not in history:
            history[session_id] = []
        history[session_id].append({
            "role": role,
            "message": message,
            "time": timestamp
        })
    return history









# @app.route("/upload_file", methods=["POST"])
# def upload_file():
#     if "resume" not in request.files:
#         return jsonify({"status": "error", "error": "No file"}), 400

#     file = request.files["resume"]
#     session_id = request.form.get("session_id", "default_session")

#     if file.filename == "":
#         return jsonify({"status": "error", "error": "No selected file"}), 400

#     if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
#         return jsonify({"status": "error", "error": "Only PDF, DOCX, TXT allowed"}), 400

#     filepath = os.path.join(UPLOAD_FOLDER, file.filename)
#     file.save(filepath)

#     text_content = extract_text_from_file(filepath)
#     encoded = file_to_base64(filepath)

#     ai_reply = chat(
#         message="Here is my Document:",
#         session=session_id,
#         resume_data=text_content.strip()
#     )

#     try:
#         data = json.loads(ai_reply) if isinstance(ai_reply, str) else ai_reply
#     except json.JSONDecodeError:
#         data = {"answer": str(ai_reply)}

#     return jsonify({
#         "status": "success",
#         "filename": file.filename,
#         "base64_content": encoded,
#         "plain_text": text_content.strip(),
#         "analysis": data
#     })


@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "resume" not in request.files:
        return jsonify({"status": "error", "error": "No file"}), 400

    file = request.files["resume"]
    session_id = request.form.get("session_id", "default_session")

    if file.filename == "":
        return jsonify({"status": "error", "error": "No selected file"}), 400

    if not file.filename.lower().endswith((".pdf", ".docx", ".txt")):
        return jsonify({"status": "error", "error": "Only PDF, DOCX, TXT allowed"}), 400

    # Rename file -> <session_id>_resume.<ext>
    ext = os.path.splitext(file.filename)[1]   # keep extension (.pdf, .docx, etc.)
    new_filename = f"{session_id}_resume{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, new_filename)

    # Save renamed file
    file.save(filepath)

    # Extract text + base64
    text_content = extract_text_from_file(filepath)

    resume_payload = {
        "filename": new_filename,
        "filepath": f"The file path is: uploads/{new_filename}",
        "extracted_text": text_content.strip()
    }
    save_message(session_id, "user", f"Here is my Document: + {text_content.strip()}")
    # Call chat with structured resume data
    ai_reply = chat(
        message="Here is my Document:",
        session=session_id,
        resume_data=resume_payload
    )
    file.close()

    try:
        data = json.loads(ai_reply) if isinstance(ai_reply, str) else ai_reply
        save_message(session_id, "ai", str(data))
    except json.JSONDecodeError:
        data = {"answer": str(ai_reply)}
        save_message(session_id, "ai", str(data))

    return jsonify({
        "status": "success",
        "filename": new_filename,
        "plain_text": text_content.strip(),
        "analysis": data
    })



@app.route("/upload_document", methods=["POST"])
def upload_document():
    if "document" not in request.files:
        return jsonify({"error": "No document"}), 400

    file = request.files["document"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    extracted_text = extract_text_from_file(file_path)
    os.remove(file_path)

    return jsonify({
        "status": "success",
        "message": "Document processed",
        "filename": file.filename,
        "extracted_text": extracted_text[:5000]
    })


# ---------------------------
# Admin Routes (under /admin)

import os

USER_NAME= os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ---------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Mycraft123"


def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")


# @app.route("/admin/")
# def admin_login():
#     return render_template("admin_login.html")

@app.route("/admin/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if check_auth(username, password):
        session["admin_logged_in"] = True   # ✅ save login state
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid credentials!", "error")
        return redirect(url_for("admin_login"))


@app.route("/admin/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access admin area.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# @app.route("/admin/dashboard")
# def dashboard():
#     contacts = get_contacts()
#     applications = get_all_applications()
#     job_openings = get_active_job_openings()
#     all_history = fetch_all_history() 
#     chat_sessions = fetch_all_sessions()
#     recent_session_ids = list(all_history.keys())[-5:]  # last 5 sessions

#     recent_sessions = []
#     for sid in recent_session_ids:
#         messages = all_history[sid]

#         # Get last user message
#         user_message = next((m['message'] for m in reversed(messages) if m['role'] == 'user'), "")

#         # Get last AI reply
#         ai_reply_raw = next((m['message'] for m in reversed(messages) if m['role'] == 'ai'), "")
        
#         # Extract actual text if AI reply is a dict
#         if isinstance(ai_reply_raw, dict):
#             ai_reply = ai_reply_raw.get("answer", str(ai_reply_raw))
#         else:
#             ai_reply = str(ai_reply_raw)

#         recent_sessions.append({
#             "session_id": sid,
#             "user_message": user_message,
#             "ai_reply": ai_reply
#         })

#     stats = {
#         "total_contacts": len(contacts),
#         "total_applications": len(applications),
#         "total_job_openings": len(job_openings),
#         "total_chat_sessions": len(chat_sessions),
#         "recent_contacts": contacts[-5:] if contacts else [],
#         "recent_applications": applications[:5] if applications else [],
#         "recent_sessions": recent_sessions
#     }
#     return render_template("admin_dashboard.html", stats=stats)


import ast  # to safely parse stringified dicts

@app.route("/admin/dashboard")
@login_required
def dashboard():
    # Fetch data
    contacts = get_contacts()
    applications = get_all_applications()
    job_openings = get_active_job_openings()
    all_history = fetch_all_history()  # {session_id: [{role, message, time}, ...], ...}
    chat_sessions = fetch_all_sessions()  # list of session_ids

    # Last 5 sessions
    recent_session_ids = list(all_history.keys())[-5:]
    recent_sessions = []

    for sid in recent_session_ids:
        messages = all_history[sid]

        # Last user message
        user_message = next((m['message'] for m in reversed(messages) if m['role'] == 'user'), "")

        # Last AI reply
        ai_reply_raw = next((m['message'] for m in reversed(messages) if m['role'] == 'ai'), "")

        # If AI reply is stringified dict, parse it
        if isinstance(ai_reply_raw, str):
            try:
                parsed = ast.literal_eval(ai_reply_raw)
                if isinstance(parsed, dict):
                    ai_reply = parsed.get("answer", str(parsed))
                else:
                    ai_reply = str(parsed)
            except Exception:
                ai_reply = ai_reply_raw  # fallback: show as-is
        elif isinstance(ai_reply_raw, dict):
            ai_reply = ai_reply_raw.get("answer", str(ai_reply_raw))
        else:
            ai_reply = str(ai_reply_raw)

        recent_sessions.append({
            "session_id": sid,
            "user_message": user_message,
            "ai_reply": ai_reply
        })

    stats = {
        "total_contacts": len(contacts),
        "total_applications": len(applications),
        "total_job_openings": len(job_openings),
        "total_chat_sessions": len(chat_sessions),
        "recent_contacts": contacts[-5:] if contacts else [],
        "recent_applications": applications[:5] if applications else [],
        "recent_sessions": recent_sessions if recent_sessions else []
    }

    return render_template("admin_dashboard.html", stats=stats)




# (✅ You can paste all remaining `/admin/contacts`, `/admin/applications`, `/admin/jobs`, `/admin/database`, `/settings`
# routes here, just change them to start with `/admin/...`)

# @app.route("/admin/chat_history")
# def admin_chat_history():
#     history = fetch_all_history()
#     return render_template("admin_chat_history.html", history=history)

import ast

@app.route("/admin/chat_history")
def admin_chat_history():
    raw_history = fetch_all_history()  # {session_id: [{role, message, time}, ...], ...}
    history = {}

    for session_id, messages in raw_history.items():
        parsed_messages = []
        for m in messages:
            message = m['message']

            # Parse AI messages if they are stringified dicts
            if m['role'] == 'ai' and isinstance(message, str):
                try:
                    parsed = ast.literal_eval(message)
                    if isinstance(parsed, dict):
                        message = parsed.get("answer", str(parsed))
                except Exception:
                    message = message  # fallback: keep original string

            parsed_messages.append({
                "role": m['role'],
                "message": message,
                "time": m['time']
            })

        history[session_id] = parsed_messages

    return render_template("admin_chat_history.html", history=history)

# ===== CONTACTS MANAGEMENT =====
@app.route("/admin/contacts")
@login_required
def contacts_list():
    contacts = get_contacts()
    return render_template("admin_contacts.html", contacts=contacts)

@app.route("/admin/contacts/<int:contact_id>")
@login_required
def contact_detail(contact_id):
    contact = get_contact_by_id(contact_id)
    return render_template("admin_contact_detail.html", contact=contact)

@app.route("/admin/contacts/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete_contact_route(contact_id):
    delete_contact(contact_id)
    flash("Contact deleted successfully!", "success")
    return redirect(url_for("contacts_list"))

@app.route("/admin/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit_contact(contact_id):
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone_number")
        subject = request.form.get("subject")
        message = request.form.get("message")
        
        update_contact(contact_id, name=name, email=email, phone_number=phone, 
                      subject=subject, message=message)
        flash("Contact updated successfully!", "success")
        return redirect(url_for("contact_detail", contact_id=contact_id))
    
    contact = get_contact_by_id(contact_id)
    return render_template("admin_contact_edit.html", contact=contact)

@app.route("/admin/contacts/add", methods=["GET", "POST"])
@login_required
def add_contact_route():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone_number")
        subject = request.form.get("subject")
        message = request.form.get("message")
        
        add_contact(name, email, phone, subject, message)
        flash("Contact added successfully!", "success")
        return redirect(url_for("contacts_list"))
    
    return render_template("admin_contact_add.html")

# ===== JOB APPLICATIONS MANAGEMENT =====
@app.route("/admin/applications")
@login_required
def applications_list():
    applications = get_all_applications()
    return render_template("admin_applications.html", applications=applications)

@app.route("/admin/applications/<int:app_id>")
@login_required
def application_detail(app_id):
    application = get_job_application(app_id)
    return render_template("admin_application_detail.html", application=application)

@app.route("/admin/applications/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_application(app_id):
    # Delete from HR database
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    
    flash("Application deleted successfully!", "success")
    return redirect(url_for("applications_list"))

# @app.route("/admin/applications/<int:app_id>/download_resume")
# def download_resume(app_id):
#     application = get_job_application(app_id)
#     if application and application.get('resume_content'):
#         try:
#             # Decode base64 resume content
#             resume_data = base64.b64decode(application['resume_content'])
            
#             # Create response with PDF content
#             from flask import Response
#             response = Response(
#                 resume_data,
#                 mimetype='application/pdf',
#                 headers={
#                     "Content-Disposition": f"attachment; filename={application['resume_filename']}"
#                 }
#             )
#             return response
#         except Exception as e:
#             flash(f"Error downloading resume: {str(e)}", "error")
#             return redirect(url_for("application_detail", app_id=app_id))
#     else:
#         flash("Resume not found!", "error")
#         return redirect(url_for("application_detail", app_id=app_id))

import os
from flask import send_file, current_app, flash, redirect, url_for

@app.route("/admin/applications/<int:app_id>/download_resume")
@login_required
def download_resume(app_id):
    application = get_job_application(app_id)

    if application and application.get('file_path'):
        try:
            # Build full path (uploads folder + stored filename)
            uploads_folder = os.path.join(current_app.root_path, "uploads")
            full_path = os.path.join(uploads_folder, application['file_path'])

            if not os.path.exists(full_path):
                flash("File not found on server!", "error")
                return redirect(url_for("application_detail", app_id=app_id))

            # Send actual file for download
            return send_file(
                full_path,
                as_attachment=True,
                download_name=application['resume_filename']  # keep original filename for user
            )

        except Exception as e:
            flash(f"Error downloading resume: {str(e)}", "error")
            return redirect(url_for("application_detail", app_id=app_id))

    else:
        flash("Resume not found!", "error")
        return redirect(url_for("application_detail", app_id=app_id))





# ===== JOB OPENINGS MANAGEMENT =====
@app.route("/admin/jobs")
@login_required
def jobs_list():
    jobs = get_active_job_openings()
    return render_template("admin_jobs.html", jobs=jobs)

@app.route("/admin/jobs/add", methods=["GET", "POST"])
@login_required
def add_job():
    if request.method == "POST":
        title = request.form.get("title")
        department = request.form.get("department")
        description = request.form.get("description")
        requirements = request.form.get("requirements")
        location = request.form.get("location", "Indore")
        employment_type = request.form.get("employment_type", "Full-time")
        
        from tools.hr_jobs import add_job_opening
        add_job_opening(title, department, description, requirements, location, employment_type)
        flash("Job opening added successfully!", "success")
        return redirect(url_for("jobs_list"))
    
    return render_template("admin_job_add.html")

@app.route("/admin/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    if request.method == "POST":
        title = request.form.get("title")
        department = request.form.get("department")
        description = request.form.get("description")
        requirements = request.form.get("requirements")
        location = request.form.get("location")
        employment_type = request.form.get("employment_type")
        is_active = 1 if request.form.get("is_active") else 0
        
        # Update job opening
        conn = sqlite3.connect("tools/hr_applications.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE job_openings 
            SET title=?, department=?, description=?, requirements=?, location=?, employment_type=?, is_active=?
            WHERE id=?
        """, (title, department, description, requirements, location, employment_type, is_active, job_id))
        conn.commit()
        conn.close()
        
        flash("Job opening updated successfully!", "success")
        return redirect(url_for("jobs_list"))
    
    # Get job details
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_openings WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    
    if job:
        job_dict = {
            "id": job[0], "title": job[1], "department": job[2],
            "description": job[3], "requirements": job[4], "location": job[5],
            "employment_type": job[6], "posted_date": job[7], "is_active": job[8]
        }
        return render_template("admin_job_edit.html", job=job_dict)
    else:
        flash("Job not found!", "error")
        return redirect(url_for("jobs_list"))

@app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_openings WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    
    flash("Job opening deleted successfully!", "success")
    return redirect(url_for("jobs_list"))

# ===== DATABASE MANAGEMENT =====
@app.route("/admin/database")
@login_required
def database_management():
    return render_template("admin_database.html")

@app.route("/admin/database/backup", methods=["POST"])
@login_required
def backup_database():
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Backup contacts database
        if os.path.exists("contacts.db"):
            shutil.copy2("contacts.db", f"backup_contacts_{timestamp}.db")
        
        # Backup HR database
        if os.path.exists("tools/hr_applications.db"):
            shutil.copy2("tools/hr_applications.db", f"backup_hr_{timestamp}.db")
        
        flash(f"Database backup created successfully! (timestamp: {timestamp})", "success")
    except Exception as e:
        flash(f"Backup failed: {str(e)}", "error")
    
    return redirect(url_for("database_management"))

@app.route("/admin/database/clear_contacts", methods=["POST"])
@login_required
def clear_contacts():
    try:
        conn = sqlite3.connect("contacts.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contact")
        conn.commit()
        conn.close()
        flash("All contacts cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing contacts: {str(e)}", "error")
    
    return redirect(url_for("database_management"))

@app.route("/admin/database/clear_applications", methods=["POST"])
@login_required
def clear_applications():
    try:
        conn = sqlite3.connect("tools/hr_applications.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM job_applications")
        conn.commit()
        conn.close()
        flash("All job applications cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing applications: {str(e)}", "error")
    
    return redirect(url_for("database_management"))

from tools.about_syscraft import update_company_vectors

def update_company_vectors_info(description):
 
    # TODO: Implement function to update Pinecone vectors
    update_company_vectors(description)
    return "Description updated successfully!"




# ===== COMPANY DESCRIPTION MANAGEMENT =====
# @app.route("/admin/company", methods=["GET", "POST"])
# @login_required
# def company_description():
#     conn = sqlite3.connect("tools/hr_applications.db")
#     cursor = conn.cursor()
#     cursor.execute("CREATE TABLE IF NOT EXISTS company_info (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
#     if request.method == "POST":
#         description = request.form.get("description")

#         # Remove old entry (only 1 description allowed)
#         cursor.execute("DELETE FROM company_info")
#         cursor.execute("INSERT INTO company_info (description) VALUES (?)", (description,))
#         conn.commit()
#         conn.close()

#         flash("Company description updated successfully!", "success")

#         # TODO: Call function to update Pinecone vectors here
#         update_company_vectors_info(description)

#         return redirect(url_for("company_description"))
    
#     cursor.execute("SELECT description FROM company_info ORDER BY updated_at DESC LIMIT 1")
#     row = cursor.fetchone()
#     conn.close()

#     current_description = row[0] if row else ""
#     return render_template("admin_company.html", description=current_description)


# ===== COMPANY DESCRIPTION & QUESTIONNAIRE MANAGEMENT =====

# ===== COMPANY DESCRIPTION MANAGEMENT =====
@app.route("/admin/company", methods=["GET", "POST"])
@login_required
def company_description():
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()

    # Ensure base table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure q1..q19 columns exist
    for i in range(1, 20):
        try:
            cursor.execute(f"ALTER TABLE company_info ADD COLUMN q{i} TEXT")
        except sqlite3.OperationalError:
            pass

    if request.method == "POST":
        description = request.form.get("description")
        answers = [request.form.get(f"q{i}") for i in range(1, 20)]

        # Keep only 1 row
        cursor.execute("DELETE FROM company_info")
        cursor.execute(f"""
            INSERT INTO company_info 
            (description, {','.join([f'q{i}' for i in range(1, 20)])})
            VALUES ({','.join(['?' for _ in range(20)])})
        """, (description, *answers))
        conn.commit()
        conn.close()

        flash("Company description & questionnaire updated successfully!", "success")

        # Update Pinecone with full text
        combined_text = description + "\n\n" + "\n".join(filter(None, answers))
        update_company_vectors_info(combined_text)

        return redirect(url_for("company_description"))

    # Fetch latest row
    cursor.execute(f"""
        SELECT description, {','.join([f'q{i}' for i in range(1, 20)])}
        FROM company_info ORDER BY updated_at DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    context = {"description": row[0] if row else ""}
    for i in range(1, 20):
        context[f"q{i}"] = row[i] if row and len(row) > i else ""

    return render_template("admin_company.html", **context)
from datetime import datetime
@app.template_filter('format_dt')
def format_dt(value):
    try:
        dt = datetime.fromisoformat(value)  # parses "2025-08-29T05:32:34.002588"
        return dt.strftime("%d %b %Y, %I:%M %p")  # "29 Aug 2025, 05:32 AM"
    except Exception:
        return value  # fallback

@app.route("/admin/settings")
@login_required
def settings():
    return render_template("admin_settings.html")

# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    init_db() 
    port = int(os.environ.get("PORT", 9050))
    app.run(host="0.0.0.0", port=port, debug=True)
