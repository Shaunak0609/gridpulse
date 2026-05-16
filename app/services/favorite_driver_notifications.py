import os

from sqlalchemy.orm import Session

from app.models.favorite_driver import FavoriteDriver
from app.models.notification import Notification
from app.models.standing import DriverStanding

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Identifies standing-snapshot notifications so the dedup query can find them.
_NOTIFICATION_TYPE = "favorite_driver_standing"


def generate_standing_notifications(db: Session) -> dict:
    """
    Create one in-app notification per user per favourited driver summarising
    the driver's current championship position.

    Rules applied in order for every (user, driver) pair:
      1. Skip if the user has turned off favourite-driver notifications.
      2. Skip if no standing row exists for this driver in the configured season.
      3. Skip if a notification of this type already exists for this (user, driver)
         pair — prevents duplicates when the function is called more than once.

    Returns a summary dict with counts for every outcome.
    """
    favorites = db.query(FavoriteDriver).all()

    checked = len(favorites)
    created = 0
    skipped_preference = 0
    skipped_no_standing = 0
    skipped_duplicate = 0

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

        # Format points as a whole number — F1 championship points are integers.
        points = int(standing.points)

        db.add(Notification(
            user_id=user.id,
            type=_NOTIFICATION_TYPE,
            title="Favourite driver update",
            message=(
                f"{driver.full_name} is currently P{standing.position} "
                f"in the {SEASON} driver standings with {points} points."
            ),
            related_driver_id=driver.id,
        ))
        created += 1

    if created:
        db.commit()

    return {
        "checked": checked,
        "created": created,
        "skipped_preference": skipped_preference,
        "skipped_no_standing": skipped_no_standing,
        "skipped_duplicate": skipped_duplicate,
    }
