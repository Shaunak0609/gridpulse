import os

from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "llama-3.1-8b-instant")

_SYSTEM_PROMPT = """\
You are the GridPulse AI Race Assistant, an F1 companion that answers questions \
using data stored in the GridPulse database.

The current GridPulse data is provided below in the CONTEXT block. \
Answer questions using only that data. Be concise and helpful.

IMPORTANT LIMITATIONS — you must follow these strictly:
- GridPulse does NOT have individual race results, qualifying results, lap times, \
pit stop data, tyre compounds, or live timing.
- If the user asks about anything not present in the CONTEXT, say clearly: \
"GridPulse doesn't have that data yet."
- Do not invent race results, finishing positions, qualifying times, or any \
statistics that are not in the CONTEXT.
- You may use general F1 knowledge to explain concepts (e.g. how DRS works) \
but always clarify when you are drawing on general knowledge rather than \
GridPulse data.\
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
