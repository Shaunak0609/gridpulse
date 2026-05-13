import os
from urllib.parse import urlencode

import requests as http_requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
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


@router.get("/google/start")
def google_start():
    """
    Redirect the user to Google's login page.
    The browser follows this redirect — the user sees Google's account picker.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    """
    Google redirects the user here after they approve sign-in.
    We exchange the one-time code for tokens, verify the ID token,
    find or create the user, and redirect to the frontend with a JWT.
    """

    # Step 1: Exchange the authorization code for Google tokens
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Google auth code for tokens.",
        )

    id_token_str = token_response.json().get("id_token")
    if not id_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an ID token.",
        )

    # Step 2: Verify the ID token and extract user info
    try:
        google_payload = verify_google_id_token(id_token_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token verification failed.",
        )

    google_sub: str = google_payload["sub"]
    email: str = google_payload["email"]
    picture: str | None = google_payload.get("picture")
    display_name: str | None = google_payload.get("name")

    # Step 3: Find or create the user
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if not user:
        # Check if a local account already exists with this email
        user = db.query(User).filter(User.email == email).first()

        if user:
            # Link the Google identity to the existing local account
            user.google_sub = google_sub
            user.profile_picture_url = picture
            # Keep auth_provider as "local" — the account was created that way
        else:
            # First-time Google user — create a brand new account
            user = User(
                email=email,
                username=display_name,
                google_sub=google_sub,
                auth_provider="google",
                profile_picture_url=picture,
            )
            db.add(user)
    else:
        # Returning Google user — refresh their profile picture in case it changed
        user.profile_picture_url = picture

    db.commit()
    db.refresh(user)

    # Step 4: Issue our own JWT (same format as password login)
    gridpulse_token = create_access_token(data={"sub": user.email})

    # Step 5: Send the token to the frontend via redirect
    # The frontend reads it from the URL and stores it in localStorage
    return RedirectResponse(
        f"{FRONTEND_URL}/auth/google/callback?token={gridpulse_token}"
    )
