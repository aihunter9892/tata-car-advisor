"""
agents.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Two agentic loops:
  • GeminiAgent  — uses google-genai SDK  (primary)
  • GroqAgent    — uses groq SDK           (fallback on 429)

Both expose a common .run(query) → AgentResult interface.
The run_agent() function wraps both with automatic fallback.

Debug tip:  python agents.py
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from tools import dispatch

# ── Lazy imports (don't crash if a key is missing) ──────────────
try:
    from google import genai
    from google.genai import types as gtypes
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

try:
    import groq as _groq_lib
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False


# ══════════════════════════════════════════
#  SHARED SYSTEM PROMPT
# ══════════════════════════════════════════
SYSTEM_PROMPT = """
You are the Tata Car Buying Advisor — an expert agentic AI helping
Indian customers choose the perfect Tata Motors car.

## STRICT SCOPE GUARDRAIL
You ONLY advise on Tata Motors vehicles. If the user asks about or requests
comparisons with ANY other brand (Maruti Suzuki, Hyundai, Honda, Mahindra,
Kia, Toyota, Ford, etc.), politely decline and redirect.

Response for out-of-scope brand questions:
"I'm specifically trained as a Tata Motors advisor and can only provide
recommendations within the Tata lineup. For a comparison with [brand],
I'd suggest visiting that brand's website. What I *can* do is help you
find the best Tata car for your needs — shall we do that?"

## Steps (always follow in order):
1. CALL get_city_weather()  — understand local heat, humidity, terrain
2. CALL get_tata_cars()     — filter by budget, fuel preference, seats
3. CALL get_fuel_price()    — get running costs for their specific city
4. CALL calculate_tco()     — calculate monthly cost for top 2–3 cars
5. SYNTHESIZE               — give a clear, ranked recommendation

## Response format:
🥇 TOP PICK     — name · why it suits them · monthly total cost
🥈 RUNNER-UP    — alternative with key trade-offs
📊 Cost table   — car | ex-showroom | monthly total
⚠️  One caveat  — e.g. EV charging infra, diesel suitability, AC limits

## Tone: Warm and confident — like a trusted friend at a showroom.
Use Indian context: ex-showroom price, EMI, lakhs, kmpl."""


# ══════════════════════════════════════════
#  RESULT DATACLASS
# ══════════════════════════════════════════
@dataclass
class AgentResult:
    answer:        str
    tool_log:      list = field(default_factory=list)
    model:         str  = ""
    provider:      str  = ""        # 'gemini' | 'groq'
    fallback_used: bool = False
    error:         Optional[str] = None


# ══════════════════════════════════════════
#  GEMINI TOOL SCHEMAS
# ══════════════════════════════════════════
def _build_gemini_tools():
    """Build the Gemini FunctionDeclaration list. Called once at startup."""
    if not _GEMINI_AVAILABLE:
        return None
    return gtypes.Tool(function_declarations=[
        gtypes.FunctionDeclaration(
            name="get_city_weather",
            description="Get weather and terrain data for an Indian city to inform car recommendations.",
            parameters_json_schema={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "Indian city name"}},
                "required": ["city"],
            },
        ),
        gtypes.FunctionDeclaration(
            name="get_tata_cars",
            description="Filter all Tata Motors cars by budget range, fuel type, and seat count.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "budget_min_lakhs": {"type": "number", "description": "Min budget in lakhs"},
                    "budget_max_lakhs": {"type": "number", "description": "Max budget in lakhs"},
                    "fuel_preference":  {"type": "string", "description": "Petrol/Diesel/CNG/EV/any"},
                    "min_seats":        {"type": "integer", "description": "Minimum seats needed"},
                },
                "required": ["budget_min_lakhs", "budget_max_lakhs"],
            },
        ),
        gtypes.FunctionDeclaration(
            name="get_fuel_price",
            description="Get today's petrol/diesel/CNG price per litre in an Indian city.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "city":      {"type": "string"},
                    "fuel_type": {"type": "string", "description": "Petrol/Diesel/CNG"},
                },
                "required": ["city", "fuel_type"],
            },
        ),
        gtypes.FunctionDeclaration(
            name="calculate_tco",
            description="Calculate Total Cost of Ownership for a specific Tata car (EMI + fuel + insurance + maintenance).",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "car_name":        {"type": "string", "description": "Exact Tata car name"},
                    "city":            {"type": "string"},
                    "daily_km":        {"type": "number", "description": "Daily km driven"},
                    "ownership_years": {"type": "integer", "description": "Years to project (default 5)"},
                    "fuel_type":       {"type": "string", "description": "Petrol/Diesel/CNG/EV"},
                },
                "required": ["car_name", "city", "daily_km"],
            },
        ),
    ])


# ══════════════════════════════════════════
#  GROQ TOOL SCHEMAS  (OpenAI format)
# ══════════════════════════════════════════
GROQ_TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_city_weather",
        "description": "Get weather and terrain data for an Indian city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_tata_cars",
        "description": "Filter Tata Motors cars by budget, fuel type, and seats.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget_min_lakhs": {"type": "number"},
                "budget_max_lakhs": {"type": "number"},
                "fuel_preference":  {"type": "string"},
                "min_seats":        {"type": "integer"},
            },
            "required": ["budget_min_lakhs", "budget_max_lakhs"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_fuel_price",
        "description": "Get today's petrol/diesel/CNG price per litre in an Indian city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city":      {"type": "string"},
                "fuel_type": {"type": "string"},
            },
            "required": ["city", "fuel_type"],
        },
    }},
    {"type": "function", "function": {
        "name": "calculate_tco",
        "description": "Calculate Total Cost of Ownership for a Tata car.",
        "parameters": {
            "type": "object",
            "properties": {
                "car_name":        {"type": "string"},
                "city":            {"type": "string"},
                "daily_km":        {"type": "number"},
                "ownership_years": {"type": "integer"},
                "fuel_type":       {"type": "string"},
            },
            "required": ["car_name", "city", "daily_km"],
        },
    }},
]


# ══════════════════════════════════════════
#  GEMINI AGENT
# ══════════════════════════════════════════
class GeminiAgent:
    """
    Agentic loop backed by Gemini 2.5 Flash.
    Uses google-genai multi-turn tool-calling protocol.
    """
    MODEL = "gemini-2.5-flash"
    MAX_STEPS = 12

    def __init__(self, api_key: str):
        if not _GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
        self.client = genai.Client(api_key=api_key)
        self.tools  = _build_gemini_tools()
        print(f"  ✅ GeminiAgent ready  ({self.MODEL})")

    def run(self, query: str) -> AgentResult:
        """Execute the agentic loop for a user query."""
        print(f"\n[GeminiAgent] Starting loop for: {query[:80]}...")

        contents = [gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=query)])]
        config   = gtypes.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.tools],
            temperature=0.1,
            max_output_tokens=4096,
        )
        tool_log = []

        for step in range(self.MAX_STEPS):
            print(f"  [Step {step + 1}] Calling Gemini...")
            response  = self.client.models.generate_content(
                model=self.MODEL, contents=contents, config=config)
            candidate = response.candidates[0]
            content   = candidate.content
            calls     = [p.function_call for p in content.parts if p.function_call]
            texts     = [p.text          for p in content.parts if p.text]

            if calls:
                print(f"  [Step {step + 1}] Gemini wants {len(calls)} tool call(s)")
                contents.append(gtypes.Content(role="model", parts=content.parts))
                tr_parts = []
                for fc in calls:
                    res = dispatch(fc.name, dict(fc.args))
                    tool_log.append({
                        "step": step + 1,
                        "tool": fc.name,
                        "args": dict(fc.args),
                    })
                    tr_parts.append(gtypes.Part.from_function_response(
                        name=fc.name, response={"result": res}))
                contents.append(gtypes.Content(role="tool", parts=tr_parts))

            elif texts:
                print(f"  [Step {step + 1}] Gemini has final answer ({len(tool_log)} tool calls made)")
                return AgentResult(
                    answer="\n".join(texts),
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="gemini",
                )
            else:
                print(f"  [Step {step + 1}] Unexpected finish — stopping")
                break

        return AgentResult(
            answer="Agent reached maximum steps without a final answer.",
            tool_log=tool_log,
            model=self.MODEL,
            provider="gemini",
        )


# ══════════════════════════════════════════
#  GROQ AGENT
# ══════════════════════════════════════════
class GroqAgent:
    """
    Agentic loop backed by Groq Llama-3.3-70b-versatile.
    Uses OpenAI-compatible tool-calling protocol.
    """
    MODEL     = "llama-3.3-70b-versatile"
    MAX_STEPS = 12

    def __init__(self, api_key: str):
        if not _GROQ_AVAILABLE:
            raise ImportError("groq not installed. Run: pip install groq")
        self.client = _groq_lib.Groq(api_key=api_key)
        print(f"  ✅ GroqAgent ready    ({self.MODEL})")

    def run(self, query: str) -> AgentResult:
        """Execute the agentic loop for a user query."""
        print(f"\n[GroqAgent] Starting loop for: {query[:80]}...")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": query},
        ]
        tool_log = []

        for step in range(self.MAX_STEPS):
            print(f"  [Step {step + 1}] Calling Groq...")
            response      = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                tools=GROQ_TOOL_SCHEMAS,
                tool_choice="auto",
                max_tokens=4096,
                temperature=0.1,
            )
            msg           = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            messages.append(msg)

            if finish_reason == "tool_calls" and msg.tool_calls:
                print(f"  [Step {step + 1}] Groq wants {len(msg.tool_calls)} tool call(s)")
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)
                    res     = dispatch(fn_name, fn_args)
                    tool_log.append({
                        "step": step + 1,
                        "tool": fn_name,
                        "args": fn_args,
                    })
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      res,
                    })

            elif msg.content:
                print(f"  [Step {step + 1}] Groq has final answer ({len(tool_log)} tool calls made)")
                return AgentResult(
                    answer=msg.content,
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="groq",
                )
            else:
                print(f"  [Step {step + 1}] Unexpected finish ({finish_reason}) — stopping")
                break

        return AgentResult(
            answer="Agent reached maximum steps without a final answer.",
            tool_log=tool_log,
            model=self.MODEL,
            provider="groq",
        )


# ══════════════════════════════════════════
#  UNIFIED RUNNER WITH AUTO-FALLBACK
# ══════════════════════════════════════════
_QUOTA_KEYWORDS = {"429", "RESOURCE_EXHAUSTED", "quota", "rate_limit", "rate limit"}


def run_agent(
    query:        str,
    gemini_agent: Optional[GeminiAgent] = None,
    groq_agent:   Optional[GroqAgent]   = None,
    force_groq:   bool                  = False,
) -> AgentResult:
    """
    Try GeminiAgent first; automatically fall back to GroqAgent on any
    quota / rate-limit error (HTTP 429 / RESOURCE_EXHAUSTED).

    Args:
        query:        Natural language car-buying question
        gemini_agent: Initialised GeminiAgent (or None)
        groq_agent:   Initialised GroqAgent (or None)
        force_groq:   Skip Gemini and go straight to Groq

    Returns:
        AgentResult with answer, tool_log, provider info
    """
    if force_groq and groq_agent:
        print("[run_agent] Force-Groq mode")
        result              = groq_agent.run(query)
        result.fallback_used = False
        return result

    # ── Try Gemini ──────────────────────────────────────────────
    if gemini_agent:
        try:
            result = gemini_agent.run(query)
            return result
        except Exception as e:
            err_str   = str(e)
            is_quota  = any(kw in err_str for kw in _QUOTA_KEYWORDS)
            if not is_quota:
                # Not a quota error — surface it
                return AgentResult(answer="", error=err_str, provider="gemini")
            print(f"[run_agent] Gemini quota hit → switching to Groq")
            print(f"            ({err_str[:120]})")

    # ── Groq fallback ────────────────────────────────────────────
    if groq_agent:
        try:
            result               = groq_agent.run(query)
            result.fallback_used = True
            return result
        except Exception as e:
            return AgentResult(answer="", error=str(e), provider="groq")

    return AgentResult(
        answer="",
        error="No AI provider available. Add GEMINI_API_KEY and/or GROQ_API_KEY to .env",
        provider="none",
    )


# ══════════════════════════════════════════
#  STANDALONE TEST — run: python agents.py
# ══════════════════════════════════════════
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 55)
    print("  agents.py — standalone test")
    print("=" * 55)

    # Build whichever agents are available
    g_agent = q_agent = None
    gkey    = os.getenv("GEMINI_API_KEY", "")
    qkey    = os.getenv("GROQ_API_KEY", "")

    if gkey and gkey != "YOUR_GEMINI_API_KEY_HERE":
        try:
            g_agent = GeminiAgent(api_key=gkey)
        except Exception as e:
            print(f"  ⚠️  GeminiAgent init failed: {e}")

    if qkey and qkey != "YOUR_GROQ_API_KEY_HERE":
        try:
            q_agent = GroqAgent(api_key=qkey)
        except Exception as e:
            print(f"  ⚠️  GroqAgent init failed: {e}")

    if not g_agent and not q_agent:
        print("\n⚠️  No API keys found in .env — add GEMINI_API_KEY or GROQ_API_KEY")
        raise SystemExit(1)

    TEST_QUERY = (
        "I live in Hyderabad, daily drive 35 km. "
        "Budget ₹10–16 lakhs. Open to petrol or diesel. "
        "Family of 4. Best Tata car?"
    )

    print(f"\nTest query: {TEST_QUERY}\n")
    result = run_agent(TEST_QUERY, gemini_agent=g_agent, groq_agent=q_agent)

    print("\n" + "─" * 55)
    print(f"Provider : {result.provider}  |  Fallback: {result.fallback_used}")
    print(f"Model    : {result.model}")
    print(f"Tools    : {len(result.tool_log)} calls")
    for t in result.tool_log:
        print(f"  Step {t['step']}: {t['tool']}({list(t['args'].keys())})")
    print("\n── ANSWER ──")
    print(result.answer[:600], "..." if len(result.answer) > 600 else "")
