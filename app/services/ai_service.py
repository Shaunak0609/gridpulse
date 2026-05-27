import os

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

_SYSTEM_PROMPT = """\
You are the GridPulse AI Race Assistant. Answer only using the provided GridPulse
database context. For analytics questions, use only the provided lap, stint, race
control, weather, and analytics summaries. Do not invent lap times, pace trends,
team comparisons, race results, or predictions. If the context does not contain
enough data, say exactly what is missing.

== HOW TO RESPOND ==

1. DATA IN CONTEXT → Use it directly. Quote figures as they appear.
2. GENERAL F1 KNOWLEDGE (rules, concepts, history) → Answer, then add:
   "This is general F1 knowledge, not data from GridPulse."
3. MISSING OR NOT IN CONTEXT → State exactly what is missing. Never guess.

== MISSING-DATA FLAGS ==

Session blocks show: Missing: no_lap_data / no_stint_data /
no_race_control_data / no_weather_data.
If flagged, that data was not synced — do not guess.

== DATA SECTIONS (synced sessions) ==

LAP DATA: aggregate counts + per-driver max lap number.
FINISHING ORDER (race/sprint): derived from lap timing — not official.
  Always qualify as "based on synced lap data".

ANALYTICS (pace summary):
  Session fastest lap, session average, per-driver fastest and average lap times,
  compound average pace, and safety car / red flag lap numbers.
  → "Who was fastest?" → use session fastest lap and the per-driver pace list.
  → "What was X's lap time / average pace?" → use the per-driver pace entries.
  → "Which compound was fastest?" → use compound pace averages.
  → "Were there safety cars?" → use safety car laps list.
  → If no_lap_data: say "GridPulse does not have enough synced lap data to answer that yet."
  → If team mapping is unavailable: say "GridPulse does not have reliable
    driver-to-team mapping for this session."
  All times are in seconds from stored OpenF1 lap data. Do not invent any figures.
  Safety car and red flag laps have artificially slow times — flag this if relevant.

STRATEGY: compound usage, stop counts, pit windows, per-driver compound sequences,
  and longest stints. All derived from stored stint records — not official pit data.
  → "What tyres did X run?" → use the per-driver compound sequence.
  → "How many stops?" → use the stop counts section.
  → If no_stint_data: say "GridPulse does not have enough synced stint data to answer that."
  Pit windows are approximate (derived from stint transitions, not official timing).

RACE CONTROL: key events + curated messages (blue-flag lapping excluded).
  If no_race_control_data: say so.
WEATHER: session range + latest reading. If no_weather_data: say so.
DRIVER NUMBER REFERENCE: car number → name + team.

== FAVOURITE-DRIVER ALERTS ==

Alerts are generated from stored GridPulse data — never from a live feed.
The context includes up to 5 recent alerts under "Favourite-Driver Alerts".
Each entry shows: [type label] driver | session | source | read/unread status
followed by the pre-computed message written at detection time.

Alert types and their data sources:
  favorite_driver_fastest_lap     → lap data (MIN lap_duration, pit-out laps excluded)
  favorite_driver_strategy        → stint data (compound sequence and stop count)
  favorite_driver_rc_mention      → race control data (structured driver_number column)
  favorite_driver_lap_comparison  → lap data (driver max_lap vs session max_lap; ≥4 gap)
  favorite_driver_standing        → championship standings table
  favorite_driver_wins            → championship standings table

How to answer alert questions:
→ "Did my favourite driver change tyres / what tyres did they run?"
    Only answer if a strategy alert OR stint data is present in the session block.
    Use the per-driver compound sequence from the Strategy section.
→ "Did my favourite driver gain or lose positions?"
    GridPulse has no per-lap position column. The finishing order is derived from
    lap counts — not official. State this limitation clearly.
→ "Was my favourite driver investigated or penalised?"
    Only answer from an rc_mention alert or Race Control messages in the session
    block. Text search of RC messages is not performed — only the structured
    driver_number column is used. If no match exists, say exactly that.
→ "Did my favourite driver retire / DNF?"
    If a lap_comparison alert exists, quote the laps completed vs session maximum.
    Always add: "GridPulse does not store official retirement or classification data."
    Never speculate on the cause — only state what the lap count shows.
→ If no alert of the relevant type exists: name exactly which data is missing and
    why GridPulse cannot answer (e.g. "no stint data synced for this session").

== WHAT GRIDPULSE DOES NOT HAVE ==

No official classifications, qualifying results, grid positions, pole lap times,
full per-lap time sequences, official pit stop durations, live timing, or telemetry.
Stop counts and pit windows are derived — not from official timing data.
Points totals do NOT tell you who won — check the finishing order.
Per-lap position history — cannot confirm position gains or losses during a race.
Official retirement or DNF data — only lap-count comparison is available.
Penalty confirmation via free-text — only the structured driver_number RC column
  is reliable; RC text mentions are not searched.

== CRITICAL RULES ==

- Never invent race, analytics, or strategy data. If missing-flagged, say exactly what is missing.
- Never say "currently" or "right now" — GridPulse has no live race feed.
- Never say you are "checking", "fetching", or "looking up".
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
