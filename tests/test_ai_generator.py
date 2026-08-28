import json

import pytest

from app.services.ai_generator import generate_ai_variants


class FakeUsage:
    prompt_token_count = 1000
    candidates_token_count = 500


class FakeResponse:
    text = json.dumps(
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
    usage_metadata = FakeUsage()


class FakeModels:
    def __init__(self):
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse()


class FakeClient:
    last_instance = None

    def __init__(self, **kwargs):
        self.models = FakeModels()
        self.api_key = kwargs.get("api_key")
        FakeClient.last_instance = self


def test_ai_generator_uses_gemini_and_structured_output(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("GEMINI_INPUT_COST_PER_MILLION", "1")
    monkeypatch.setenv("GEMINI_OUTPUT_COST_PER_MILLION", "2")
    monkeypatch.setattr("google.genai.Client", FakeClient)

    result = generate_ai_variants(
        "AI Backend", "A source article about reliable backend engineering."
    )

    assert {v.platform for v in result.variants} == {"x", "linkedin", "telegram"}
    assert result.usage.model == "test-model"
    assert result.usage.input_tokens == 1000
    assert result.usage.output_tokens == 500
    assert result.usage.estimated_cost_usd == 0.002

    request = FakeClient.last_instance.models.last_kwargs
    assert request["model"] == "test-model"
    assert request["config"].response_mime_type == "application/json"
    assert request["config"].response_schema["type"] == "object"


def test_ai_generator_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        generate_ai_variants("Title", "Content that is long enough.")


def test_ai_generator_requires_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_MODEL"):
        generate_ai_variants("Title", "Content that is long enough.")
