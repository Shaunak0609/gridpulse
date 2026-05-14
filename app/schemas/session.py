from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    race_id: int
    session_type: str
    session_name: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    timezone: str | None = None


class SessionResponse(BaseModel):
    id: int
    race_id: int
    session_type: str
    session_name: str
    start_time: datetime | None
    end_time: datetime | None
    timezone: str | None

    model_config = {"from_attributes": True}
