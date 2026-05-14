from datetime import datetime

from pydantic import BaseModel


class FavoriteTeamInfo(BaseModel):
    id: int
    name: str
    constructor_name: str
    base: str | None

    model_config = {"from_attributes": True}


class FavoriteDriverInfo(BaseModel):
    id: int
    code: str
    full_name: str
    nationality: str | None
    driver_number: int | None
    team: FavoriteTeamInfo | None

    model_config = {"from_attributes": True}


class FavoriteDriverResponse(BaseModel):
    id: int
    user_id: int
    driver_id: int
    created_at: datetime
    driver: FavoriteDriverInfo

    model_config = {"from_attributes": True}


class FavoriteTeamResponse(BaseModel):
    id: int
    user_id: int
    team_id: int
    created_at: datetime
    team: FavoriteTeamInfo

    model_config = {"from_attributes": True}
