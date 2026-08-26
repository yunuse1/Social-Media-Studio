import uuid
from app.adapters.base import SocialPublisher, PublishResult

class MockLinkedInPublisher(SocialPublisher):
    async def publish(self, content: str, idempotency_key: str) -> PublishResult:
        mock_urn = f"urn:li:share:mock_{uuid.uuid4().hex[:8]}"
        return PublishResult(
            success=True,
            platform="linkedin",
            post_id=mock_urn,
            url=f"https://linkedin.com/feed/update/{mock_urn}",
            message=f"[MOCK LinkedIn] Published (length: {len(content)})."
        )