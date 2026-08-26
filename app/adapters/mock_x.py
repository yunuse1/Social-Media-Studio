import uuid
from app.adapters.base import SocialPublisher, PublishResult

class MockXPublisher(SocialPublisher):
    async def publish(self, content: str, idempotency_key: str) -> PublishResult:
        mock_tweet_id = f"mock_x_{uuid.uuid4().hex[:8]}"
        return PublishResult(
            success=True,
            platform="x",
            post_id=mock_tweet_id,
            url=f"https://x.com/mock_user/status/{mock_tweet_id}",
            message=f"[MOCK X] Published (length: {len(content)})."
        )