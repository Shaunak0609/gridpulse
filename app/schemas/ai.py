from datetime import datetime

from pydantic import BaseModel, Field


class AIRequestCreate(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    request_type: str = "general"


class AIResponse(BaseModel):
    id: int
    prompt: str
    response: str | None
    request_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIHistoryResponse(BaseModel):
    id: int
    prompt: str
    response: str | None
    request_type: str
    created_at: datetime
    model_name: str | None

    model_config = {"from_attributes": True}
