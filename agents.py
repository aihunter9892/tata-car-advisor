"""
agents.py
Two agentic loops:
  • GeminiAgent  — uses google-genai SDK  (primary)
  • GroqAgent    — uses groq SDK          (fallback on 429)

Both expose a common .run(query) → AgentResult interface.
The run_agent() function wraps both with automatic fallback.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from tools import dispatch

# ─────────────────────────────────────────────
# Lazy Imports
# ─────────────────────────────────────────────
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
# SYSTEM PROMPT
# ══════════════════════════════════════════
SYSTEM_PROMPT = """
You are the Tata Car Buying Advisor — an expert agentic AI helping
Indian customers choose the perfect Tata Motors car.

STRICT SCOPE:
You ONLY advise on Tata Motors vehicles.

Follow these steps:
1. CALL get_city_weather()
2. CALL get_tata_cars()
3. CALL get_fuel_price()
4. CALL calculate_tco()
5. SYNTHESIZE

Respond warmly and clearly.
"""


# ══════════════════════════════════════════
# RESULT DATACLASS
# ══════════════════════════════════════════
@dataclass
class AgentResult:
    answer: str
    tool_log: list = field(default_factory=list)
    model: str = ""
    provider: str = ""
    fallback_used: bool = False
    error: Optional[str] = None


# ══════════════════════════════════════════
# GEMINI TOOL SCHEMAS (ENUM SAFE)
# ══════════════════════════════════════════
def _build_gemini_tools():
    if not _GEMINI_AVAILABLE:
        return None

    return gtypes.Tool(function_declarations=[

        gtypes.FunctionDeclaration(
            name="get_city_weather",
            description="Get weather and terrain data for an Indian city.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "city": {
                        "type": "STRING",
                        "description": "Indian city name"
                    }
                },
                "required": ["city"],
            },
        ),

        gtypes.FunctionDeclaration(
            name="get_tata_cars",
            description="Filter Tata cars by budget, fuel type, and seats.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "budget_min_lakhs": {"type": "NUMBER"},
                    "budget_max_lakhs": {"type": "NUMBER"},
                    "fuel_preference": {"type": "STRING"},
                    "min_seats": {"type": "INTEGER"},
                },
                "required": ["budget_min_lakhs", "budget_max_lakhs"],
            },
        ),

        gtypes.FunctionDeclaration(
            name="get_fuel_price",
            description="Get fuel price in city.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "city": {"type": "STRING"},
                    "fuel_type": {"type": "STRING"},
                },
                "required": ["city", "fuel_type"],
            },
        ),

        gtypes.FunctionDeclaration(
            name="calculate_tco",
            description="Calculate total cost of ownership.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "car_name": {"type": "STRING"},
                    "city": {"type": "STRING"},
                    "daily_km": {"type": "NUMBER"},
                    "ownership_years": {"type": "INTEGER"},
                    "fuel_type": {"type": "STRING"},
                },
                "required": ["car_name", "city", "daily_km"],
            },
        ),
    ])


# ══════════════════════════════════════════
# GEMINI AGENT
# ══════════════════════════════════════════
class GeminiAgent:

    MODEL = "gemini-2.5-flash"
    MAX_STEPS = 10

    def __init__(self, api_key: str):
        if not _GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed")
        self.client = genai.Client(api_key=api_key)
        self.tools = _build_gemini_tools()
        print(f"  ✅ GeminiAgent ready ({self.MODEL})")

    def run(self, query: str) -> AgentResult:

        contents = [
            gtypes.Content(
                role="user",
                parts=[gtypes.Part.from_text(text=query)]
            )
        ]

        config = gtypes.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[self.tools],
            temperature=0.1,
            max_output_tokens=4096,
        )

        tool_log = []

        for step in range(self.MAX_STEPS):

            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            content = candidate.content

            calls = [p.function_call for p in content.parts if p.function_call]
            texts = [p.text for p in content.parts if p.text]

            if calls:
                contents.append(gtypes.Content(role="model", parts=content.parts))
                tool_parts = []

                for fc in calls:
                    result = dispatch(fc.name, dict(fc.args))
                    tool_log.append({
                        "step": step + 1,
                        "tool": fc.name,
                        "args": dict(fc.args),
                    })
                    tool_parts.append(
                        gtypes.Part.from_function_response(
                            name=fc.name,
                            response={"result": result},
                        )
                    )

                contents.append(gtypes.Content(role="tool", parts=tool_parts))

            elif texts:
                return AgentResult(
                    answer="\n".join(texts),
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="gemini",
                )

        return AgentResult(
            answer="Gemini reached max steps.",
            tool_log=tool_log,
            model=self.MODEL,
            provider="gemini",
        )


# ══════════════════════════════════════════
# GROQ AGENT
# ══════════════════════════════════════════
class GroqAgent:

    MODEL = "llama-3.3-70b-versatile"
    MAX_STEPS = 10

    def __init__(self, api_key: str):
        if not _GROQ_AVAILABLE:
            raise ImportError("groq not installed")
        self.client = _groq_lib.Groq(api_key=api_key)
        print(f"  ✅ GroqAgent ready ({self.MODEL})")

    def run(self, query: str) -> AgentResult:

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        tool_log = []

        for step in range(self.MAX_STEPS):

            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                tools=None,
                max_tokens=4096,
                temperature=0.1,
            )

            msg = response.choices[0].message

            if msg.content:
                return AgentResult(
                    answer=msg.content,
                    tool_log=tool_log,
                    model=self.MODEL,
                    provider="groq",
                )

        return AgentResult(
            answer="Groq reached max steps.",
            tool_log=tool_log,
            model=self.MODEL,
            provider="groq",
        )


# ══════════════════════════════════════════
# AUTO FALLBACK RUNNER
# ══════════════════════════════════════════
def run_agent(
    query: str,
    gemini_agent: Optional[GeminiAgent] = None,
    groq_agent: Optional[GroqAgent] = None,
    force_groq: bool = False,
) -> AgentResult:

    if force_groq and groq_agent:
        return groq_agent.run(query)

    if gemini_agent:
        try:
            return gemini_agent.run(query)
        except Exception as e:
            if groq_agent:
                result = groq_agent.run(query)
                result.fallback_used = True
                return result
            return AgentResult(answer="", error=str(e), provider="gemini")

    if groq_agent:
        return groq_agent.run(query)

    return AgentResult(
        answer="No AI provider available.",
        provider="none",
        error="Missing API keys",
    )