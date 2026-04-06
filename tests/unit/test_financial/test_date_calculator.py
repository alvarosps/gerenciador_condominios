"""Tests for DateCalculatorService — date calculations, edge cases, formatting."""

from datetime import date

import pytest
from freezegun import freeze_time

from core.services.date_calculator import DateCalculatorService


@pytest.mark.unit
class TestCalculateNextMonthDate:
    def test_normal_date(self) -> None:
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 15))
        assert result == date(2025, 2, 15)

    def test_end_of_january_goes_to_feb_28(self) -> None:
        result = DateCalculatorService.calculate_next_month_date(date(2025, 1, 31))
        assert result == date(2025, 2, 28)  # Non-leap year

    def test_end_of_january_leap_year_goes_to_feb_29(self) -> None:
        result = DateCalculatorService.calculate_next_month_date(date(2024, 1, 31))
        assert result == date(2024, 2, 29)  # 2024 is a leap year

    def test_december_to_january_next_year(self) -> None:
        result = DateCalculatorService.calculate_next_month_date(date(2025, 12, 15))
        assert result == date(2026, 1, 15)

    def test_end_of_march_to_april(self) -> None:
        result = DateCalculatorService.calculate_next_month_date(date(2025, 3, 31))
        assert result == date(2025, 4, 30)


@pytest.mark.unit
class TestCalculateFinalDate:
    def test_normal_12_month_lease(self) -> None:
        result = DateCalculatorService.calculate_final_date(date(2025, 1, 15), 12)
        assert result == date(2026, 1, 15)

    def test_feb29_12_months_goes_to_march1(self) -> None:
        # Start on Feb 29 (leap year 2024), 12 months = Feb 28 2025 (non-leap) → March 1
        result = DateCalculatorService.calculate_final_date(date(2024, 2, 29), 12)
        assert result == date(2025, 3, 1)

    def test_feb29_24_months_stays_feb28(self) -> None:
        # Start on Feb 29, 24 months = Feb 28, 2026 (also non-leap) → stays Feb 28
        # Because: starts at Feb 29, ends at Feb 28 of non-leap year → March 1
        # Actually 24 months from 2024-02-29 is 2026-02-28 (non-leap) → March 1
        result = DateCalculatorService.calculate_final_date(date(2024, 2, 29), 24)
        assert result == date(2026, 3, 1)

    def test_feb29_48_months_to_next_leap_stays_feb29(self) -> None:
        # 2024-02-29 + 48 months = 2028-02-29 (leap year) — stays as Feb 29
        result = DateCalculatorService.calculate_final_date(date(2024, 2, 29), 48)
        assert result == date(2028, 2, 29)

    def test_normal_start_date_not_affected_by_edge_case(self) -> None:
        result = DateCalculatorService.calculate_final_date(date(2025, 3, 15), 12)
        assert result == date(2026, 3, 15)


@pytest.mark.unit
class TestCalculateLeaseDates:
    def test_returns_all_keys(self) -> None:
        result = DateCalculatorService.calculate_lease_dates(date(2025, 1, 15), 12)
        assert "start_date" in result
        assert "next_month_date" in result
        assert "final_date" in result
        assert "validity_months" in result

    def test_values_are_correct(self) -> None:
        result = DateCalculatorService.calculate_lease_dates(date(2025, 1, 15), 12)
        assert result["start_date"] == date(2025, 1, 15)
        assert result["next_month_date"] == date(2025, 2, 15)
        assert result["final_date"] == date(2026, 1, 15)
        assert result["validity_months"] == 12


@pytest.mark.unit
class TestIsRentDue:
    def test_rent_is_due_when_current_day_equals_due_day(self) -> None:
        assert DateCalculatorService.is_rent_due(10, date(2025, 1, 10)) is True

    def test_rent_is_due_when_current_day_after_due_day(self) -> None:
        assert DateCalculatorService.is_rent_due(10, date(2025, 1, 15)) is True

    def test_rent_not_due_when_current_day_before_due_day(self) -> None:
        assert DateCalculatorService.is_rent_due(20, date(2025, 1, 15)) is False

    @freeze_time("2025-01-15")
    def test_uses_today_when_no_date_provided(self) -> None:
        assert DateCalculatorService.is_rent_due(10) is True
        assert DateCalculatorService.is_rent_due(20) is False


@pytest.mark.unit
class TestDaysUntilDue:
    def test_days_until_due_when_before_due_day(self) -> None:
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 5))
        assert result == 5

    def test_zero_when_already_due(self) -> None:
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 10))
        assert result == 0

    def test_zero_when_past_due(self) -> None:
        result = DateCalculatorService.days_until_due(10, date(2025, 1, 15))
        assert result == 0

    @freeze_time("2025-01-05")
    def test_uses_today_when_no_date_provided(self) -> None:
        assert DateCalculatorService.days_until_due(10) == 5


@pytest.mark.unit
class TestFormatDateBrazilian:
    def test_format_basic_date(self) -> None:
        result = DateCalculatorService.format_date_brazilian(date(2025, 1, 15))
        assert result == "15/01/2025"

    def test_format_single_digit_day_month(self) -> None:
        result = DateCalculatorService.format_date_brazilian(date(2025, 3, 5))
        assert result == "05/03/2025"


@pytest.mark.unit
class TestFormatLeaseDatesForContract:
    def test_returns_formatted_strings(self) -> None:
        result = DateCalculatorService.format_lease_dates_for_contract(date(2025, 1, 15), 12)
        assert result["start_date_formatted"] == "15/01/2025"
        assert result["next_month_date_formatted"] == "15/02/2025"
        assert result["final_date_formatted"] == "15/01/2026"

    def test_all_keys_present(self) -> None:
        result = DateCalculatorService.format_lease_dates_for_contract(date(2025, 6, 1), 6)
        assert "start_date_formatted" in result
        assert "next_month_date_formatted" in result
        assert "final_date_formatted" in result
