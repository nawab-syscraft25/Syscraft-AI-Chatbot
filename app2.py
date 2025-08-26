import os
import base64
import json
from flask import Flask, request, jsonify, render_template, send_from_directory

# Document parsing
import fitz  # PyMuPDF for PDF
from docx import Document

# Import your agent chat function
from chat2 import chat 

app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------
# Utility functions
# ---------------------------
def extract_text_from_file(file_path: str) -> str:
    """Extract text from PDF, DOCX, or TXT file"""
    text = ""

    try:
        # PDF
        if file_path.lower().endswith(".pdf"):
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"

        # DOCX
        elif file_path.lower().endswith(".docx"):
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"

        # TXT
        elif file_path.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        else:
            text = "[Unsupported file type uploaded]"

    except Exception as e:
        text = f"[Error extracting text: {str(e)}]"

    return text.strip()


def file_to_base64(file_path: str) -> str:
    """Convert any file to base64 string"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------
# Static + Home routes
# ---------------------------
@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)


@app.route("/", methods=["GET"])
def index():
    return render_template("chat.html")


# ---------------------------
# Chat Route
# ---------------------------
@app.route("/chat", methods=["POST"])
def chat_endpoint():
    payload = request.get_json(force=True)
    message = payload.get("message")
    session_id = payload.get("session_id", "default_session")
    resume_data = payload.get("resume_data")  # dict with filename, base64_content, extracted_text

    if not message:
        return jsonify({"error": "Missing 'message' in request"}), 400

    try:
        # Call your chat function
        ai_reply = chat(message=message, session=session_id, resume_data=resume_data)

        # ai_reply is already a JSON string → load it back
        try:
            data = json.loads(ai_reply)
        except Exception:
            data = {"answer": str(ai_reply)}

        return jsonify({"status": "success", "data": data})

    except Exception as e:
        app.logger.exception("Error in chat")
        return jsonify({"status": "error", "error": str(e)}), 500


# ---------------------------
# Upload Resume (PDF, DOCX, TXT)
# ---------------------------
@app.route("/upload_file", methods=["POST"])
def upload_file():
    if "resume" not in request.files:
        return jsonify({"status": "error", "error": "No file part"}), 400

    file = request.files["resume"]
    session_id = request.form.get("session_id", "default_session")

    if file.filename == "":
        return jsonify({"status": "error", "error": "No selected file"}), 400

    if not (file.filename.lower().endswith(".pdf")
            or file.filename.lower().endswith(".docx")
            or file.filename.lower().endswith(".txt")):
        return jsonify({"status": "error", "error": "Only PDF, DOCX, or TXT files are allowed"}), 400

    # Save locally
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Extract text
    text_content = extract_text_from_file(filepath)

    # Convert to base64
    encoded = file_to_base64(filepath)

    # Auto-call chat for resume analysis
    ai_reply = chat(
        message="According to my resume, for which role am I a good fit?",
        session=session_id,
        resume_data=text_content.strip()
    )

    if isinstance(ai_reply, dict):
        data = ai_reply
    elif isinstance(ai_reply, str):
        try:
            data = json.loads(ai_reply)
        except json.JSONDecodeError:
            data = {"answer": ai_reply}
    else:
        data = {"answer": str(ai_reply)}

    return jsonify({
        "status": "success",
        "filename": file.filename,
        "base64_content": encoded,
        "plain_text": text_content.strip(),
        "analysis": data   # <-- result of chat_with_agent on the resume
    })


# ---------------------------
# Upload Other Documents (Project Req, etc.)
# ---------------------------
@app.route("/upload_document", methods=["POST"])
def upload_document():
    if "document" not in request.files:
        return jsonify({"error": "No document uploaded"}), 400

    file = request.files["document"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        extracted_text = extract_text_from_file(file_path)

        os.remove(file_path)

        return jsonify({
            "status": "success",
            "message": "Document uploaded and processed",
            "filename": file.filename,
            "extracted_text": extracted_text[:5000]  # Limit to avoid huge payloads
        })

    except Exception as e:
        app.logger.exception("Error processing uploaded document")
        return jsonify({"status": "error", "error": str(e)}), 500


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port, debug=True)
