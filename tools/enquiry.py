import sqlite3
from datetime import datetime

DB_NAME = "contacts.db"

# ----------------- CREATE TABLE -----------------
def create_table():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        subject TEXT,
        message TEXT,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

# ----------------- CREATE -----------------
def add_contact(name, email, phone_number, subject, message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO contact (name, email, phone_number, subject, message, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, email, phone_number, subject, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ----------------- READ -----------------
def get_contacts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_contact_by_id(contact_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contact WHERE id = ?", (contact_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# ----------------- UPDATE -----------------
def update_contact(contact_id, name=None, email=None, phone_number=None, subject=None, message=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    updates = []
    values = []
    if name:
        updates.append("name=?")
        values.append(name)
    if email:
        updates.append("email=?")
        values.append(email)
    if phone_number:
        updates.append("phone_number=?")
        values.append(phone_number)
    if subject:
        updates.append("subject=?")
        values.append(subject)
    if message:
        updates.append("message=?")
        values.append(message)

    values.append(contact_id)
    query = f"UPDATE contact SET {', '.join(updates)} WHERE id=?"
    cursor.execute(query, values)

    conn.commit()
    conn.close()

# ----------------- DELETE -----------------
def delete_contact(contact_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()

# ----------------- DEMO -----------------
if __name__ == "__main__":
    create_table()
    
    # Add a contact
    add_contact("John Doe", "john@example.com", "1234567890", "Test Subject", "Hello, this is a test message.")

    # Read all
    print("All contacts:", get_contacts())

    # Read single
    print("Contact with ID 1:", get_contact_by_id(1))

    # Update
    update_contact(1, name="John Smith", message="Updated message")
    print("Updated Contact ID 1:", get_contact_by_id(1))

    # Delete
    # delete_contact(1)
    # print("After Deletion:", get_contacts())

# Initialize the database when module is imported
create_table()
