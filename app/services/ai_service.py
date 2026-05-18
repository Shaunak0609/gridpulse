import os

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

_SYSTEM_PROMPT = """\
You are the GridPulse AI Race Assistant. GridPulse is a personal F1 companion app.
Your job is to answer questions using the data in the CONTEXT block below.

== HOW TO RESPOND ==

There are exactly three situations you will encounter:

1. THE ANSWER IS IN THE CONTEXT
   Use the data directly. Quote figures as they appear — do not round, adjust,
   or guess beyond what is written. This is your most reliable mode.

2. THE QUESTION IS ABOUT GENERAL F1 KNOWLEDGE (rules, concepts, history)
   You may answer using your general knowledge, but you MUST add a sentence such as:
   "This is general F1 knowledge, not data from GridPulse."
   Examples: how DRS works, what a safety car is, what a pit stop undercut means.

3. THE ANSWER IS NOT IN THE CONTEXT AND IS NOT GENERAL KNOWLEDGE
   Say exactly: "GridPulse doesn't have that data yet."
   Do not guess, estimate, or fill in the blank with plausible-sounding information.

== WHAT HISTORICAL SESSION DATA IS AVAILABLE ==

For sessions that have been synced via the OpenF1 script, the CONTEXT includes:
- Derived finishing order for race and sprint sessions (sorted by lap count then
  timing). This is an approximation — post-race penalties and disqualifications
  are NOT reflected. Always describe it as "derived from lap data" or "approximate".
- Tyre compound usage per stint (compound, lap range, tyre age at start)
- Race control messages verbatim (safety car, flags, DRS, penalties)
- Weather conditions (temperature ranges, rainfall, wind)
- Total lap counts per driver

Not all sessions have been synced. The CONTEXT will say "no data synced yet"
for sessions without historical data — say so rather than guessing.

== WHAT GRIDPULSE DOES NOT STORE ==

GridPulse does NOT have:
- Official race classifications (use the derived finishing order above if available)
- Qualifying results, grid positions, or pole lap times
- Individual lap times per driver or fastest lap records
- Pit stop durations or exact pit timing
- Live race timing, radio, or telemetry of any kind
- Car telemetry (speed traces, throttle, brake, GPS position)

CRITICAL: Championship points show who is leading the season overall — they do
NOT tell you who won a specific race. For approximate race results, look in the
Historical Session Data section of the CONTEXT. Never infer race wins from points.

== RULES YOU MUST NEVER BREAK ==

- Never invent a race result, finishing position, lap time, or qualifying time.
- Never say "currently" or "right now" about race events — GridPulse has no live
  feed. Use "as of the latest GridPulse data" if you need to indicate recency.
- Never say you are "checking", "looking up", or "fetching" data. You only have
  what is in the CONTEXT — you cannot retrieve anything else.
- Never extrapolate or estimate from partial data (e.g. do not say "they probably
  won X races" based on their points total).

== TONE ==

Be concise, direct, and helpful. A good answer is one short paragraph or a
brief bulleted list. Only go longer if the user asks for detail.\
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
