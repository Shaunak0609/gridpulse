import os
from urllib.parse import urlencode, quote

import requests as http_requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.google_oauth import verify_google_id_token
from app.auth.security import create_access_token
from app.database.database import get_db
from app.models.user import User

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

router = APIRouter(prefix="/auth", tags=["google"])


def _error_redirect(message: str) -> RedirectResponse:
    """Redirect to the frontend login page with a human-readable error message."""
    return RedirectResponse(
        f"{FRONTEND_URL}/login?error={quote(message)}"
    )


@router.get("/google/start")
def google_start():
    """Redirect the browser to Google's login page."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    db: Session = Depends(get_db),
    code: str | None = None,
    error: str | None = None,
):
    """
    Google redirects the browser here after the user approves or denies sign-in.
    On success Google sends ?code=..., on denial it sends ?error=access_denied.
    Every failure redirects to the frontend login page with a clear error message
    rather than showing a raw JSON error in the browser.
    """

    # Google sent an error (e.g. user closed the popup or denied permission)
    if error:
        return _error_redirect("Google sign-in was cancelled or denied.")

    if not code:
        return _error_redirect("No authorisation code received from Google.")

    # Step 1: Exchange the one-time code for Google tokens
    token_response = http_requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )

    if not token_response.ok:
        return _error_redirect("Failed to complete Google sign-in. Please try again.")

    id_token_str = token_response.json().get("id_token")
    if not id_token_str:
        return _error_redirect("Google did not return the expected credentials.")

    # Step 2: Verify the ID token and extract user info
    try:
        google_payload = verify_google_id_token(id_token_str)
    except ValueError:
        return _error_redirect("Google credentials could not be verified. Please try again.")

    google_sub: str = google_payload["sub"]
    email: str = google_payload["email"]
    picture: str | None = google_payload.get("picture")
    display_name: str | None = google_payload.get("name")

    # Step 3: Find or create the user
    try:
        user = db.query(User).filter(User.google_sub == google_sub).first()

        if not user:
            user = db.query(User).filter(User.email == email).first()

            if user:
                # Link Google identity to the existing local account
                user.google_sub = google_sub
                user.profile_picture_url = picture
            else:
                # First-time Google user — create a new account
                user = User(
                    email=email,
                    username=display_name,
                    google_sub=google_sub,
                    auth_provider="google",
                    profile_picture_url=picture,
                )
                db.add(user)
        else:
            # Returning Google user — refresh profile picture
            user.profile_picture_url = picture

        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        return _error_redirect("Something went wrong creating your account. Please try again.")

    # Step 4: Issue a GridPulse JWT (same format as password login)
    gridpulse_token = create_access_token(data={"sub": user.email})

    # Step 5: Redirect to the frontend callback page with the token in the URL
    return RedirectResponse(
        f"{FRONTEND_URL}/auth/google/callback?token={gridpulse_token}"
    )
