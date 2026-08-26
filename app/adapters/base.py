from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional

class PublishResult(BaseModel):
    success: bool
    platform: str
    post_id: str
    url: Optional[str] = None
    message: Optional[str] = None

class SocialPublisher(ABC):
    @abstractmethod
    async def publish(self, content: str, idempotency_key: str) -> PublishResult:
        pass