# backend/app.py
import os
import uuid
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from gemini_client import GeminiClient

# Load environment variables from .env file in the backend directory
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

app = Flask(__name__, template_folder="../templates")
app.secret_key = "your-secret-key-change-in-production"  # Change this in production

# Initialize the Gemini client
gemini_client = GeminiClient()


@app.route("/")
def index():
    """Render the main chat interface."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages from the frontend."""
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        session_id = data.get("session_id")

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Generate or use existing session ID
        if not session_id:
            session_id = str(uuid.uuid4())

        # Get response from Gemini client (with session persistence)
        response = gemini_client.chat(user_message, session_id=session_id)

        return jsonify({
            "response": response,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the conversation history."""
    try:
        gemini_client.reset_conversation()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

