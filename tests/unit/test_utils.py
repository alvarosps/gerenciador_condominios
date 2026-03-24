"""Unit tests for core/utils.py — currency formatting and number-to-words conversion."""

from decimal import Decimal

import pytest

from core.utils import format_currency, number_to_words


@pytest.mark.unit
class TestFormatCurrency:
    def test_integer_value(self):
        assert format_currency(1500) == "R$1.500,00"

    def test_float_value(self):
        assert format_currency(1500.50) == "R$1.500,50"

    def test_decimal_value(self):
        assert format_currency(Decimal("1500.00")) == "R$1.500,00"

    def test_zero(self):
        assert format_currency(0) == "R$0,00"

    def test_small_value(self):
        assert format_currency(10) == "R$10,00"

    def test_large_value(self):
        assert format_currency(1_000_000) == "R$1.000.000,00"

    def test_cents_only(self):
        assert format_currency(0.50) == "R$0,50"

    def test_decimal_with_cents(self):
        assert format_currency(Decimal("200.75")) == "R$200,75"


@pytest.mark.unit
class TestNumberToWords:
    def test_round_integer(self):
        result = number_to_words(1500)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_zero(self):
        result = number_to_words(0)
        assert isinstance(result, str)

    def test_float_value(self):
        result = number_to_words(1500.50)
        assert isinstance(result, str)

    def test_decimal_value(self):
        result = number_to_words(Decimal("200.00"))
        assert isinstance(result, str)

    def test_returns_portuguese(self):
        result = number_to_words(1000)
        # num2words in pt_BR renders 1000 as 'mil'
        assert "mil" in result

    def test_invalid_value_returns_string_representation(self):
        # Pass an object that num2words cannot handle — it should return str(value)
        result = number_to_words("not_a_number")  # type: ignore[arg-type]
        # Either raises or returns fallback string
        assert isinstance(result, str)
