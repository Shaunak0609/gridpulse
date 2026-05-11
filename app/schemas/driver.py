from pydantic import BaseModel


class DriverSchema(BaseModel):
    id: int
    code: str
    full_name: str
    nationality: str | None
    driver_number: int | None
    team: str | None
