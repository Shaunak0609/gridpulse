import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.favorite_driver import FavoriteDriver
from app.models.favorite_team import FavoriteTeam
from app.models.notification import Notification
from app.models.race import Race
from app.models.reminder import Reminder
from app.models.session import Session as RaceSession
from app.models.user import User
from app.schemas.dashboard import DashboardResponse

router = APIRouter(prefix="/me", tags=["dashboard"])

SEASON = int(os.getenv("F1_SEASON", "2026"))


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    favorite_drivers = (
        db.query(FavoriteDriver)
        .filter(FavoriteDriver.user_id == current_user.id)
        .order_by(FavoriteDriver.created_at)
        .all()
    )

    favorite_teams = (
        db.query(FavoriteTeam)
        .filter(FavoriteTeam.user_id == current_user.id)
        .order_by(FavoriteTeam.created_at)
        .all()
    )

    upcoming_sessions = (
        db.query(RaceSession)
        .join(Race)
        .filter(
            Race.season == SEASON,
            RaceSession.start_time != None,     # noqa: E711
            RaceSession.start_time >= now,
        )
        .order_by(RaceSession.start_time)
        .limit(5)
        .all()
    )

    upcoming_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == current_user.id,
            Reminder.reminder_time >= now,
        )
        .order_by(Reminder.reminder_time)
        .limit(5)
        .all()
    )

    recent_notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return DashboardResponse(
        user=current_user,
        favorite_drivers=favorite_drivers,
        favorite_teams=favorite_teams,
        upcoming_sessions=upcoming_sessions,
        upcoming_reminders=upcoming_reminders,
        recent_notifications=recent_notifications,
    )
