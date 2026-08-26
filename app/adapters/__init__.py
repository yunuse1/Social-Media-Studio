from app.adapters.base import SocialPublisher
from app.adapters.telegram import TelegramPublisher
from app.adapters.mock_x import MockXPublisher
from app.adapters.mock_linkedin import MockLinkedInPublisher

def get_publisher(platform: str) -> SocialPublisher:
    platform_key = platform.lower()
    if platform_key == "telegram":
        return TelegramPublisher()
    elif platform_key == "x" or platform_key == "mock_x":
        return MockXPublisher()
    elif platform_key == "linkedin" or platform_key == "mock_linkedin":
        return MockLinkedInPublisher()
    else:
        raise ValueError(f"unsupported platform adapter: {platform}")