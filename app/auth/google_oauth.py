import os

from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


def verify_google_id_token(credential: str) -> dict:
    """
    Verify a Google ID token sent from the frontend and return the decoded payload.

    The payload contains:
      - sub           — Google's permanent unique ID for this user (google_sub)
      - email         — the user's Google email address
      - name          — the user's full display name
      - picture       — URL of the user's profile picture
      - email_verified — whether Google has verified this email

    Raises ValueError if the token is invalid, expired, or meant for a different app.
    """
    try:
        payload = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        return payload
    except ValueError as e:
        raise ValueError(f"Google token verification failed: {e}")
