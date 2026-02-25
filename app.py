import os
import json
import time
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# ── Load .env for local dev ─────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ════════════════════════════════════════
#  AWS SECRETS MANAGER LOADER (SAFE)
# ════════════════════════════════════════
def load_aws_secrets(
    secret_name: str = "tata-car-advisor",
    region: str = os.getenv("AWS_REGION", "us-east-1"),
) -> None:
    """
    Loads secrets only if running inside AWS.
    Safe fallback for local development.
    """
    try:
        import boto3

        if not os.getenv("AWS_EXECUTION_ENV"):
            # Not running inside AWS
            print("  ℹ️  Not in AWS environment — skipping Secrets Manager")
            return

        client = boto3.client("secretsmanager", region_name=region)
        payload = client.get_secret_value(SecretId=secret_name)
        secrets = json.loads(payload["SecretString"])

        for key, value in secrets.items():
            os.environ[key] = value

        print(f"  ✅ Secrets Manager: loaded {list(secrets.keys())}")

    except Exception as e:
        print(f"  ℹ️  Secrets Manager skipped ({type(e).__name__}) — using env vars")


# Load secrets if in AWS
load_aws_secrets()

# ── Import app modules ─────────────────────────────────
from agents import GeminiAgent, GroqAgent, run_agent
from tools import get_tata_cars

# ── Flask app setup ────────────────────────────────────
app = Flask(__name__, static_folder="static")
CORS(app)

# ── Initialize AI agents ───────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

gemini_agent = None
groq_agent = None

print("\n🚗 Tata Car Advisor — Starting up\n")

if GEMINI_API_KEY:
    try:
        gemini_agent = GeminiAgent(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"⚠️ Gemini init failed: {e}")

if GROQ_API_KEY:
    try:
        groq_agent = GroqAgent(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"⚠️ Groq init failed: {e}")


# ════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "gemini_enabled": gemini_agent is not None,
        "groq_enabled": groq_agent is not None,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "query is required"}), 400

    start = time.time()

    result = run_agent(
        query=query,
        gemini_agent=gemini_agent,
        groq_agent=groq_agent,
        force_groq=data.get("force_groq", False),
    )

    elapsed = round(time.time() - start, 2)

    if result.error:
        return jsonify({
            "error": result.error,
            "provider": result.provider
        }), 500

    return jsonify({
        "answer": result.answer,
        "tool_log": result.tool_log,
        "model": result.model,
        "provider": result.provider,
        "fallback_used": result.fallback_used,
        "elapsed_seconds": elapsed,
    })


@app.route("/api/filter", methods=["POST"])
def filter_cars():
    d = request.json or {}
    result = get_tata_cars(
        budget_min_lakhs=float(d.get("budget_min", 0)),
        budget_max_lakhs=float(d.get("budget_max", 100)),
        fuel_preference=d.get("fuel", "any"),
        min_seats=int(d.get("seats", 4)),
    )
    return jsonify(result)


# ════════════════════════════════════════
#  Local Run Only
# ════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)