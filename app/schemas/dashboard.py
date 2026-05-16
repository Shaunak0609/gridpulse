from datetime import datetime

from pydantic import BaseModel

from app.schemas.favorite import FavoriteDriverResponse, FavoriteTeamResponse
from app.schemas.notification import NotificationResponse
from app.schemas.reminder import ReminderResponse
from app.schemas.session import SessionResponse


class DashboardUser(BaseModel):
    id: int
    email: str
    username: str | None

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    user: DashboardUser
    favorite_drivers: list[FavoriteDriverResponse]
    favorite_teams: list[FavoriteTeamResponse]
    upcoming_sessions: list[SessionResponse]
    upcoming_reminders: list[ReminderResponse]
    recent_notifications: list[NotificationResponse]
