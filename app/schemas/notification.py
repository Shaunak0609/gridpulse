from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str | None
    read: bool
    created_at: datetime
    related_race_id: int | None
    related_driver_id: int | None

    model_config = {"from_attributes": True}
