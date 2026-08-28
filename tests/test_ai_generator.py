import json

import pytest

from app.services.ai_generator import generate_ai_variants


class FakeUsage:
    input_tokens = 1000
    output_tokens = 500


class FakeResponse:
    output_text = json.dumps(
        {
            "variants": [
                {
                    "platform": "x",
                    "tone": "neutral",
                    "content": "AI is changing backend engineering. #AI #Backend",
                    "hashtags": ["#AI", "#Backend"],
                },
                {
                    "platform": "linkedin",
                    "tone": "professional",
                    "content": "AI is changing how backend teams design and operate reliable systems. #AI #Backend",
                    "hashtags": ["#AI", "#Backend"],
                },
                {
                    "platform": "telegram",
                    "tone": "casual",
                    "content": "AI is changing backend engineering. Here is a quick overview. #AI",
                    "hashtags": ["#AI"],
                },
            ]
        }
    )
    usage = FakeUsage()


class FakeResponses:
    def create(self, **kwargs):
        return FakeResponse()


class FakeClient:
    def __init__(self, **kwargs):
        self.responses = FakeResponses()


def test_ai_generator_uses_structured_output_and_validates(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("openai.OpenAI", FakeClient, raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    result = generate_ai_variants("AI Backend", "A source article about reliable backend engineering.")

    assert {v.platform for v in result.variants} == {"x", "linkedin", "telegram"}
    assert result.usage.model == "test-model"
    assert result.usage.input_tokens == 1000
    assert result.usage.output_tokens == 500
    assert result.usage.estimated_cost_usd > 0


def test_ai_generator_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        generate_ai_variants("Title", "Content that is long enough.")
