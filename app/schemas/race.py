from pydantic import BaseModel


class RaceSchema(BaseModel):
    id: int
    season: int
    round: int
    name: str
    circuit_name: str | None
    country: str | None
    start_date: str | None
