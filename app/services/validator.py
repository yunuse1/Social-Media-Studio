from typing import Any, Dict

CONSTRAINT_PROFILES: Dict[str, Dict[str, Any]] = {
    "x": {"max_length": 280, "max_hashtags": 3, "allowed_tones": {"casual", "professional", "neutral"}, "name": "X"},
    "linkedin": {"max_length": 3000, "max_hashtags": 10, "allowed_tones": {"professional", "neutral"}, "name": "LinkedIn"},
    "telegram": {"max_length": 4096, "max_hashtags": 15, "allowed_tones": {"casual", "professional", "neutral"}, "name": "Telegram"},
}


class ValidationError(Exception):
    pass


def validate_variant_constraints(platform: str, content: str, tone: str | None = None) -> bool:
    platform_key = platform.lower()
    if platform_key not in CONSTRAINT_PROFILES:
        raise ValidationError(f"platform not supported: {platform}")

    profile = CONSTRAINT_PROFILES[platform_key]
    if len(content) > profile["max_length"]:
        raise ValidationError(f"character limit exceeded ({platform}): {len(content)} > {profile['max_length']}")

    hashtag_count = content.count("#")
    if hashtag_count > profile["max_hashtags"]:
        raise ValidationError(f"hashtag limit exceeded ({platform}): {hashtag_count} > {profile['max_hashtags']}")

    if tone is not None and tone.lower() not in profile["allowed_tones"]:
        raise ValidationError(f"tone '{tone}' is not allowed for {platform}")

    return True
