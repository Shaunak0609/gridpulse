from pydantic import BaseModel


class StintResponse(BaseModel):
    id: int
    session_id: int
    driver_number: int
    stint_number: int | None

    # Tyre compound. Known values: SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    compound: str | None

    lap_start: int | None
    lap_end: int | None

    # Number of laps the tyre had already done before this stint. 0 = new tyre.
    tyre_age_at_start: int | None

    model_config = {"from_attributes": True}
