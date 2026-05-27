from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.favorite_driver import FavoriteDriver
from app.models.notification import Notification
from app.models.user import User
from app.schemas.alert import SessionAlertGenerationResult
from app.schemas.notification import NotificationGenerationSummary, NotificationResponse
from app.services.favorite_driver_alerts import generate_session_alerts
from app.services.favorite_driver_notifications import (
    generate_standing_notifications,
    generate_wins_notifications,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _get_owned_notification(
    notification_id: int,
    current_user: User,
    db: Session,
) -> Notification:
    """
    Fetch a notification by id and verify it belongs to current_user.
    Raises 404 if not found, 403 if it belongs to someone else.
    """
    notification = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with id {notification_id} not found.",
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this notification.",
        )

    return notification


@router.get("", response_model=list[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = _get_owned_notification(notification_id, current_user, db)
    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = _get_owned_notification(notification_id, current_user, db)
    db.delete(notification)
    db.commit()


@router.post(
    "/generate-favorite-driver-updates",
    response_model=NotificationGenerationSummary,
    summary="[Dev] Manually trigger favourite-driver notification generation",
    description=(
        "Development/manual endpoint. Runs the favourite-driver notification "
        "generators (standings snapshot and race wins) for all users and their "
        "favourited drivers. Duplicate notifications are skipped automatically. "
        "This is the same logic that runs automatically at the end of the F1 "
        "data sync script."
    ),
)
def generate_favorite_driver_updates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users_checked = db.query(FavoriteDriver.user_id).distinct().count()

    standing = generate_standing_notifications(db)
    wins = generate_wins_notifications(db)

    return NotificationGenerationSummary(
        users_checked=users_checked,
        favorite_drivers_checked=standing["checked"],
        notifications_created=standing["created"] + wins["created"],
        duplicates_skipped=standing["skipped_duplicate"] + wins["skipped_duplicate"],
    )


@router.post(
    "/generate-favorite-driver-alerts/{session_id}",
    response_model=SessionAlertGenerationResult,
    summary="[Dev] Generate favourite-driver alerts for a synced session",
    description=(
        "Development/manual endpoint. Detects favourite-driver events in a "
        "specific synced OpenF1 session — fastest stored lap, tyre strategy, "
        "race control mentions, and lap data notes — and creates in-app "
        "notifications for any user who has favourited a driver with data in "
        "that session. Duplicate alerts (same user, type, driver, and session) "
        "are skipped automatically, so calling this endpoint more than once is "
        "safe. Returns a per-alert-type breakdown of what was created and "
        "skipped. The session must have been synced via "
        "sync_openf1_session.py before alerts can be generated."
    ),
)
def generate_favorite_driver_alerts(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = generate_session_alerts(session_id, db)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )

    return SessionAlertGenerationResult.model_validate(result)
