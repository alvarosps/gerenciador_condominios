"""
Fee calculation service for Condomínios Manager.

This service handles all fee-related business logic:
- Late payment fee calculations
- Due date change fee calculations
- Tag fee calculations based on tenant count
- Total value calculations
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Union

from django.conf import settings


class FeeCalculatorService:
    """
    Service class for calculating various fees in the lease management system.

    All calculations use Decimal for precision with currency values.
    """

    @staticmethod
    def calculate_daily_rate(rental_value: Decimal) -> Decimal:
        """
        Calculate the daily rental rate based on monthly rental value.

        Args:
            rental_value: Monthly rental value in BRL

        Returns:
            Daily rental rate (rental_value / DAYS_PER_MONTH)

        Examples:
            >>> FeeCalculatorService.calculate_daily_rate(Decimal('1500.00'))
            Decimal('50.00')  # 1500 / 30
        """
        days_per_month = Decimal(str(settings.DAYS_PER_MONTH))
        return rental_value / days_per_month

    @staticmethod
    def calculate_late_fee(
        rental_value: Decimal, due_day: int, current_date: date
    ) -> Dict[str, Union[int, Decimal, str]]:
        """
        Calculate late payment fee based on days overdue.

        The fee is calculated as:
        late_fee = daily_rate × days_late × LATE_FEE_PERCENTAGE

        Args:
            rental_value: Monthly rental value in BRL
            due_day: Day of month when rent is due (1-31)
            current_date: Current date to calculate from

        Returns:
            Dictionary with:
                - is_late (bool): Whether payment is late
                - late_days (int): Number of days late (0 if not late)
                - late_fee (Decimal): Late fee amount (0.00 if not late)
                - message (str): Descriptive message

        Examples:
            >>> service = FeeCalculatorService()
            >>> result = service.calculate_late_fee(
            ...     Decimal('1500.00'),
            ...     10,
            ...     date(2025, 1, 15)
            ... )
            >>> result['late_days']
            5
            >>> result['late_fee']
            Decimal('375.00')  # (1500/30) × 5 × 1.05
        """
        if current_date.day > due_day:
            late_days = current_date.day - due_day
            daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)
            late_fee_percentage = Decimal(str(settings.LATE_FEE_PERCENTAGE))
            late_fee = daily_rate * late_days * late_fee_percentage

            return {
                "is_late": True,
                "late_days": late_days,
                "late_fee": late_fee,
                "message": f"Pagamento atrasado há {late_days} dia(s).",
            }
        else:
            return {
                "is_late": False,
                "late_days": 0,
                "late_fee": Decimal("0.00"),
                "message": "Aluguel não está atrasado.",
            }

    @staticmethod
    def calculate_due_date_change_fee(
        rental_value: Decimal, current_due_day: int, new_due_day: int
    ) -> Dict[str, Union[int, Decimal]]:
        """
        Calculate fee for changing the rental due date.

        The fee is proportional to the difference in days:
        fee = daily_rate × |new_due_day - current_due_day|

        Args:
            rental_value: Monthly rental value in BRL
            current_due_day: Current due day (1-31)
            new_due_day: New desired due day (1-31)

        Returns:
            Dictionary with:
                - days_difference (int): Absolute difference in days
                - fee (Decimal): Fee for changing due date
                - daily_rate (Decimal): Daily rental rate used

        Examples:
            >>> service = FeeCalculatorService()
            >>> result = service.calculate_due_date_change_fee(
            ...     Decimal('1500.00'),
            ...     10,
            ...     15
            ... )
            >>> result['days_difference']
            5
            >>> result['fee']
            Decimal('250.00')  # (1500/30) × 5
        """
        days_difference = abs(new_due_day - current_due_day)
        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value)
        fee = daily_rate * days_difference

        return {"days_difference": days_difference, "fee": fee, "daily_rate": daily_rate}

    @staticmethod
    def calculate_tag_fee(num_tenants: int) -> Decimal:
        """
        Calculate tag deposit fee based on number of tenants.

        Fee structure:
        - 1 tenant: DEFAULT_TAG_FEE_SINGLE (typically R$50.00)
        - 2+ tenants: DEFAULT_TAG_FEE_MULTIPLE (typically R$80.00)

        Args:
            num_tenants: Number of tenants in the lease

        Returns:
            Tag fee amount

        Raises:
            ValueError: If num_tenants is less than 1

        Examples:
            >>> FeeCalculatorService.calculate_tag_fee(1)
            Decimal('50.00')
            >>> FeeCalculatorService.calculate_tag_fee(2)
            Decimal('80.00')
            >>> FeeCalculatorService.calculate_tag_fee(3)
            Decimal('80.00')
        """
        if num_tenants < 1:
            raise ValueError("Number of tenants must be at least 1")

        if num_tenants == 1:
            return Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))
        else:
            return Decimal(str(settings.DEFAULT_TAG_FEE_MULTIPLE))

    @staticmethod
    def calculate_total_value(
        rental_value: Decimal, cleaning_fee: Decimal, tag_fee: Decimal
    ) -> Decimal:
        """
        Calculate total initial payment value.

        This represents the first payment required when starting a lease:
        total = rental_value + cleaning_fee + tag_fee

        Args:
            rental_value: Monthly rental value
            cleaning_fee: One-time cleaning fee
            tag_fee: Tag deposit fee

        Returns:
            Total amount due for first payment

        Examples:
            >>> FeeCalculatorService.calculate_total_value(
            ...     Decimal('1500.00'),
            ...     Decimal('200.00'),
            ...     Decimal('80.00')
            ... )
            Decimal('1780.00')
        """
        return rental_value + cleaning_fee + tag_fee
