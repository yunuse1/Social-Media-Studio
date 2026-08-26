import pytest

from app.services.validator import ValidationError, validate_variant_constraints


def test_variant_within_constraints_is_allowed():
    assert validate_variant_constraints("x", "hello world #ai", "casual") is True


def test_variant_over_max_length_is_blocked():
    with pytest.raises(ValidationError):
        validate_variant_constraints("x", "a" * 281)


def test_variant_with_too_many_hashtags_is_blocked():
    with pytest.raises(ValidationError):
        validate_variant_constraints("x", "#one #two #three #four")


def test_variant_tone_must_match_platform_constraint():
    with pytest.raises(ValidationError):
        validate_variant_constraints("linkedin", "hello", "casual")
