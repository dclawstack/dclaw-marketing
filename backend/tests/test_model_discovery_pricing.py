"""Unit tests for the OpenRouter pricing parser (S5 #365)."""

from app.services.model_discovery import _parse_pricing_from_openrouter


def test_free_suffix_marks_as_free():
    out = _parse_pricing_from_openrouter(
        {"pricing": {"prompt": "0.000003", "completion": "0.000015"}},
        "vendor/model:free",
    )
    assert out == {"is_free": True}


def test_all_zero_pricing_marks_as_free():
    out = _parse_pricing_from_openrouter(
        {"pricing": {"prompt": "0", "completion": "0", "request": "0"}},
        "vendor/model",
    )
    assert out == {"is_free": True}


def test_paid_rates_pass_through_with_currency():
    out = _parse_pricing_from_openrouter(
        {"pricing": {"prompt": "0.000003", "completion": "0.000015"}},
        "anthropic/claude-3-haiku",
    )
    assert out is not None
    assert out["currency"] == "USD"
    assert out["prompt"] == "0.000003"
    assert out["completion"] == "0.000015"


def test_missing_pricing_returns_none():
    assert _parse_pricing_from_openrouter({}, "vendor/model") is None
    assert _parse_pricing_from_openrouter({"pricing": None}, "vendor/model") is None
    assert _parse_pricing_from_openrouter({"pricing": "junk"}, "vendor/model") is None


def test_image_pricing_preserved():
    out = _parse_pricing_from_openrouter(
        {"pricing": {"prompt": "0.000003", "completion": "0.000015", "image": "0.0001"}},
        "vendor/multimodal",
    )
    assert out is not None
    assert out.get("image") == "0.0001"
