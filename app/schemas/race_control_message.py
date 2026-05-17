from datetime import datetime

from pydantic import BaseModel


class RaceControlMessageResponse(BaseModel):
    id: int
    session_id: int
    date: datetime | None
    lap_number: int | None

    # Broad category. Known values: SafetyCar, Flag, Drs, CarEvent, Other
    category: str | None

    # Full text of the message, e.g. "SAFETY CAR DEPLOYED" or "DRS ENABLED".
    message: str

    # Flag status. Known values: GREEN, YELLOW, DOUBLE YELLOW, RED, SC, VSC, CHEQUERED
    flag: str | None

    # Whether the message targets the whole track, a specific driver, or a sector.
    scope: str | None

    # Sector number (1–3) when scope is "Sector". Null for track-wide messages.
    sector: int | None

    # Driver number when the message targets a specific driver (e.g. a penalty).
    driver_number: int | None

    model_config = {"from_attributes": True}
