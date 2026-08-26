from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime

class VariantStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"

class PostIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, description="title")
    content: str = Field(..., min_length=10, description="content")
    source_url: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    source_url: Optional[str] = None
    created_at: str

class VariantCreate(BaseModel):
    platform: str
    content: str

class VariantResponse(BaseModel):
    id: int
    post_id: int
    platform: str
    content: str
    status: VariantStatus
    created_at: str

class ScheduleRequest(BaseModel):
    variant_id: int
    scheduled_at: Optional[datetime] = None  
    idempotency_key: str = Field(..., min_length=4, description="idempotency_key")

class PublishHistoryResponse(BaseModel):
    id: int
    variant_id: int
    platform: str
    status: str
    idempotency_key: str
    live_post_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str