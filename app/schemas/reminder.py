from datetime import datetime

from pydantic import BaseModel


class ReminderCreate(BaseModel):
    title: str
    reminder_time: datetime
    race_id: int | None = None


class ReminderResponse(BaseModel):
    id: int
    user_id: int
    race_id: int | None
    title: str
    reminder_time: datetime
    sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}
