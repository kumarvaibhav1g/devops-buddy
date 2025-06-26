from flask import Flask, render_template, request, jsonify
import os
import requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# Flask setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('app', 'upload')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit

# Allowed file types
ALLOWED_EXTENSIONS = {'txt', 'log'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    query = request.form["question"]
    command_type = request.form.get("commandType", "")

    # Build the prompt based on command type
    if command_type:
        prompt = f"Suggest a {command_type} command to do the following task: '{query}'. Also, explain what the command does in one line."
    else:
        prompt = query

    # Get response from LLM
    response = ask_ai(prompt)
    return jsonify({"response": response})

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        with open(filepath, "r") as f:
            content = f.read()

        prompt = f"Analyze this log file and explain the main errors or issues:\n\n{content[:3000]}"
        analysis = ask_ai(prompt)
        return jsonify({"response": analysis})

    return jsonify({"error": "Invalid file type"}), 400

@app.route("/generate", methods=["POST"])
def generate_artifact():
    prompt = request.form["prompt"]
    full_prompt = f"You're a DevOps assistant. Write the requested configuration or code with best practices:\n\n{prompt}"
    response = ask_ai(full_prompt)
    return jsonify({"response": response})


def ask_ai(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        data = r.json()
        print("🔍 DEBUG API Response:", data)

        if r.status_code == 200 and "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return f"❌ API Error {r.status_code}: {data.get('error', 'No details')}"
    except Exception as e:
        return f"❌ Exception: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
