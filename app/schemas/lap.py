from datetime import datetime

from pydantic import BaseModel


class LapResponse(BaseModel):
    id: int
    session_id: int
    driver_number: int
    lap_number: int

    # Total lap time in seconds. Null for incomplete laps (red flags, in-laps).
    lap_duration: float | None

    duration_sector_1: float | None
    duration_sector_2: float | None
    duration_sector_3: float | None

    # True when this lap immediately follows a pit stop.
    # Pit-out laps should be excluded from fastest-lap comparisons.
    is_pit_out_lap: bool

    date_start: datetime | None

    model_config = {"from_attributes": True}
