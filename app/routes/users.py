import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import (
    EmailPreferencesResponse,
    EmailPreferencesUpdate,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UserProfileUpdate,
    UserResponse,
)

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/profile", response_model=UserResponse)
def update_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.username is not None:
        username = body.username.strip()
        if len(username) < 3 or len(username) > 30:
            raise HTTPException(status_code=422, detail="Username must be between 3 and 30 characters.")
        if not _USERNAME_RE.match(username):
            raise HTTPException(status_code=422, detail="Username can only contain letters, numbers, underscores, and hyphens.")
        current_user.username = username
    if body.timezone is not None:
        current_user.timezone = body.timezone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/email-preferences", response_model=EmailPreferencesResponse)
def get_email_preferences(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/email-preferences", response_model=EmailPreferencesResponse)
def update_email_preferences(
    body: EmailPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.email_notifications_enabled is not None:
        current_user.email_notifications_enabled = body.email_notifications_enabled
    if body.calendar_email_reminders_enabled is not None:
        current_user.calendar_email_reminders_enabled = body.calendar_email_reminders_enabled
    if body.favorite_driver_email_alerts_enabled is not None:
        current_user.favorite_driver_email_alerts_enabled = body.favorite_driver_email_alerts_enabled

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/notification-preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/notification-preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    body: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.favorite_driver_notifications_enabled is not None:
        current_user.favorite_driver_notifications_enabled = body.favorite_driver_notifications_enabled
    if body.favorite_driver_email_alerts_enabled is not None:
        current_user.favorite_driver_email_alerts_enabled = body.favorite_driver_email_alerts_enabled

    db.commit()
    db.refresh(current_user)
    return current_user
