import json
import os
from typing import List

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


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost using prices configured for the selected Gemini model.

    Defaults are zero so the application never invents a provider price.
    Set GEMINI_INPUT_COST_PER_MILLION and GEMINI_OUTPUT_COST_PER_MILLION
    to the current prices for the selected model when cost tracking is desired.
    """
    input_price = float(os.getenv("GEMINI_INPUT_COST_PER_MILLION", "0"))
    output_price = float(os.getenv("GEMINI_OUTPUT_COST_PER_MILLION", "0"))
    return round(
        (input_tokens / 1_000_000) * input_price
        + (output_tokens / 1_000_000) * output_price,
        8,
    )


def generate_ai_variants(title: str, content: str) -> AIGenerationResult:
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    if not model:
        raise RuntimeError("GEMINI_MODEL is not configured")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
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
- telegram: readable and conversational.
- Put hashtags in the hashtags array and also include them in content.
- Hard limits: x <= 280 chars and <= 3 hashtags; linkedin <= 3000 chars and <= 10 hashtags; telegram <= 4096 chars and <= 15 hashtags.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_schema(),
        ),
    )

    parsed = AIVariantResponse.model_validate_json(response.text)
    by_platform = {item.platform: item for item in parsed.variants}
    if set(by_platform) != set(PLATFORMS) or len(parsed.variants) != len(PLATFORMS):
        raise ValidationError("LLM must return exactly one variant for each supported platform")

    for variant in parsed.variants:
        validate_variant_constraints(variant.platform, variant.content, variant.tone)

    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
    output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

    return AIGenerationResult(
        variants=parsed.variants,
        usage=AIUsage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(input_tokens, output_tokens),
        ),
    )
