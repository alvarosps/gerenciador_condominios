"""
Unit tests for DateCalculatorService.

Tests all date calculation business logic in isolation, including leap year edge cases.
"""
import pytest
from datetime import date

from core.services.date_calculator import DateCalculatorService


class TestCalculateNextMonthDate:
    """Test next month date calculations."""

    def test_next_month_regular_date(self):
        """Test next month calculation for regular date."""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 15))
        assert result == date(2025, 2, 15)

    def test_next_month_month_end_non_leap(self):
        """Test next month calculation for month-end date (non-leap year)."""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 31))
        assert result == date(2025, 2, 28)  # No Feb 31, non-leap year

    def test_next_month_month_end_leap_year(self):
        """Test next month calculation for month-end date (leap year)."""
        result = DateCalculatorService.calculate_next_month_date(date(2024, 1, 31))
        assert result == date(2024, 2, 29)  # Leap year

    def test_next_month_from_february_non_leap(self):
        """Test next month from February in non-leap year."""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 2, 28))
        assert result == date(2025, 3, 28)

    def test_next_month_from_february_leap(self):
        """Test next month from February 29 in leap year."""
        result = DateCalculatorService.calculate_next_month_date(date(2024, 2, 29))
        assert result == date(2024, 3, 29)

    def test_next_month_december_to_january(self):
        """Test next month calculation across year boundary."""
        result = DateCalculatorService.calculate_next_month_date(date(2024, 12, 15))
        assert result == date(2025, 1, 15)

    def test_next_month_30_day_month(self):
        """Test next month from 30-day month to 31-day month."""
        result = DateCalculatorService.calculate_next_month_date(date(2025, 4, 30))
        assert result == date(2025, 5, 30)


class TestCalculateFinalDate:
    """Test final date calculations."""

    def test_final_date_regular_case(self):
        """Test final date calculation for regular case."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 12
        )
        assert result == date(2026, 1, 15)

    def test_final_date_6_months(self):
        """Test final date calculation for 6 months."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 6
        )
        assert result == date(2025, 7, 15)

    def test_final_date_24_months(self):
        """Test final date calculation for 24 months."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 24
        )
        assert result == date(2027, 1, 15)

    def test_final_date_leap_year_edge_case(self):
        """Test final date calculation for Feb 29 -> Feb 28 -> March 1 edge case."""
        # Start on Feb 29, 2024 (leap year)
        # 12 months later would be Feb 29, 2025, but 2025 is not a leap year
        # So it becomes Feb 28, 2025, and we adjust to March 1, 2025
        result = DateCalculatorService.calculate_final_date(
            date(2024, 2, 29), 12
        )
        assert result == date(2025, 3, 1)

    def test_final_date_leap_year_to_leap_year(self):
        """Test final date from leap year to leap year."""
        # Feb 29, 2024 + 48 months = Feb 29, 2028 (both leap years)
        result = DateCalculatorService.calculate_final_date(
            date(2024, 2, 29), 48
        )
        assert result == date(2028, 2, 29)

    def test_final_date_leap_year_24_months(self):
        """Test final date for 24 months from leap year."""
        # Feb 29, 2024 + 24 months = Feb 29, 2026
        # But 2026 is not leap year, so -> Feb 28, 2026 -> March 1, 2026
        result = DateCalculatorService.calculate_final_date(
            date(2024, 2, 29), 24
        )
        assert result == date(2026, 3, 1)

    def test_final_date_month_end_to_month_end(self):
        """Test final date from month end to month end."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 31), 12
        )
        assert result == date(2026, 1, 31)

    def test_final_date_short_lease(self):
        """Test final date for short lease (1 month)."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 1
        )
        assert result == date(2025, 2, 15)

    def test_final_date_long_lease(self):
        """Test final date for long lease (36 months)."""
        result = DateCalculatorService.calculate_final_date(
            date(2025, 1, 15), 36
        )
        assert result == date(2028, 1, 15)


class TestCalculateLeaseDates:
    """Test comprehensive lease date calculations."""

    def test_lease_dates_standard(self):
        """Test complete lease dates calculation."""
        result = DateCalculatorService.calculate_lease_dates(
            date(2025, 1, 15), 12
        )

        assert result['start_date'] == date(2025, 1, 15)
        assert result['next_month_date'] == date(2025, 2, 15)
        assert result['final_date'] == date(2026, 1, 15)
        assert result['validity_months'] == 12

    def test_lease_dates_leap_year_edge_case(self):
        """Test lease dates with leap year edge case."""
        result = DateCalculatorService.calculate_lease_dates(
            date(2024, 2, 29), 12
        )

        assert result['start_date'] == date(2024, 2, 29)
        assert result['next_month_date'] == date(2024, 3, 29)
        assert result['final_date'] == date(2025, 3, 1)  # Adjusted edge case
        assert result['validity_months'] == 12

    def test_lease_dates_short_lease(self):
        """Test lease dates for short lease."""
        result = DateCalculatorService.calculate_lease_dates(
            date(2025, 6, 1), 6
        )

        assert result['start_date'] == date(2025, 6, 1)
        assert result['next_month_date'] == date(2025, 7, 1)
        assert result['final_date'] == date(2025, 12, 1)
        assert result['validity_months'] == 6


class TestIsRentDue:
    """Test rent due checking."""

    def test_rent_due_before_due_date(self):
        """Test rent not due before due date."""
        result = DateCalculatorService.is_rent_due(15, date(2025, 1, 10))
        assert result is False

    def test_rent_due_on_due_date(self):
        """Test rent due on exactly the due date."""
        result = DateCalculatorService.is_rent_due(15, date(2025, 1, 15))
        assert result is True

    def test_rent_due_after_due_date(self):
        """Test rent due after due date."""
        result = DateCalculatorService.is_rent_due(15, date(2025, 1, 20))
        assert result is True

    def test_rent_due_first_of_month(self):
        """Test rent due on first of month."""
        result = DateCalculatorService.is_rent_due(1, date(2025, 1, 1))
        assert result is True

        result = DateCalculatorService.is_rent_due(1, date(2025, 1, 15))
        assert result is True

    def test_rent_due_end_of_month(self):
        """Test rent due at end of month."""
        result = DateCalculatorService.is_rent_due(30, date(2025, 1, 31))
        assert result is True

        result = DateCalculatorService.is_rent_due(30, date(2025, 1, 29))
        assert result is False


class TestDaysUntilDue:
    """Test days until due calculations."""

    def test_days_until_due_before_due_date(self):
        """Test days until due before due date."""
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 5))
        assert result == 5

    def test_days_until_due_on_due_date(self):
        """Test days until due on due date."""
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 10))
        assert result == 0

    def test_days_until_due_after_due_date(self):
        """Test days until due after due date."""
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 15))
        assert result == 0  # Already past due

    def test_days_until_due_one_day_before(self):
        """Test days until due one day before."""
        result = DateCalculatorService.days_until_due(15, date(2025, 1, 14))
        assert result == 1

    def test_days_until_due_beginning_of_month(self):
        """Test days until due at beginning of month."""
        result = DateCalculatorService.days_until_due(25, date(2025, 1, 1))
        assert result == 24


class TestFormatDateBrazilian:
    """Test Brazilian date formatting."""

    def test_format_date_brazilian_regular(self):
        """Test formatting regular date."""
        result = DateCalculatorService.format_date_brazilian(date(2025, 1, 15))
        assert result == "15/01/2025"

    def test_format_date_brazilian_single_digit_day(self):
        """Test formatting date with single digit day."""
        result = DateCalculatorService.format_date_brazilian(date(2025, 1, 5))
        assert result == "05/01/2025"

    def test_format_date_brazilian_single_digit_month(self):
        """Test formatting date with single digit month."""
        result = DateCalculatorService.format_date_brazilian(date(2025, 3, 15))
        assert result == "15/03/2025"

    def test_format_date_brazilian_december(self):
        """Test formatting December date."""
        result = DateCalculatorService.format_date_brazilian(date(2025, 12, 31))
        assert result == "31/12/2025"


class TestFormatLeaseDatesForContract:
    """Test lease date formatting for contract."""

    def test_format_lease_dates_for_contract_standard(self):
        """Test formatting all lease dates for contract."""
        result = DateCalculatorService.format_lease_dates_for_contract(
            date(2025, 1, 15), 12
        )

        assert result['start_date_formatted'] == "15/01/2025"
        assert result['next_month_date_formatted'] == "15/02/2025"
        assert result['final_date_formatted'] == "15/01/2026"

    def test_format_lease_dates_for_contract_leap_year(self):
        """Test formatting lease dates with leap year edge case."""
        result = DateCalculatorService.format_lease_dates_for_contract(
            date(2024, 2, 29), 12
        )

        assert result['start_date_formatted'] == "29/02/2024"
        assert result['next_month_date_formatted'] == "29/03/2024"
        assert result['final_date_formatted'] == "01/03/2025"  # Adjusted edge case

    def test_format_lease_dates_for_contract_short_lease(self):
        """Test formatting dates for short lease."""
        result = DateCalculatorService.format_lease_dates_for_contract(
            date(2025, 6, 1), 6
        )

        assert result['start_date_formatted'] == "01/06/2025"
        assert result['next_month_date_formatted'] == "01/07/2025"
        assert result['final_date_formatted'] == "01/12/2025"


class TestDateCalculatorServiceIntegration:
    """Integration tests combining multiple date calculations."""

    def test_complete_lease_scenario(self):
        """Test a complete lease scenario with all date operations."""
        start_date = date(2025, 1, 15)
        validity_months = 12

        # Get all lease dates
        lease_dates = DateCalculatorService.calculate_lease_dates(start_date, validity_months)

        assert lease_dates['start_date'] == date(2025, 1, 15)
        assert lease_dates['next_month_date'] == date(2025, 2, 15)
        assert lease_dates['final_date'] == date(2026, 1, 15)

        # Format for contract
        formatted = DateCalculatorService.format_lease_dates_for_contract(start_date, validity_months)

        assert formatted['start_date_formatted'] == "15/01/2025"
        assert formatted['next_month_date_formatted'] == "15/02/2025"
        assert formatted['final_date_formatted'] == "15/01/2026"

        # Check rent due status on various dates
        assert DateCalculatorService.is_rent_due(10, date(2025, 1, 5)) is False
        assert DateCalculatorService.is_rent_due(10, date(2025, 1, 10)) is True
        assert DateCalculatorService.is_rent_due(10, date(2025, 1, 15)) is True

    def test_edge_case_comprehensive_leap_year(self):
        """Test comprehensive leap year edge case scenario."""
        start_date = date(2024, 2, 29)  # Leap year
        validity_months = 12

        # Calculate dates
        lease_dates = DateCalculatorService.calculate_lease_dates(start_date, validity_months)

        # Verify edge case handling: Feb 29 -> Feb 28 -> March 1
        assert lease_dates['start_date'] == date(2024, 2, 29)
        assert lease_dates['next_month_date'] == date(2024, 3, 29)
        assert lease_dates['final_date'] == date(2025, 3, 1)  # Not Feb 28!

        # Verify formatting works correctly
        formatted = DateCalculatorService.format_lease_dates_for_contract(start_date, validity_months)
        assert formatted['final_date_formatted'] == "01/03/2025"

    def test_edge_case_multiple_validity_periods(self):
        """Test leap year edge case with different validity periods."""
        start_date = date(2024, 2, 29)

        # 12 months: Feb 29, 2024 -> March 1, 2025
        result_12 = DateCalculatorService.calculate_final_date(start_date, 12)
        assert result_12 == date(2025, 3, 1)

        # 24 months: Feb 29, 2024 -> March 1, 2026
        result_24 = DateCalculatorService.calculate_final_date(start_date, 24)
        assert result_24 == date(2026, 3, 1)

        # 48 months: Feb 29, 2024 -> Feb 29, 2028 (leap year)
        result_48 = DateCalculatorService.calculate_final_date(start_date, 48)
        assert result_48 == date(2028, 2, 29)
