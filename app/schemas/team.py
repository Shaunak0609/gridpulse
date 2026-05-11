from pydantic import BaseModel


class TeamSchema(BaseModel):
    id: int
    name: str
    constructor_name: str
    base: str | None
