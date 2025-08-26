import os
import base64
import json
import sqlite3
from datetime import datetime
import shutil

from flask import (
    Flask, request, jsonify, render_template, redirect,
    url_for, flash, send_from_directory, Response, session
)

# Tools for Admin (Contacts + HR Jobs)
from tools.enquiry import get_contacts, get_contact_by_id, delete_contact, update_contact, add_contact
from tools.hr_jobs import (
    get_active_job_openings, get_all_applications, get_job_application,
    add_job_opening, init_hr_db
)

# Document parsing
import fitz  # PyMuPDF
from docx import Document

# Import AI Chat
from chat2 import chat


# ---------------------------
# Flask Setup
# ---------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "syscraft_secret_key_2025"  # 🔐 Change in production

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------
# Admin Authentication
# ---------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "syscraft2025"  # 🔐 Change in production


def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def login_required(f):
    """Decorator to protect admin routes"""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in first!", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return wrapper


# ---------------------------
# Utility Functions
# ---------------------------
def extract_text_from_file(file_path: str) -> str:
    text = ""
    try:
        if file_path.lower().endswith(".pdf"):
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"
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
# Public Routes
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
        ai_reply = chat(message=message, session=session_id, resume_data=resume_data)
        try:
            data = json.loads(ai_reply)
        except Exception:
            data = {"answer": str(ai_reply)}
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        app.logger.exception("Error in chat")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No filename"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    text_content = extract_text_from_file(filepath)
    encoded = file_to_base64(filepath)

    ai_reply = chat(
        message="According to my resume, for which role am I a good fit?",
        session="default_session",
        resume_data=text_content.strip(),
    )
    try:
        data = json.loads(ai_reply) if isinstance(ai_reply, str) else ai_reply
    except json.JSONDecodeError:
        data = {"answer": ai_reply}

    return jsonify({
        "status": "success",
        "filename": file.filename,
        "base64_content": encoded,
        "plain_text": text_content.strip(),
        "analysis": data,
    })


@app.route("/upload_document", methods=["POST"])
def upload_document():
    if "document" not in request.files:
        return jsonify({"error": "No document uploaded"}), 400
    file = request.files["document"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    extracted_text = extract_text_from_file(filepath)
    os.remove(filepath)
    return jsonify({
        "status": "success",
        "filename": file.filename,
        "extracted_text": extracted_text[:5000],
    })


# ---------------------------
# Admin Routes
# ---------------------------
@app.route("/admin")
def admin_login():
    return render_template("admin_login.html")


@app.route("/admin/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    if check_auth(username, password):
        session["logged_in"] = True
        return redirect(url_for("dashboard"))
    flash("Invalid credentials!", "error")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def dashboard():
    contacts = get_contacts()
    applications = get_all_applications()
    jobs = get_active_job_openings()
    stats = {
        "total_contacts": len(contacts),
        "total_applications": len(applications),
        "total_job_openings": len(jobs),
        "recent_contacts": contacts[-5:],
        "recent_applications": applications[:5],
    }
    return render_template("admin_dashboard.html", stats=stats)


# ===== CONTACTS =====
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
        update_contact(contact_id, name, email, phone, subject, message)
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


# ===== APPLICATIONS =====
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
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("Application deleted successfully!", "success")
    return redirect(url_for("applications_list"))


@app.route("/admin/applications/<int:app_id>/download_resume")
@login_required
def download_resume(app_id):
    application = get_job_application(app_id)
    if application and application.get("resume_content"):
        try:
            resume_data = base64.b64decode(application["resume_content"])
            return Response(
                resume_data,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={application['resume_filename']}"
                },
            )
        except Exception as e:
            flash(f"Error downloading resume: {e}", "error")
    else:
        flash("Resume not found!", "error")
    return redirect(url_for("application_detail", app_id=app_id))


# ===== JOBS =====
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
        conn = sqlite3.connect("tools/hr_applications.db")
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE job_openings 
               SET title=?, department=?, description=?, requirements=?, location=?, 
                   employment_type=?, is_active=? WHERE id=?""",
            (title, department, description, requirements, location, employment_type, is_active, job_id),
        )
        conn.commit()
        conn.close()
        flash("Job opening updated successfully!", "success")
        return redirect(url_for("jobs_list"))

    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_openings WHERE id=?", (job_id,))
    job = cursor.fetchone()
    conn.close()
    if job:
        job_dict = {
            "id": job[0],
            "title": job[1],
            "department": job[2],
            "description": job[3],
            "requirements": job[4],
            "location": job[5],
            "employment_type": job[6],
            "posted_date": job[7],
            "is_active": job[8],
        }
        return render_template("admin_job_edit.html", job=job_dict)
    flash("Job not found!", "error")
    return redirect(url_for("jobs_list"))


@app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_openings WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job deleted successfully!", "success")
    return redirect(url_for("jobs_list"))


# ===== DATABASE =====
@app.route("/admin/database")
@login_required
def database_management():
    return render_template("admin_database.html")


@app.route("/admin/database/backup", methods=["POST"])
@login_required
def backup_database():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.exists("contacts.db"):
            shutil.copy2("contacts.db", f"backup_contacts_{timestamp}.db")
        if os.path.exists("tools/hr_applications.db"):
            shutil.copy2("tools/hr_applications.db", f"backup_hr_{timestamp}.db")
        flash("Database backup created successfully!", "success")
    except Exception as e:
        flash(f"Backup failed: {e}", "error")
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
        flash(f"Error clearing contacts: {e}", "error")
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
        flash("All applications cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing applications: {e}", "error")
    return redirect(url_for("database_management"))


# ---------------------------
# Run Server
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port, debug=True)
