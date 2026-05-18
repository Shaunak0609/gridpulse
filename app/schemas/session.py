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


class SessionDetailResponse(BaseModel):
    id: int
    race_id: int
    session_type: str
    session_name: str
    start_time: datetime | None
    end_time: datetime | None
    timezone: str | None
    circuit_short_name: str | None
    country_name: str | None
    openf1_session_key: int | None
    race_name: str | None = None

    model_config = {"from_attributes": True}
