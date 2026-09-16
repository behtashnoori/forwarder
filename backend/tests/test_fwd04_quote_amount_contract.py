import pytest

from backend.services.quote_service import QuoteValidationError, normalize_quote_payload


def test_quote_normalization_preserves_large_integral_string_without_float_rounding():
    assert normalize_quote_payload({"amount": "9007199254740993"})["amount"] == 9007199254740993


@pytest.mark.parametrize("amount", ["12.50", 12.5, True])
def test_quote_normalization_rejects_fractional_or_boolean_amounts(amount):
    with pytest.raises(QuoteValidationError):
        normalize_quote_payload({"amount": amount})
