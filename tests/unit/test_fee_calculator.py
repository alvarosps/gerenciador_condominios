"""Unit tests for core/services/fee_calculator.py."""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings

from core.services.fee_calculator import FeeCalculatorService


@pytest.mark.unit
class TestCalculateDailyRate:
    def test_standard_value_divides_by_days_per_month(self):
        rate = FeeCalculatorService.calculate_daily_rate(Decimal("3000.00"))
        expected = Decimal("3000.00") / Decimal(str(settings.DAYS_PER_MONTH))
        assert rate == expected

    def test_known_value_1500(self):
        # 1500 / 30 = 50.00
        rate = FeeCalculatorService.calculate_daily_rate(Decimal("1500.00"))
        assert rate == Decimal("50.00")

    def test_zero_value_returns_zero(self):
        rate = FeeCalculatorService.calculate_daily_rate(Decimal(0))
        assert rate == Decimal(0)

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            FeeCalculatorService.calculate_daily_rate(Decimal(-100))


@pytest.mark.unit
class TestCalculateLateFee:
    def test_payment_is_late_returns_correct_keys(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2025, 1, 10),
            current_date=date(2025, 1, 15),
        )
        assert "is_late" in result
        assert "late_days" in result
        assert "late_fee" in result
        assert "message" in result

    def test_payment_is_late_when_current_date_after_due_date(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2025, 1, 10),
            current_date=date(2025, 1, 15),
        )
        assert result["is_late"] is True
        assert result["late_days"] == 5

    def test_late_fee_same_month(self):
        # daily_rate = 1500/30 = 50; late_days = 5; fee = quantize(50 * 5 * 0.05) = 12.50
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2025, 1, 10),
            current_date=date(2025, 1, 15),
        )
        daily_rate = Decimal("1500.00") / Decimal(str(settings.DAYS_PER_MONTH))
        expected_fee = (daily_rate * 5 * Decimal(str(settings.LATE_FEE_PERCENTAGE))).quantize(
            Decimal("0.01")
        )
        assert result["late_fee"] == expected_fee

    def test_late_fee_cross_month_overdue(self):
        # Regression: rent due Jan 25, still unpaid on Feb 10 → 16 days late, fee > 0.
        # The old implementation compared only current_date.day (10) > due_day (25) → R$0.
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2026, 1, 25),
            current_date=date(2026, 2, 10),
        )
        assert result["is_late"] is True
        assert result["late_days"] == 16
        assert result["late_fee"] > Decimal("0.00")

    def test_due_day_31_overdue_in_february(self):
        # Regression: due_day 31 clamped by the caller to Feb 28; current Mar 5 → 5 days late.
        # The old day-only comparison never marked due_day 31 as late in February.
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2026, 2, 28),
            current_date=date(2026, 3, 5),
        )
        assert result["is_late"] is True
        assert result["late_days"] == 5

    def test_payment_on_due_date_is_not_late(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2025, 1, 10),
            current_date=date(2025, 1, 10),
        )
        assert result["is_late"] is False
        assert result["late_days"] == 0
        assert result["late_fee"] == Decimal("0.00")

    def test_payment_before_due_date_is_not_late(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1500.00"),
            due_date=date(2025, 1, 15),
            current_date=date(2025, 1, 10),
        )
        assert result["is_late"] is False
        assert result["late_fee"] == Decimal("0.00")

    def test_late_fee_is_quantized_two_places(self):
        # 1234.56/30 * 3 * 0.05 = 6.1728 → quantized ROUND_HALF_UP to 6.17.
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("1234.56"),
            due_date=date(2026, 3, 10),
            current_date=date(2026, 3, 13),
        )
        late_fee = result["late_fee"]
        assert isinstance(late_fee, Decimal)
        assert -late_fee.as_tuple().exponent == 2
        assert late_fee == Decimal("6.17")

    def test_negative_rental_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            FeeCalculatorService.calculate_late_fee(
                rental_value=Decimal(-100),
                due_date=date(2025, 1, 10),
                current_date=date(2025, 1, 15),
            )

    def test_large_rental_value(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("999999.99"),
            due_date=date(2025, 1, 1),
            current_date=date(2025, 1, 31),
        )
        assert result["is_late"] is True
        assert isinstance(result["late_fee"], Decimal)
        assert result["late_fee"] > Decimal(0)
        assert -result["late_fee"].as_tuple().exponent == 2

    def test_one_day_late(self):
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal("3000.00"),
            due_date=date(2025, 1, 10),
            current_date=date(2025, 1, 11),
        )
        assert result["is_late"] is True
        assert result["late_days"] == 1
        assert result["late_fee"] > Decimal(0)


@pytest.mark.unit
class TestCalculateDueDateChangeFee:
    def test_new_day_later_in_same_month(self):
        # due_day 5 → 20, reference date March 2026
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1500.00"),
            current_due_day=5,
            new_due_day=20,
            reference_date=date(2026, 3, 1),
        )
        assert result["old_due_date"] == date(2026, 3, 5)
        assert result["new_due_date"] == date(2026, 3, 20)
        assert result["days_difference"] == 16  # inclusive: 5→20 = 15 days + 1
        assert "fee" in result
        assert "total_due" in result
        assert "daily_rate" in result

    def test_new_day_earlier_wraps_to_next_month(self):
        # due_day 22 → 5, reference March 2026 → new date = April 5
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1250.00"),
            current_due_day=22,
            new_due_day=5,
            reference_date=date(2026, 3, 1),
        )
        assert result["old_due_date"] == date(2026, 3, 22)
        assert result["new_due_date"] == date(2026, 4, 5)

    def test_total_due_equals_rental_plus_fee(self):
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1500.00"),
            current_due_day=10,
            new_due_day=25,
            reference_date=date(2026, 3, 1),
        )
        assert result["total_due"] == Decimal("1500.00") + result["fee"]

    def test_december_to_january_wraps_year(self):
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal("1000.00"),
            current_due_day=28,
            new_due_day=5,
            reference_date=date(2026, 12, 1),
        )
        assert result["old_due_date"] == date(2026, 12, 28)
        assert result["new_due_date"] == date(2027, 1, 5)


@pytest.mark.unit
class TestCalculateTagFee:
    def test_single_tenant_returns_single_fee(self):
        fee = FeeCalculatorService.calculate_tag_fee(1)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))

    def test_two_tenants_returns_multiple_fee(self):
        fee = FeeCalculatorService.calculate_tag_fee(2)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_MULTIPLE))

    def test_three_tenants_returns_multiple_fee(self):
        fee = FeeCalculatorService.calculate_tag_fee(3)
        assert fee == Decimal(str(settings.DEFAULT_TAG_FEE_MULTIPLE))

    def test_zero_tenants_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            FeeCalculatorService.calculate_tag_fee(0)

    def test_negative_tenants_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            FeeCalculatorService.calculate_tag_fee(-1)

    def test_single_fee_less_than_multiple_fee(self):
        single = FeeCalculatorService.calculate_tag_fee(1)
        multiple = FeeCalculatorService.calculate_tag_fee(2)
        assert single <= multiple


@pytest.mark.unit
class TestCalculateTotalValue:
    def test_sums_all_components(self):
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            tag_fee=Decimal("80.00"),
        )
        assert total == Decimal("1780.00")

    def test_zero_fees(self):
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("0.00"),
            tag_fee=Decimal("0.00"),
        )
        assert total == Decimal("1500.00")

    def test_all_zero(self):
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal(0),
            cleaning_fee=Decimal(0),
            tag_fee=Decimal(0),
        )
        assert total == Decimal(0)
