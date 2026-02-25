"""
app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thin Flask server. No business logic here —
it just wires the HTTP layer to agents.py and tools.py.

Run:
    pip install -r requirements.txt
    cp .env.example .env   # add your API keys
    python app.py

Open: http://localhost:5000

Routes:
    GET  /                 → index.html
    GET  /api/status       → Gemini + Groq health check
    POST /api/chat         → run agentic loop (auto-fallback)
    POST /api/filter       → filter cars without AI (sidebar search)
"""

import os
import time
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Import our modules ──────────────────────────────────────────
from agents import GeminiAgent, GroqAgent, run_agent
from tools  import get_tata_cars
from database import TATA_CARS_DB

# ── App setup ───────────────────────────────────────────────────
app = Flask(__name__, static_folder="static")
CORS(app)

# ── Initialise agents once at startup ───────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "")

gemini_agent = None
groq_agent   = None

print("\n" + "═" * 52)
print("  🚗  Tata Car Advisor — Starting up")
print("═" * 52)

if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    try:
        gemini_agent = GeminiAgent(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"  ⚠️  Gemini init failed: {e}")
else:
    print("  ⚠️  GEMINI_API_KEY not set — Gemini disabled")

if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY_HERE":
    try:
        groq_agent = GroqAgent(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"  ⚠️  Groq init failed: {e}")
else:
    print("  ⚠️  GROQ_API_KEY not set — Groq disabled")

print(f"\n  Open: http://localhost:5000")
print("═" * 52 + "\n")


# ════════════════════════════════════════
#  GUARDRAIL — Competitor Brand Filter
#  Layer 1: Hard block before LLM is called
#  (zero API cost, fully deterministic)
# ════════════════════════════════════════

# Add/remove brands here as needed
COMPETITOR_BRANDS = {
    # Maruti Suzuki
    "maruti", "suzuki", "swift", "baleno", "brezza", "ertiga",
    "wagon r", "alto", "dzire", "vitara", "fronx", "jimny",
    # Hyundai / Kia
    "hyundai", "kia", "creta", "venue", "i20", "i10",
    "grand i10", "verna", "tucson", "sonet", "seltos", "carens",
    # Honda
    "honda", "city", "amaze", "elevate", "jazz",
    # Mahindra
    "mahindra", "scorpio", "thar", "xuv", "bolero",
    # Toyota / Suzuki joint
    "toyota", "innova", "fortuner", "urban cruiser", "hyryder",
    # Others
    "mg", "morris garages", "hector", "astor", "gloster",
    "volkswagen", "vw", "taigun", "virtus",
    "skoda", "kushaq", "slavia",
    "renault", "kiger", "triber",
    "nissan", "magnite",
    "jeep", "compass", "meridian",
    "ford", "bmw", "mercedes", "audi", "volvo",
    "citroen", "peugeot", "ola electric", "ather",
}

def check_competitor_mention(query: str) -> str | None:
    """
    Scan the query for any competitor brand keyword.

    Returns a polite refusal string if a competitor is detected,
    or None if the query is clean and should proceed to the agent.

    This runs BEFORE the LLM — no API tokens consumed on blocked queries.
    """
    query_lower = query.lower()

    for brand in COMPETITOR_BRANDS:
        if brand in query_lower:
            # Capitalise the matched brand nicely for the response
            display_name = brand.title()
            print(f"  [GUARDRAIL] Blocked competitor mention: '{brand}' in query")
            return (
                f"I'm your dedicated Tata Motors advisor and I'm not able to "
                f"compare with or advise on {display_name} vehicles. "
                f"For {display_name} models, their official website or a multi-brand "
                f"platform like CarDekho would be a better resource.\n\n"
                f"What I *can* do is help you find the best Tata car that fits your "
                f"needs — just share your city, budget, and how you plan to use the car!"
            )
    return None   # query is clean


# ════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status")
def api_status():
    """
    Check which AI providers are live right now.
    Called by the frontend every 25 seconds to update the status pills.
    """
    out = {
        "gemini":    False,
        "groq":      False,
        "timestamp": datetime.now().isoformat(),
    }

    if gemini_agent:
        try:
            # Cheap ping — single token response
            gemini_agent.client.models.generate_content(
                model=gemini_agent.MODEL,
                contents="ping"
            )
            out["gemini"] = True
        except Exception as e:
            out["gemini_error"] = str(e)[:100]

    if groq_agent:
        try:
            groq_agent.client.chat.completions.create(
                model=groq_agent.MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=3,
            )
            out["groq"] = True
        except Exception as e:
            out["groq_error"] = str(e)[:100]

    return jsonify(out)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Run the full agentic loop and return the recommendation.

    Request JSON:
        { "query": "...", "force_groq": false }

    Response JSON:
        { "answer": "...", "tool_log": [...], "model": "...",
          "provider": "gemini|groq|guardrail", "fallback_used": bool,
          "elapsed_seconds": float }
    """
    data  = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "query is required"}), 400

    # ── Layer 1 Guardrail: block competitor brand questions ──────
    # Runs before the LLM — zero API cost, instant response
    refusal = check_competitor_mention(query)
    if refusal:
        return jsonify({
            "answer":          refusal,
            "tool_log":        [],
            "model":           "guardrail",
            "provider":        "guardrail",
            "fallback_used":   False,
            "elapsed_seconds": 0.0,
        })
    # ────────────────────────────────────────────────────────────

    t0     = time.time()
    result = run_agent(
        query        = query,
        gemini_agent = gemini_agent,
        groq_agent   = groq_agent,
        force_groq   = data.get("force_groq", False),
    )
    elapsed = round(time.time() - t0, 1)

    if result.error:
        return jsonify({"error": result.error, "provider": result.provider}), 500

    return jsonify({
        "answer":          result.answer,
        "tool_log":        result.tool_log,
        "model":           result.model,
        "provider":        result.provider,
        "fallback_used":   result.fallback_used,
        "elapsed_seconds": elapsed,
    })


@app.route("/api/filter", methods=["POST"])
def filter_cars():
    """
    Filter cars without AI — pure database lookup.
    Used by the sidebar Search button.

    Request JSON:
        { "budget_min": 8.0, "budget_max": 16.0,
          "fuel": "Petrol", "seats": 4 }
    """
    d      = request.json or {}
    result = get_tata_cars(
        budget_min_lakhs = float(d.get("budget_min", 0)),
        budget_max_lakhs = float(d.get("budget_max", 100)),
        fuel_preference  = d.get("fuel", "any"),
        min_seats        = int(d.get("seats", 4)),
    )
    return jsonify(result)


# ════════════════════════════════════════
#  RUN
# ════════════════════════════════════════
if __name__ == "__main__":
    app.run(debug=True, port=5000)