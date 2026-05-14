import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")


def send_email(to: str, subject: str, body: str) -> None:
    """
    Send a plain-text email via Resend.

    Raises RuntimeError if the API key is not configured or the send fails.
    """
    if not resend.api_key:
        raise RuntimeError(
            "RESEND_API_KEY is not set. Add it to your .env file."
        )
    if not EMAIL_FROM:
        raise RuntimeError(
            "EMAIL_FROM is not set. Add it to your .env file."
        )

    try:
        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "text": body,
        })
    except Exception as e:
        raise RuntimeError(f"Resend could not deliver the email: {e}") from e
