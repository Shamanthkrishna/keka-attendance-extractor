from flask import Flask, request, jsonify
import threading
from main import main, log_message, start_gui
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/extract", methods=["POST"])
def extract():
    token = request.json.get("token")
    if token:
        try:
            # Start GUI in background
            threading.Thread(target=lambda: start_gui(disable_input=True), daemon=True).start()

            # Wait until log_box is initialized
            from main import log_box_ready
            log_box_ready.wait(timeout=5)  # max 5 sec wait to avoid indefinite hang

            log_message("Received token from extension")
            main(token)

            return jsonify({"status": "success"}), 200
        except Exception as e:
            log_message(f"Exception during /extract: {e}")
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "No token"}), 400



# Start Flask in a separate thread if needed
if __name__ == "__main__":
    app.run(port=5000)
