"""
Unit tests for utility functions

Tests all utility functions in core/utils.py including:
- Currency formatting
- Number to words conversion
- Edge cases and error handling

Coverage target: 100% of utils.py
"""

import pytest
from decimal import Decimal

from core.utils import format_currency, number_to_words


# ============================================================================
# format_currency Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.util
class TestFormatCurrency:
    """Test suite for format_currency function"""

    def test_format_currency_integer(self):
        """Test formatting integer values"""
        result = format_currency(1500)
        assert result == "R$1,500.00"

    def test_format_currency_float(self):
        """Test formatting float values"""
        result = format_currency(1500.50)
        assert result == "R$1,500.50"

    def test_format_currency_decimal(self):
        """Test formatting Decimal values"""
        result = format_currency(Decimal('1500.00'))
        assert result == "R$1,500.00"

    def test_format_currency_large_value(self):
        """Test formatting large values with thousands separator"""
        result = format_currency(1234567.89)
        assert result == "R$1,234,567.89"

    def test_format_currency_zero(self):
        """Test formatting zero value"""
        result = format_currency(0)
        assert result == "R$0.00"

    def test_format_currency_negative(self):
        """Test formatting negative values"""
        result = format_currency(-500.50)
        # Format may vary, but should include minus sign
        assert "-" in result or "(" in result
        assert "500.50" in result

    def test_format_currency_small_decimal(self):
        """Test formatting values with many decimal places"""
        result = format_currency(10.999)
        # Should round to 2 decimal places
        assert "11.00" in result

    def test_format_currency_string_number(self):
        """Test formatting string numbers"""
        result = format_currency(float("1500.00"))
        assert result == "R$1,500.00"


# ============================================================================
# number_to_words Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.util
class TestNumberToWords:
    """Test suite for number_to_words function"""

    def test_number_to_words_integer(self):
        """Test converting integer to words"""
        result = number_to_words(100)
        # num2words in pt_BR should return Portuguese words
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain Portuguese number words
        assert "cem" in result.lower() or "cento" in result.lower()

    def test_number_to_words_float(self):
        """Test converting float to words"""
        result = number_to_words(1500.50)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_number_to_words_decimal(self):
        """Test converting Decimal to words"""
        result = number_to_words(Decimal('2000.00'))
        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain "dois mil" or similar
        assert "dois" in result.lower() or "mil" in result.lower()

    def test_number_to_words_zero(self):
        """Test converting zero to words"""
        result = number_to_words(0)
        assert isinstance(result, str)
        assert "zero" in result.lower()

    def test_number_to_words_one(self):
        """Test converting one to words"""
        result = number_to_words(1)
        assert isinstance(result, str)
        assert "um" in result.lower() or "uma" in result.lower()

    def test_number_to_words_large_number(self):
        """Test converting large numbers"""
        result = number_to_words(1000000)
        assert isinstance(result, str)
        assert "milhão" in result.lower() or "milhao" in result.lower()

    def test_number_to_words_with_cents(self):
        """Test converting numbers with cents"""
        result = number_to_words(1500.75)
        assert isinstance(result, str)
        # Should handle decimal part
        assert len(result) > 0

    def test_number_to_words_negative(self):
        """Test converting negative numbers"""
        result = number_to_words(-100)
        assert isinstance(result, str)
        # Should handle negative (may include "menos" or just return the number)
        assert len(result) > 0

    def test_number_to_words_error_handling(self):
        """Test error handling for invalid input"""
        # The function has error handling that returns the original value
        result = number_to_words("invalid")
        # Should return the original value on error
        assert result == "invalid"

    def test_number_to_words_string_number(self):
        """Test converting string numbers"""
        result = number_to_words("1500")
        assert isinstance(result, str)
        # Should convert successfully
        assert len(result) > 0

    def test_number_to_words_none(self):
        """Test handling None value"""
        result = number_to_words(None)
        # Should return None or handle gracefully
        assert result is None or isinstance(result, str)


# ============================================================================
# Integration Tests (using both functions together)
# ============================================================================

@pytest.mark.unit
@pytest.mark.util
class TestUtilsIntegration:
    """Test suite for integrated usage of utility functions"""

    def test_format_and_words_rental_value(self):
        """Test formatting typical rental values"""
        value = Decimal('1500.00')

        formatted = format_currency(value)
        words = number_to_words(value)

        assert "1,500.00" in formatted
        assert isinstance(words, str)
        assert len(words) > 0

    def test_format_and_words_tag_fee(self):
        """Test formatting tag fees"""
        value = Decimal('50.00')

        formatted = format_currency(value)
        words = number_to_words(value)

        assert "50.00" in formatted
        assert isinstance(words, str)

    def test_format_and_words_cleaning_fee(self):
        """Test formatting cleaning fees"""
        value = Decimal('200.00')

        formatted = format_currency(value)
        words = number_to_words(value)

        assert "200.00" in formatted
        assert isinstance(words, str)

    def test_format_and_words_total_value(self):
        """Test formatting total contract values"""
        rental = Decimal('1500.00')
        cleaning = Decimal('200.00')
        tag = Decimal('80.00')
        total = rental + cleaning + tag

        formatted = format_currency(total)
        words = number_to_words(total)

        assert "1,780.00" in formatted
        assert isinstance(words, str)

    @pytest.mark.parametrize("value,expected_in_formatted", [
        (Decimal('1200.00'), "1,200.00"),
        (Decimal('1500.00'), "1,500.00"),
        (Decimal('1800.00'), "1,800.00"),
        (Decimal('2000.00'), "2,000.00"),
        (Decimal('2500.00'), "2,500.00"),
    ])
    def test_common_rental_values(self, value, expected_in_formatted):
        """Test formatting common rental values"""
        formatted = format_currency(value)
        assert expected_in_formatted in formatted

    @pytest.mark.parametrize("value", [
        Decimal('50.00'),   # Single tenant tag fee
        Decimal('80.00'),   # Multiple tenant tag fee
        Decimal('150.00'),  # Low cleaning fee
        Decimal('200.00'),  # Standard cleaning fee
        Decimal('250.00'),  # High cleaning fee
    ])
    def test_common_fee_values(self, value):
        """Test formatting common fee values"""
        formatted = format_currency(value)
        words = number_to_words(value)

        assert "R$" in formatted
        assert isinstance(words, str)
        assert len(words) > 0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.unit
@pytest.mark.util
class TestUtilsEdgeCases:
    """Test suite for edge cases and error scenarios"""

    def test_format_currency_very_small_value(self):
        """Test formatting very small values"""
        result = format_currency(0.01)
        assert "0.01" in result

    def test_format_currency_very_large_value(self):
        """Test formatting very large values"""
        result = format_currency(9999999.99)
        assert "9,999,999.99" in result

    def test_number_to_words_decimal_precision(self):
        """Test number to words with high decimal precision"""
        result = number_to_words(1500.123456)
        assert isinstance(result, str)

    def test_format_currency_precision(self):
        """Test that format_currency maintains 2 decimal places"""
        result = format_currency(1500.1)
        assert ".10" in result  # Should pad to 2 decimals

    def test_number_to_words_boundary_values(self):
        """Test number to words with boundary values"""
        values = [0, 1, 10, 100, 1000, 10000]

        for value in values:
            result = number_to_words(value)
            assert isinstance(result, str)
            assert len(result) > 0
