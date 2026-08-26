from app.services.validator import validate_variant


def test_variant_within_constraints_is_allowed():
    result = validate_variant("x", "hello world #ai", "short", "casual")
    assert result["allowed"] is True


def test_variant_over_max_length_is_blocked():
    result = validate_variant("x", "hello", "short", "casual")
    assert result["allowed"] is False


def test_variant_with_too_many_hashtags_is_blocked():
    result = validate_variant("x", "#one #two #three", "long", "casual")
    assert result["allowed"] is False


def test_variant_tone_must_match_platform_constraint():
    result = validate_variant("linkedin", "hello", "long", "casual")
    assert result["allowed"] is False
