import httpx
import os
from typing import Optional
from app.adapters.base import SocialPublisher, PublishResult

class TelegramPublisher(SocialPublisher):
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    async def publish(self, content: str, idempotency_key: str) -> PublishResult:
        if not self.bot_token or not self.chat_id:
            return PublishResult(
                success=False,
                platform="telegram",
                post_id="none",
                message="telegram token or chat_id is not configured."
            )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": content,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                message_id = str(data["result"]["message_id"])
                
                return PublishResult(
                    success=True,
                    platform="telegram",
                    post_id=message_id,
                    url=f"https://t.me/{self.chat_id}/{message_id}",
                    message="success"
                )
            except httpx.HTTPStatusError as e:
                return PublishResult(
                    success=False,
                    platform="telegram",
                    post_id="error",
                    message=f"Telegram api error: {e.response.text}"
                )
            except Exception as e:
                return PublishResult(
                    success=False,
                    platform="telegram",
                    post_id="error",
                    message=f"Telegram connection error: {str(e)}"
                )