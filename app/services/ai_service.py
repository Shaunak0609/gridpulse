import os

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

_SYSTEM_PROMPT = """\
You are the GridPulse AI Race Assistant. Answer questions using ONLY the data in
the CONTEXT block. Do not use outside knowledge to fill in race data. Do not invent
results, lap times, pit stops, compounds, penalties, retirements, or classifications.

== HOW TO RESPOND ==

1. DATA IN CONTEXT → Use it directly. Quote figures as they appear.
2. GENERAL F1 KNOWLEDGE (rules, concepts, history) → Answer, then add:
   "This is general F1 knowledge, not data from GridPulse."
3. MISSING OR NOT IN CONTEXT → State exactly what is missing. Never guess.

== MISSING-DATA FLAGS ==

Each session block may show: Missing: no_lap_data / no_stint_data /
no_race_control_data / no_weather_data.
If a flag is listed, that data was not synced. State this clearly — do not guess.

== DATA AVAILABLE FOR SYNCED SESSIONS ==

LAP DATA: aggregate counts + per-driver max lap number.
  For qualifying/FP: "Per-driver laps" table shows max lap per car number.
  For race/sprint: per-driver data is in the finishing order.

FINISHING ORDER (race/sprint only): derived from lap timing — not official.
  Always qualify as "based on synced lap data". Post-race penalties not reflected.
  Drivers with max_lap below the leader were lapped or retired (DNF).

TYRE STRATEGY: compound, lap range, tyre age per stint per driver.
  Answer tyre questions only from this section. If no_stint_data: say so.

RACE CONTROL: key-events bullet list (always complete, all event types with lap
  numbers) + curated chronological messages (blue-flag lapping messages excluded).
  If omitted messages noted, say: "Full log is on the GridPulse session detail page."
  If no_race_control_data: say so.

WEATHER: session range (temp min/max, rain) + latest reading (humidity, wind).
  If no_weather_data: say so.

DRIVER NUMBER REFERENCE: car number → name + team for decoding RC messages.

== WHAT GRIDPULSE DOES NOT HAVE ==

No official classifications, qualifying results, grid positions, pole times,
individual lap times, pit stop durations, live timing, or car telemetry.
Points totals do NOT tell you who won a race — check the finishing order.

== CRITICAL RULES ==

- Never invent race data. If a section is missing-flagged, say exactly what is missing.
- Never say "currently" or "right now" — GridPulse has no live feed.
- Never say you are "checking", "fetching", or "looking up" — you only have the CONTEXT.
- Never infer race wins from championship points.
- Be concise: one short paragraph or a brief bulleted list.\
"""


def _call_groq(full_prompt: str) -> tuple[str, int]:
    from groq import APIError, AuthenticationError, Groq, RateLimitError

    client = Groq(api_key=AI_API_KEY)
    try:
        completion = client.chat.completions.create(
            model=AI_MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ],
        )
    except AuthenticationError:
        return "The AI API key is invalid or expired. Check AI_API_KEY in your .env file.", 0
    except RateLimitError:
        return "The AI API rate limit was reached. Please wait a moment and try again.", 0
    except APIError as e:
        return f"The AI service returned an error: {e}", 0

    response_text = completion.choices[0].message.content or ""
    tokens_used = completion.usage.prompt_tokens + completion.usage.completion_tokens
    return response_text, tokens_used


def _call_anthropic(full_prompt: str) -> tuple[str, int]:
    import anthropic

    client = anthropic.Anthropic(api_key=AI_API_KEY)
    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}],
        )
    except anthropic.AuthenticationError:
        return "The AI API key is invalid or expired. Check AI_API_KEY in your .env file.", 0
    except anthropic.RateLimitError:
        return "The AI API rate limit was reached. Please wait a moment and try again.", 0
    except anthropic.APIError as e:
        msg = str(e)
        if "credit balance" in msg.lower():
            return "The AI API account has no credits. Add credits at console.anthropic.com to enable the Race Assistant.", 0
        return f"The AI service returned an error: {e}", 0

    response_text = message.content[0].text
    tokens_used = message.usage.input_tokens + message.usage.output_tokens
    return response_text, tokens_used


_PROVIDERS: dict[str, object] = {
    "groq": _call_groq,
    "anthropic": _call_anthropic,
}


def generate_ai_response(prompt: str, context: str) -> tuple[str, int]:
    """
    Send a user prompt to the configured AI provider, grounded in the supplied
    context string built from the GridPulse database.

    Returns (response_text, total_tokens_used).
    Never raises — errors are returned as readable messages with 0 tokens.
    """
    if not AI_API_KEY:
        return (
            "AI_API_KEY is not configured. Add it to your .env file to enable "
            "the AI Race Assistant. See .env.example for instructions."
        ), 0

    caller = _PROVIDERS.get(AI_PROVIDER)
    if caller is None:
        supported = ", ".join(_PROVIDERS)
        return f"Unknown AI_PROVIDER '{AI_PROVIDER}'. Supported: {supported}.", 0

    full_prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{prompt}"
    return caller(full_prompt)  # type: ignore[operator]
