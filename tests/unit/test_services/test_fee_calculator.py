"""
Unit tests for FeeCalculatorService.

Tests all fee calculation business logic in isolation from Django views.
"""
import pytest
from datetime import date
from decimal import Decimal

from core.services.fee_calculator import FeeCalculatorService


class TestCalculateDailyRate:
    """Test daily rate calculations."""

    def test_calculate_daily_rate_standard(self):
        """Test standard daily rate calculation."""
        rental_value = Decimal('1500.00')
        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)

        assert daily_rate == Decimal('50.00')  # 1500 / 30

    def test_calculate_daily_rate_higher_value(self):
        """Test daily rate for higher rental value."""
        rental_value = Decimal('6000.00')
        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)

        assert daily_rate == Decimal('100.00')  # 6000 / 30

    def test_calculate_daily_rate_with_cents(self):
        """Test daily rate calculation preserves decimal precision."""
        rental_value = Decimal('1550.00')
        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)

        # 1550 / 30 = 51.666... (check with reasonable precision)
        expected = Decimal('1550') / Decimal('30')
        assert daily_rate == expected


class TestCalculateLateFee:
    """Test late payment fee calculations."""

    def test_late_fee_not_late(self):
        """Test late fee when payment is not late."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=15,
            current_date=date(2025, 1, 10)
        )

        assert result['is_late'] is False
        assert result['late_days'] == 0
        assert result['late_fee'] == Decimal('0.00')
        assert 'não está atrasado' in result['message'].lower()

    def test_late_fee_on_due_day(self):
        """Test late fee on exactly the due day."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=15,
            current_date=date(2025, 1, 15)
        )

        assert result['is_late'] is False
        assert result['late_days'] == 0
        assert result['late_fee'] == Decimal('0.00')

    def test_late_fee_one_day_late(self):
        """Test late fee for 1 day late."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=10,
            current_date=date(2025, 1, 11)
        )

        # 1 day late
        # daily_rate = 1500 / 30 = 50.00
        # late_fee = 50.00 * 1 * 0.05 = 2.50
        assert result['is_late'] is True
        assert result['late_days'] == 1
        assert result['late_fee'] == Decimal('2.50')

    def test_late_fee_multiple_days(self):
        """Test late fee for multiple days late."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('1500.00'),
            due_day=5,
            current_date=date(2025, 1, 15)
        )

        # 10 days late
        # daily_rate = 1500 / 30 = 50.00
        # late_fee = 50.00 * 10 * 0.05 = 25.00
        assert result['is_late'] is True
        assert result['late_days'] == 10
        assert result['late_fee'] == Decimal('25.00')

    def test_late_fee_end_of_month(self):
        """Test late fee at end of month."""
        result = FeeCalculatorService.calculate_late_fee(
            rental_value=Decimal('6000.00'),
            due_day=1,
            current_date=date(2025, 1, 31)
        )

        # 30 days late
        # daily_rate = 6000 / 30 = 100.00
        # late_fee = 100.00 * 30 * 0.05 = 150.00
        assert result['is_late'] is True
        assert result['late_days'] == 30
        assert result['late_fee'] == Decimal('150.00')


class TestCalculateDueDateChangeFee:
    """Test due date change fee calculations."""

    def test_due_date_change_fee_forward(self):
        """Test fee for moving due date forward."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal('1500.00'),
            current_due_day=10,
            new_due_day=15
        )

        # 5 days difference
        # daily_rate = 1500 / 30 = 50.00
        # fee = 50.00 * 5 = 250.00
        assert result['days_difference'] == 5
        assert result['daily_rate'] == Decimal('50.00')
        assert result['fee'] == Decimal('250.00')

    def test_due_date_change_fee_backward(self):
        """Test fee for moving due date backward."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal('1500.00'),
            current_due_day=20,
            new_due_day=10
        )

        # 10 days difference (absolute value)
        # daily_rate = 1500 / 30 = 50.00
        # fee = 50.00 * 10 = 500.00
        assert result['days_difference'] == 10
        assert result['daily_rate'] == Decimal('50.00')
        assert result['fee'] == Decimal('500.00')

    def test_due_date_change_fee_no_change(self):
        """Test fee when due date doesn't change."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal('1500.00'),
            current_due_day=15,
            new_due_day=15
        )

        assert result['days_difference'] == 0
        assert result['fee'] == Decimal('0.00')

    def test_due_date_change_fee_large_difference(self):
        """Test fee for large due date change."""
        result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=Decimal('2000.00'),
            current_due_day=5,
            new_due_day=25
        )

        # 20 days difference
        # daily_rate = 2000 / 30 = 66.666...
        # fee = 66.666... * 20 = 1333.333...
        assert result['days_difference'] == 20
        assert result['fee'] == Decimal('1333.333333333333333333333333')


class TestCalculateTagFee:
    """Test tag fee calculations."""

    def test_tag_fee_single_tenant(self):
        """Test tag fee for single tenant."""
        fee = FeeCalculatorService.calculate_tag_fee(1)

        assert fee == Decimal('50.00')

    def test_tag_fee_two_tenants(self):
        """Test tag fee for two tenants."""
        fee = FeeCalculatorService.calculate_tag_fee(2)

        assert fee == Decimal('80.00')

    def test_tag_fee_three_tenants(self):
        """Test tag fee for three tenants."""
        fee = FeeCalculatorService.calculate_tag_fee(3)

        assert fee == Decimal('80.00')

    def test_tag_fee_many_tenants(self):
        """Test tag fee for many tenants (still uses multiple rate)."""
        fee = FeeCalculatorService.calculate_tag_fee(5)

        assert fee == Decimal('80.00')

    def test_tag_fee_invalid_zero_tenants(self):
        """Test tag fee raises error for zero tenants."""
        with pytest.raises(ValueError, match="at least 1"):
            FeeCalculatorService.calculate_tag_fee(0)

    def test_tag_fee_invalid_negative_tenants(self):
        """Test tag fee raises error for negative tenants."""
        with pytest.raises(ValueError, match="at least 1"):
            FeeCalculatorService.calculate_tag_fee(-1)


class TestCalculateTotalValue:
    """Test total value calculations."""

    def test_total_value_standard(self):
        """Test standard total value calculation."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal('1500.00'),
            cleaning_fee=Decimal('200.00'),
            tag_fee=Decimal('50.00')
        )

        assert total == Decimal('1750.00')

    def test_total_value_with_multiple_tenant_tag(self):
        """Test total value with multiple tenant tag fee."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal('1500.00'),
            cleaning_fee=Decimal('200.00'),
            tag_fee=Decimal('80.00')
        )

        assert total == Decimal('1780.00')

    def test_total_value_no_cleaning_fee(self):
        """Test total value with zero cleaning fee."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal('1500.00'),
            cleaning_fee=Decimal('0.00'),
            tag_fee=Decimal('50.00')
        )

        assert total == Decimal('1550.00')

    def test_total_value_high_values(self):
        """Test total value with higher amounts."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal('5000.00'),
            cleaning_fee=Decimal('500.00'),
            tag_fee=Decimal('80.00')
        )

        assert total == Decimal('5580.00')

    def test_total_value_decimal_precision(self):
        """Test total value maintains decimal precision."""
        total = FeeCalculatorService.calculate_total_value(
            rental_value=Decimal('1550.50'),
            cleaning_fee=Decimal('225.75'),
            tag_fee=Decimal('80.00')
        )

        assert total == Decimal('1856.25')


class TestFeeCalculatorServiceIntegration:
    """Integration tests combining multiple fee calculations."""

    def test_complete_lease_fee_scenario(self):
        """Test a complete lease scenario with all fees."""
        rental_value = Decimal('1500.00')
        num_tenants = 2

        # Calculate tag fee
        tag_fee = FeeCalculatorService.calculate_tag_fee(num_tenants)
        assert tag_fee == Decimal('80.00')

        # Calculate total initial payment
        total = FeeCalculatorService.calculate_total_value(
            rental_value=rental_value,
            cleaning_fee=Decimal('200.00'),
            tag_fee=tag_fee
        )
        assert total == Decimal('1780.00')

        # Calculate late fee (10 days late)
        late_result = FeeCalculatorService.calculate_late_fee(
            rental_value=rental_value,
            due_day=5,
            current_date=date(2025, 1, 15)
        )
        assert late_result['late_fee'] == Decimal('25.00')

        # Calculate due date change fee
        change_result = FeeCalculatorService.calculate_due_date_change_fee(
            rental_value=rental_value,
            current_due_day=5,
            new_due_day=10
        )
        assert change_result['fee'] == Decimal('250.00')

    def test_edge_case_very_low_rental(self):
        """Test fee calculations with very low rental value."""
        rental_value = Decimal('300.00')  # Very low rent

        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)
        assert daily_rate == Decimal('10.00')

        late_result = FeeCalculatorService.calculate_late_fee(
            rental_value=rental_value,
            due_day=1,
            current_date=date(2025, 1, 15)
        )
        # 14 days late * 10.00 daily * 0.05 = 7.00
        assert late_result['late_fee'] == Decimal('7.00')

    def test_edge_case_very_high_rental(self):
        """Test fee calculations with very high rental value."""
        rental_value = Decimal('10000.00')  # Very high rent

        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)
        expected_daily_rate = Decimal('10000') / Decimal('30')
        assert daily_rate == expected_daily_rate

        tag_fee = FeeCalculatorService.calculate_tag_fee(1)
        assert tag_fee == Decimal('50.00')  # Same regardless of rental value
