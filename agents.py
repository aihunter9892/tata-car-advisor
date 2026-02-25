"""
agents.py
Two agentic loops:
  • GeminiAgent  — uses google-genai SDK  (primary)
  • GroqAgent    — uses groq SDK          (fallback on 429)
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from tools import dispatch

# ── Lazy imports ────────────────────────────────────────────────
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
#  SYSTEM PROMPT
# ══════════════════════════════════════════
SYSTEM_PROMPT = """
You are the Tata Car Buying Advisor — an expert agentic AI helping
Indian customers choose the perfect car.

## Steps (always follow in order):
1. CALL get_city_weather()  — understand local heat, humidity, terrain
2. CALL get_tata_cars()     — filter by budget, fuel preference, seats
3. CALL get_fuel_price()    — get running costs for their specific city
4. CALL calculate_tco()     — calculate monthly cost for top 2-3 cars
5. SYNTHESIZE               — give a clear, ranked recommendation

## Response format:
🥇 TOP PICK     — name · why it suits them · monthly total cost
🥈 RUNNER-UP    — alternative with key trade-offs
📊 Cost table   — car | ex-showroom | monthly total
⚠️  One caveat  — e.g. EV charging infra, diesel suitability, AC limits

## Tone: Warm and confident — like a trusted friend at a showroom.
Use Indian context: ex-showroom price, EMI, lakhs, kmpl.
"""


# ══════════════════════════════════════════
#  RESULT DATACLASS
# ══════════════════════════════════════════
@dataclass
class AgentResult:
    answer:        str
    tool_log:      list = field(default_factory=list)
    model:         str  = ""
    provider:      str  = ""
    fallback_used: bool = False
    error:         Optional[str] = None


# ══════════════════════════════════════════
#  GEMINI TOOL SCHEMAS — use gtypes.Schema with UPPERCASE types
# ══════════════════════════════════════════
def _build_gemini_tools():
    if not _GEMINI_AVAILABLE:
        return None

    return gtypes.Tool(function_declarations=[

        gtypes.FunctionDeclaration(
            name="get_city_weather",
            description="Get weather and terrain data for an Indian city to inform car recommendations.",
            parameters=gtypes.Schema(
                type="OBJECT",
                properties={
                    "city": gtypes.Schema(type="STRING", description="Indian city name e.g. Mumbai, Delhi"),
                },
                required=["city"],
            ),
        ),

        gtypes.FunctionDeclaration(
            name="get_tata_cars",
            description="Filter all Tata Motors cars by budget range, fuel type, and seat count.",
            parameters=gtypes.Schema(
                type="OBJECT",
                properties={
                    "budget_min_lakhs": gtypes.Schema(type="NUMBER",  description="Min budget in lakhs e.g. 8.0"),
                    "budget_max_lakhs": gtypes.Schema(type="NUMBER",  description="Max budget in lakhs e.g. 16.0"),
                    "fuel_preference":  gtypes.Schema(type="STRING",  description="Petrol/Diesel/CNG/EV/any"),
                    "min_seats":        gtypes.Schema(type="INTEGER", description="Minimum seats required"),
                },
                required=["budget_min_lakhs", "budget_max_lakhs"],
            ),
        ),

        gtypes.FunctionDeclaration(
            name="get_fuel_price",
            description="Get today's petrol/diesel/CNG price per litre in an Indian city.",
            parameters=gtypes.Schema(
                type="OBJECT",
                properties={
                    "city":      gtypes.Schema(type="STRING", description="Indian city name"),
                    "fuel_type": gtypes.Schema(type="STRING", description="Petrol, Diesel, or CNG"),
                },
                required=["city", "fuel_type"],
            ),
        ),

        gtypes.FunctionDeclaration(
            name="calculate_tco",
            description="Calculate Total Cost of Ownership for a specific Tata car (EMI + fuel + insurance + maintenance).",
            parameters=gtypes.Schema(
                type="OBJECT",
                properties={
                    "car_name":        gtypes.Schema(type="STRING",  description="Exact Tata car name e.g. Tata Nexon"),
                    "city":            gtypes.Schema(type="STRING",  description="Indian city name"),
                    "daily_km":        gtypes.Schema(type="NUMBER",  description="Average km driven per day"),
                    "ownership_years": gtypes.Schema(type="INTEGER", description="Years to project, default 5"),
                    "fuel_type":       gtypes.Schema(type="STRING",  description="Petrol/Diesel/CNG/EV"),
                },
                required=["car_name", "city", "daily_km"],
            ),
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

    MODEL     = "gemini-2.5-flash"
    MAX_STEPS = 12

    def __init__(self, api_key: str):
        if not _GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed. Run: pip install google-genai")
        self.client = genai.Client(api_key=api_key)
        self.tools  = _build_gemini_tools()
        print(f"  ✅ GeminiAgent ready  ({self.MODEL})")

    def run(self, query: str) -> AgentResult:
        print(f"\n[GeminiAgent] Query: {query[:80]}...")

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
                print(f"  [Step {step + 1}] Tool calls: {[c.name for c in calls]}")
                contents.append(gtypes.Content(role="model", parts=content.parts))
                tr_parts = []
                for fc in calls:
                    res = dispatch(fc.name, dict(fc.args))
                    tool_log.append({"step": step + 1, "tool": fc.name, "args": dict(fc.args)})
                    tr_parts.append(gtypes.Part.from_function_response(
                        name=fc.name, response={"result": res}))
                contents.append(gtypes.Content(role="tool", parts=tr_parts))

            elif texts:
                print(f"  [Step {step + 1}] Final answer ({len(tool_log)} tool calls)")
                return AgentResult(
                    answer="\n".join(texts),
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="gemini",
                )
            else:
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

    MODEL     = "llama-3.3-70b-versatile"
    MAX_STEPS = 12

    def __init__(self, api_key: str):
        if not _GROQ_AVAILABLE:
            raise ImportError("groq not installed. Run: pip install groq")
        self.client = _groq_lib.Groq(api_key=api_key)
        print(f"  ✅ GroqAgent ready    ({self.MODEL})")

    def run(self, query: str) -> AgentResult:
        print(f"\n[GroqAgent] Query: {query[:80]}...")

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
                print(f"  [Step {step + 1}] Tool calls: {[tc.function.name for tc in msg.tool_calls]}")
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)
                    res     = dispatch(fn_name, fn_args)
                    tool_log.append({"step": step + 1, "tool": fn_name, "args": fn_args})
                    messages.append({
                        "role":         "tool",
                        "tool_call_id": tc.id,
                        "content":      res,
                    })

            elif msg.content:
                print(f"  [Step {step + 1}] Final answer ({len(tool_log)} tool calls)")
                return AgentResult(
                    answer=msg.content,
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="groq",
                )
            else:
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

    if force_groq and groq_agent:
        print("[run_agent] Force-Groq mode")
        result               = groq_agent.run(query)
        result.fallback_used = False
        return result

    if gemini_agent:
        try:
            return gemini_agent.run(query)
        except Exception as e:
            err_str  = str(e)
            is_quota = any(kw in err_str for kw in _QUOTA_KEYWORDS)
            if not is_quota:
                return AgentResult(answer="", error=err_str, provider="gemini")
            print(f"[run_agent] Gemini quota hit → switching to Groq")

    if groq_agent:
        try:
            result               = groq_agent.run(query)
            result.fallback_used = True
            return result
        except Exception as e:
            return AgentResult(answer="", error=str(e), provider="groq")

    return AgentResult(
        answer="",
        error="No AI provider available. Add GEMINI_API_KEY and/or GROQ_API_KEY.",
        provider="none",
    )


# ══════════════════════════════════════════
#  STANDALONE TEST
# ══════════════════════════════════════════
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    g_agent = q_agent = None
    gkey = os.getenv("GEMINI_API_KEY", "")
    qkey = os.getenv("GROQ_API_KEY", "")

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
        print("\n⚠️  No API keys found — add GEMINI_API_KEY or GROQ_API_KEY to .env")
        raise SystemExit(1)

    TEST_QUERY = (
        "I live in Hyderabad, daily drive 35 km. "
        "Budget 10 to 16 lakhs. Open to petrol or diesel. "
        "Family of 4. Best car?"
    )
    print(f"\nTest query: {TEST_QUERY}\n")
    result = run_agent(TEST_QUERY, gemini_agent=g_agent, groq_agent=q_agent)
    print(f"\nProvider: {result.provider} | Fallback: {result.fallback_used}")
    print(f"Tools: {len(result.tool_log)} calls")
    print("\n── ANSWER ──")
    print(result.answer[:800])