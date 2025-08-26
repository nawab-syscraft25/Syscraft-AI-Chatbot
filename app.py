# app.py

import os
from flask import Flask, request, jsonify, render_template, send_from_directory
import base64


# from agenticai_lotus import  LotusElectronicsBot
# from try_agentic import chat_with_agent

app = Flask(__name__, static_folder="static", template_folder="templates")
# allow all origins; adjust in production as needed

@app.route("/static")
def serve_static(path):
    return send_from_directory("static", path)

@app.route("/", methods=["GET"])
def index():
    # Renders templates/chatbot.html
    return render_template("chat.html")

from chat import chat as chat_with_agent
import json



@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(force=True)
    message = payload.get("message")
    session_id = payload.get("session_id", "default_session")
    resume_data = payload.get("resume_data")  # Optional resume data
    
    if not message:
        return jsonify({"error": "Missing 'message' in request"}), 400

    try:
        ai_reply = chat_with_agent(message, session_id, resume_data)
        
        # Handle different response formats
        if isinstance(ai_reply, dict):
            data = ai_reply
        elif isinstance(ai_reply, str):
            try:
                data = json.loads(ai_reply)
            except json.JSONDecodeError:
                data = {"answer": ai_reply}
        else:
            data = {"answer": str(ai_reply)}
            
        response = {
            "status": "success", 
            "data": data
        }
        return response
    except Exception as e:
        app.logger.exception("Error in chat_with_agent")
        return jsonify({"error": str(e)})

@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    """Handle resume upload for job applications."""
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Read file content and encode to base64
        file_content = file.read()
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        return jsonify({
            "status": "success",
            "filename": file.filename,
            "base64_content": base64_content,
            "message": "Resume uploaded successfully. Please provide your details to complete the application."
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    # Load PORT from env or default to 8000
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port, debug=True)
