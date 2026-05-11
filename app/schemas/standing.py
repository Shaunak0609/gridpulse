from pydantic import BaseModel


class DriverStandingSchema(BaseModel):
    position: int
    driver: str
    team: str
    points: float
    wins: int
    podiums: int
