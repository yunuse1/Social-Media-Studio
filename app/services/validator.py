from typing import Dict, Any

CONSTRAINT_PROFILES: Dict[str, Dict[str, Any]] = {
    "x": {
        "max_length": 280,
        "max_hashtags": 3,
        "name": "X (Twitter) Profile"
    },
    "linkedin": {
        "max_length": 3000,
        "max_hashtags": 10,
        "name": "LinkedIn Profile"
    },
    "telegram": {
        "max_length": 4096,
        "max_hashtags": 15,
        "name": "Telegram Profile"
    }
}

class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

def validate_variant_constraints(platform: str, content: str) -> bool:
    platform_key = platform.lower()
    if platform_key not in CONSTRAINT_PROFILES:
        raise ValidationError(f"platform not supported {platform}")
    
    profile = CONSTRAINT_PROFILES[platform_key]
    
    if len(content) > profile["max_length"]:
        raise ValidationError(
            f"character limit exceeded ({platform}): {len(content)} > {profile['max_length']}"
        )
    
    hashtag_count = content.count("#")
    if hashtag_count > profile["max_hashtags"]:
        raise ValidationError(
            f"hashtag limit exceeded ({platform}): {hashtag_count} > {profile['max_hashtags']}"
        )
    
    return True