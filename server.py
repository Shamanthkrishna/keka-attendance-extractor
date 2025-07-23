from flask import Flask, request, jsonify, send_from_directory, render_template_string
import threading
from main import main, log_message, start_gui
from flask_cors import CORS
from waitress import serve
import os


app = Flask(__name__)
CORS(app)

@app.route("/extract", methods=["POST"])
def extract():
    token = request.json.get("token")
    if token:
        try:
            log_message("Received token from extension", level="info")
            main(token)
            report_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "Report"))
            report_url = "http://localhost:5000/report"
            return jsonify({"status": "success", "report_url": report_url}), 200
        except Exception as e:
            log_message(f"Exception during /extract: {e}", level="error")
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "No token"}), 400

@app.route("/report")
def report_listing():
    report_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "Report"))
    files = os.listdir(report_folder)
    # Only show files (not subfolders)
    files = [f for f in files if os.path.isfile(os.path.join(report_folder, f))]
    # Simple HTML template without hyperlinks
    html = """
    <h2>Attendance Reports</h2>
    <p><b>Report folder:</b> {{ folder_path }}</p>
    <ul>
    {% for file in files %}
      <li>{{ file }}</li>
    {% endfor %}
    </ul>
    """
    return render_template_string(html, files=files, folder_path=report_folder)

@app.route("/report/<path:filename>")
def download_report(filename):
    report_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "Report"))
    return send_from_directory(report_folder, filename)


# Start Flask in a separate thread if needed
if __name__ == "__main__":
    log_message("Flask server is starting on port 5000")
    serve(app, port=5000)
