import os

from sqlalchemy.orm import Session

from app.models.favorite_driver import FavoriteDriver
from app.models.notification import Notification
from app.models.standing import DriverStanding
from app.services.email_service import send_email

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Identifies standing-snapshot notifications so the dedup query can find them.
_NOTIFICATION_TYPE = "favorite_driver_standing"


def _build_email_body(user, driver, standing) -> str:
    username = user.username or user.email
    points = int(standing.points)
    return (
        f"Hi {username},\n\n"
        f"{driver.full_name} is currently P{standing.position} in the "
        f"{SEASON} driver standings with {points} points.\n\n"
        f"Head to GridPulse to see the full standings and upcoming race schedule.\n\n"
        f"— The GridPulse team\n\n"
        f"To stop receiving these emails, turn off favourite-driver email alerts "
        f"in your GridPulse settings."
    )


def generate_standing_notifications(db: Session) -> dict:
    """
    Create one in-app notification per user per favourited driver summarising
    the driver's current championship position, and optionally send an email.

    Rules applied in order for every (user, driver) pair:
      1. Skip if the user has turned off favourite-driver notifications.
      2. Skip if no standing row exists for this driver in the configured season.
      3. Skip if a notification of this type already exists for this (user, driver)
         pair — prevents duplicates when the function is called more than once.

    If a new notification is created, an email is also sent when the user has
    both email_notifications_enabled and favorite_driver_email_alerts_enabled set
    to true. The notification row is committed before the email attempt, so the
    in-app notification is always saved even if email delivery fails.

    Returns a summary dict with counts for every outcome.
    """
    favorites = db.query(FavoriteDriver).all()

    checked = len(favorites)
    created = 0
    skipped_preference = 0
    skipped_no_standing = 0
    skipped_duplicate = 0
    emails_sent = 0
    emails_failed = 0

    for fav in favorites:
        user = fav.user
        driver = fav.driver

        # Rule 1 — respect the user's in-app notification opt-out.
        if not user.favorite_driver_notifications_enabled:
            skipped_preference += 1
            continue

        # Rule 2 — only proceed if we have standing data for this driver.
        standing = (
            db.query(DriverStanding)
            .filter(
                DriverStanding.driver_id == driver.id,
                DriverStanding.season == SEASON,
            )
            .first()
        )

        if not standing:
            skipped_no_standing += 1
            continue

        # Rule 3 — one standing notification per (user, driver).
        already_notified = (
            db.query(Notification)
            .filter_by(
                user_id=user.id,
                type=_NOTIFICATION_TYPE,
                related_driver_id=driver.id,
            )
            .first()
            is not None
        )

        if already_notified:
            skipped_duplicate += 1
            continue

        # Build the shared message text used by both the notification and email.
        points = int(standing.points)
        message = (
            f"{driver.full_name} is currently P{standing.position} "
            f"in the {SEASON} driver standings with {points} points."
        )

        # Persist the in-app notification before attempting email so it is
        # always saved even if the email send fails.
        db.add(Notification(
            user_id=user.id,
            type=_NOTIFICATION_TYPE,
            title="Favourite driver update",
            message=message,
            related_driver_id=driver.id,
        ))
        db.commit()
        created += 1

        # Optional email — requires both the master switch and the driver-specific flag.
        if user.email_notifications_enabled and user.favorite_driver_email_alerts_enabled:
            try:
                send_email(
                    to=user.email,
                    subject=(
                        f"GridPulse: {driver.full_name} is P{standing.position} "
                        f"in the {SEASON} standings"
                    ),
                    body=_build_email_body(user, driver, standing),
                )
                emails_sent += 1
            except RuntimeError:
                emails_failed += 1

    return {
        "checked": checked,
        "created": created,
        "skipped_preference": skipped_preference,
        "skipped_no_standing": skipped_no_standing,
        "skipped_duplicate": skipped_duplicate,
        "emails_sent": emails_sent,
        "emails_failed": emails_failed,
    }
