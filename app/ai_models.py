from pydantic import BaseModel, Field


class AIGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
