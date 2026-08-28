import json
import os
from typing import Dict, List

from pydantic import BaseModel, Field

from app.services.validator import ValidationError, validate_variant_constraints


class AIVariant(BaseModel):
    platform: str
    tone: str
    content: str
    hashtags: List[str] = Field(default_factory=list)


class AIVariantResponse(BaseModel):
    variants: List[AIVariant]


class AIUsage(BaseModel):
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AIGenerationResult(BaseModel):
    variants: List[AIVariant]
    usage: AIUsage


PLATFORMS = ("x", "linkedin", "telegram")

# Prices are configurable because model pricing can change. Defaults match the
# current low-cost GPT-5.6 Luna pricing used by this project.
INPUT_COST_PER_MILLION = float(os.getenv("OPENAI_INPUT_COST_PER_MILLION", "0.20"))
OUTPUT_COST_PER_MILLION = float(os.getenv("OPENAI_OUTPUT_COST_PER_MILLION", "1.20"))


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": list(PLATFORMS)},
                        "tone": {"type": "string", "enum": ["casual", "professional", "neutral"]},
                        "content": {"type": "string"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["platform", "tone", "content", "hashtags"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["variants"],
        "additionalProperties": False,
    }


def generate_ai_variants(title: str, content: str) -> AIGenerationResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    client = OpenAI(api_key=api_key)

    prompt = f"""Create exactly one social-media variant for each platform: x, linkedin, telegram.

Source title:
{title}

Source content:
{content}

Rules:
- Preserve facts from the source. Do not invent claims, statistics, links, or product details.
- Adapt the writing style to each platform.
- x: concise and engaging, casual or neutral tone.
- linkedin: professional and useful, professional or neutral tone.
- telegram: readable and conversational, casual, professional, or neutral tone.
- Put hashtags in the hashtags array and also include them naturally in content.
- Respect these hard limits: x <= 280 chars and <= 3 hashtags; linkedin <= 3000 chars and <= 10 hashtags; telegram <= 4096 chars and <= 15 hashtags.
"""

    response = client.responses.create(
        model=model,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "social_media_variants",
                "strict": True,
                "schema": _schema(),
            }
        },
    )

    parsed = AIVariantResponse.model_validate(json.loads(response.output_text))
    by_platform = {item.platform: item for item in parsed.variants}
    if set(by_platform) != set(PLATFORMS):
        raise ValidationError("LLM must return exactly one variant for each supported platform")

    for variant in parsed.variants:
        validate_variant_constraints(variant.platform, variant.content, variant.tone)

    usage = response.usage
    input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
    output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
    estimated_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_MILLION + (output_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION

    return AIGenerationResult(
        variants=parsed.variants,
        usage=AIUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(estimated_cost, 8),
        ),
    )
