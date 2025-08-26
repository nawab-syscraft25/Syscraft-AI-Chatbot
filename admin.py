# admin.py

import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory
from tools.enquiry import get_contacts, get_contact_by_id, delete_contact, update_contact, add_contact
from tools.hr_jobs import (
    get_active_job_openings, get_all_applications, get_job_application, 
    add_job_opening, init_hr_db
)
import sqlite3
from datetime import datetime
import base64

app = Flask(__name__, static_folder="static", template_folder="admin_templates")
app.secret_key = 'syscraft_admin_secret_key_2025'  # Change this in production

# Admin authentication (simple - enhance for production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "syscraft2025"  # Change this in production

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

@app.route("/")
def admin_login():
    return render_template("admin_login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    
    if check_auth(username, password):
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid credentials!", "error")
        return redirect(url_for("admin_login"))

@app.route("/dashboard")
def dashboard():
    # Get summary statistics
    contacts = get_contacts()
    applications = get_all_applications()
    job_openings = get_active_job_openings()
    
    stats = {
        "total_contacts": len(contacts),
        "total_applications": len(applications),
        "total_job_openings": len(job_openings),
        "recent_contacts": contacts[-5:] if contacts else [],
        "recent_applications": applications[:5] if applications else []
    }
    
    return render_template("admin_dashboard.html", stats=stats)

# ===== CONTACTS MANAGEMENT =====
@app.route("/admin/contacts")
def contacts_list():
    contacts = get_contacts()
    return render_template("admin_contacts.html", contacts=contacts)

@app.route("/admin/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = get_contact_by_id(contact_id)
    return render_template("admin_contact_detail.html", contact=contact)

@app.route("/admin/contacts/<int:contact_id>/delete", methods=["POST"])
def delete_contact_route(contact_id):
    delete_contact(contact_id)
    flash("Contact deleted successfully!", "success")
    return redirect(url_for("contacts_list"))

@app.route("/admin/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
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
def applications_list():
    applications = get_all_applications()
    return render_template("admin_applications.html", applications=applications)

@app.route("/admin/applications/<int:app_id>")
def application_detail(app_id):
    application = get_job_application(app_id)
    return render_template("admin_application_detail.html", application=application)

@app.route("/admin/applications/<int:app_id>/delete", methods=["POST"])
def delete_application(app_id):
    # Delete from HR database
    conn = sqlite3.connect("tools/hr_applications.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()
    
    flash("Application deleted successfully!", "success")
    return redirect(url_for("applications_list"))

@app.route("/admin/applications/<int:app_id>/download_resume")
def download_resume(app_id):
    application = get_job_application(app_id)
    if application and application.get('resume_content'):
        try:
            # Decode base64 resume content
            resume_data = base64.b64decode(application['resume_content'])
            
            # Create response with PDF content
            from flask import Response
            response = Response(
                resume_data,
                mimetype='application/pdf',
                headers={
                    "Content-Disposition": f"attachment; filename={application['resume_filename']}"
                }
            )
            return response
        except Exception as e:
            flash(f"Error downloading resume: {str(e)}", "error")
            return redirect(url_for("application_detail", app_id=app_id))
    else:
        flash("Resume not found!", "error")
        return redirect(url_for("application_detail", app_id=app_id))

# ===== JOB OPENINGS MANAGEMENT =====
@app.route("/admin/jobs")
def jobs_list():
    jobs = get_active_job_openings()
    return render_template("admin_jobs.html", jobs=jobs)

@app.route("/admin/jobs/add", methods=["GET", "POST"])
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
def database_management():
    return render_template("admin_database.html")

@app.route("/admin/database/backup", methods=["POST"])
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

# ===== SETTINGS =====
@app.route("/settings")
def settings():
    return render_template("admin_settings.html")

if __name__ == "__main__":
    # Create admin templates directory
    os.makedirs("admin_templates", exist_ok=True)
    
    port = int(os.environ.get("ADMIN_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
