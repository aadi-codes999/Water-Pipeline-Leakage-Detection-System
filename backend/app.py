# ============================================================
# 💧 WATER LEAKAGE DETECTION BACKEND (NO DATABASE VERSION)
# ============================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import joblib
import pandas as pd
import traceback
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from utils.blockchain import SimplePrivateBlockchain
from utils.retrain_model import retrain_model
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ------------------------------------------------------------
# 🔧 Basic Setup
# ------------------------------------------------------------
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
LOG_FILE = "server_log.json"
USER_FILE = "users.json"
UPLOAD_RECORDS = "uploads.json"
LEDGER_FILE = "ledger.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "leak_detection_model.pkl")

try:
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Model file not found at {MODEL_PATH} (will run without model).")
        model = None
    else:
        model = joblib.load(MODEL_PATH)
        print(f"✅ Model loaded successfully from {MODEL_PATH}")
except Exception as e:
    print("⚠️ Error loading model:", e)
    model = None

blockchain = SimplePrivateBlockchain()

# ------------------------------------------------------------
# 🔹 Helper Utilities
# ------------------------------------------------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f, indent=4)
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def log_event(action, username="system", details=None):
    logs = load_json(LOG_FILE, [])
    logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "username": username,
        "details": details or {}
    })
    save_json(LOG_FILE, logs)

# ------------------------------------------------------------
# 🔹 AUTH ENDPOINTS
# ------------------------------------------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "citizen")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    users = load_json(USER_FILE, [])
    if any(u["username"] == username for u in users):
        return jsonify({"error": "Username already exists"}), 409

    hashed = generate_password_hash(password)
    users.append({"username": username, "password": hashed, "role": role, "coins": 0, "reports": 0})
    save_json(USER_FILE, users)
    log_event("signup", username, {"role": role})
    return jsonify({"message": "✅ Signup successful"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    users = load_json(USER_FILE, [])
    for u in users:
        if u["username"] == username and check_password_hash(u["password"], password):
            log_event("login", username)
            return jsonify({"message": "✅ Login successful", "role": u["role"]}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "💧 Water Leakage Detection Backend is Running"}), 200

# ------------------------------------------------------------
# 🔹 ADMIN ENDPOINTS
# ------------------------------------------------------------
@app.route("/upload_dataset", methods=["POST"])
def upload_dataset():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    uploads = load_json(UPLOAD_RECORDS, [])
    uploads.append({
        "username": "admin",
        "filename": filename,
        "filetype": "dataset",
        "path": filepath,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(UPLOAD_RECORDS, uploads)

    log_event("upload_dataset", "admin", {"filename": filename})
    return jsonify({"message": "✅ Dataset uploaded successfully", "path": filepath})


@app.route("/retrain_model", methods=["POST"])
def retrain_model_endpoint():
    try:
        dataset_path = request.json.get("dataset_path")
        if not os.path.exists(dataset_path):
            return jsonify({"error": "Dataset not found"}), 404

        # Use MODEL_PATH for both existing and save path
        result = retrain_model(MODEL_PATH, dataset_path, MODEL_PATH)
        
        if result["status"] == "success":
            log_event("retrain_model", "admin", {"dataset": dataset_path})
            return jsonify({"message": "✅ Model retrained successfully"})
        else:
            return jsonify({"error": result["message"]}), 500
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/view_reports", methods=["GET"])
def view_reports():
    # Dummy data simulation
    report_data = {
        "summary": {"total_leaks": 12, "high_risk_areas": 5, "avg_confidence": 0.83},
        "graph_data": [
            {"area": "Sector 1", "confidence": 0.9},
            {"area": "Sector 2", "confidence": 0.85},
            {"area": "Sector 3", "confidence": 0.6},
        ],
        "table_data": [
            {"id": 1, "location": "Sector 1", "status": "Leak Detected"},
            {"id": 2, "location": "Sector 2", "status": "Possible Leak"},
        ]
    }
    return jsonify(report_data)


@app.route("/ledger", methods=["GET"])
def view_ledger():
    ledger = load_json(LEDGER_FILE, [])
    return jsonify({"ledger": ledger})


@app.route("/add_transaction", methods=["POST"])
def add_transaction():
    data = request.get_json()
    sender = data.get("sender")
    receiver = data.get("receiver")
    amount = data.get("amount")

    if not all([sender, receiver, amount]):
        return jsonify({"error": "Missing fields"}), 400

    new_block = blockchain.add_transaction(sender, receiver, amount)
    ledger = load_json(LEDGER_FILE, [])
    ledger.append(new_block)
    save_json(LEDGER_FILE, ledger)

    log_event("add_transaction", "admin", {"sender": sender, "receiver": receiver, "amount": amount})
    return jsonify({"message": "✅ Transaction added", "block": new_block})


@app.route("/logs", methods=["GET"])
def get_logs():
    logs = load_json(LOG_FILE, [])
    return jsonify({"logs": logs})

# ------------------------------------------------------------
# 🔹 CITIZEN ENDPOINTS
# ------------------------------------------------------------
@app.route("/citizen_profile", methods=["GET"])
def citizen_profile():
    username = request.args.get("username")
    users = load_json(USER_FILE, [])
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = {
        "username": user["username"],
        "coins": user["coins"],
        "reports": user["reports"],
        "city": "Raipur",
        "colony": "Shanti Nagar"
    }
    return jsonify(profile)


@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    username = request.form.get("username", "anonymous")
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    photo = request.files["photo"]
    filename = secure_filename(photo.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    photo.save(filepath)

    uploads = load_json(UPLOAD_RECORDS, [])
    uploads.append({
        "username": username,
        "filename": filename,
        "filetype": "photo",
        "path": filepath,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_json(UPLOAD_RECORDS, uploads)

    users = load_json(USER_FILE, [])
    for u in users:
        if u["username"] == username:
            u["reports"] += 1
            u["coins"] += 5
    save_json(USER_FILE, users)

    log_event("upload_photo", username, {"filename": filename})
    return jsonify({"message": "📷 Photo uploaded successfully", "path": filepath})


@app.route("/my_reports", methods=["GET"])
def my_reports():
    username = request.args.get("username")
    uploads = load_json(UPLOAD_RECORDS, [])
    user_reports = [u for u in uploads if u["username"] == username and u["filetype"] == "photo"]
    return jsonify({"reports": user_reports})


@app.route("/my_rewards", methods=["GET"])
def my_rewards():
    username = request.args.get("username")
    users = load_json(USER_FILE, [])
    user = next((u for u in users if u["username"] == username), None)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": username, "coins": user["coins"]})

# ------------------------------------------------------------
# 🔹 ML / PREDICTION ENDPOINTS
# ------------------------------------------------------------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Please upload a CSV file"}), 400
            
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({"error": f"Error reading CSV file: {str(e)}"}), 400
        
        if not model:
            return jsonify({"error": "Model not loaded"}), 500

        # Import flexible prediction function
        from utils.predict_leak import predict_with_flexible_columns
        
        try:
            predictions, processed_df = predict_with_flexible_columns(model, df)
            
            # Add predictions to the dataframe
            processed_df["leak_prediction"] = predictions.tolist()
            
            # Try to add confidence scores if model supports it
            try:
                confidence = model.predict_proba(processed_df)
                processed_df["leak_confidence"] = confidence[:, 1].tolist()
            except:
                pass
                
            result = processed_df.to_dict(orient="records")
            
            # Enhanced logging with more details
            log_event("predict", "admin", {
                "rows": len(result),
                "columns": list(df.columns),
                "leaks_detected": int(sum(predictions)),
                "input_columns": list(df.columns),
                "processed_columns": list(processed_df.columns)
            })
            
            return jsonify({
                "predictions": result,
                "summary": {
                    "total_records": len(predictions),
                    "leaks_detected": int(sum(predictions)),
                    "leak_percentage": f"{(sum(predictions)/len(predictions)*100):.1f}%",
                    "original_columns": list(df.columns),
                    "processed_columns": list(processed_df.columns)
                }
            })
        except ValueError as ve:
            # Catch specific column mapping errors
            return jsonify({"error": str(ve)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/report_leak", methods=["POST"])
def report_leak():
    try:
        data = request.get_json()
        leaks = data.get("leaks", [])
        log_event("report_leak", "system", {"count": len(leaks)})
        return jsonify({"message": f"✅ {len(leaks)} leaks reported successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------------------------------------------------
# 🚀 Run Server
# ------------------------------------------------------------
if __name__ == "__main__":
    print("✅ Flask backend running on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
