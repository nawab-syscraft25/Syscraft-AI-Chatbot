import sqlite3

DB_NAME = "hr_applications.db"

schema = """
CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    position TEXT NOT NULL,
    resume_filename TEXT NOT NULL,
    resume_content BLOB,
    extracted_text TEXT,
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

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
);
"""

with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    cursor.executescript(schema)
    print("✅ Database tables created successfully!")
