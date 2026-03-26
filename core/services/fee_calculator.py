"""
Fee calculation service for Condomínios Manager.

This service handles all fee-related business logic:
- Late payment fee calculations
- Due date change fee calculations
- Tag fee calculations based on tenant count
- Total value calculations
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal

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
            >>> FeeCalculatorService.calculate_daily_rate(Decimal("1500.00"))
            Decimal('50.00')  # 1500 / 30
        """
        days_per_month = Decimal(str(settings.DAYS_PER_MONTH))
        return rental_value / days_per_month

    @staticmethod
    def calculate_late_fee(
        rental_value: Decimal, due_day: int, current_date: date
    ) -> dict[str, int | Decimal | str]:
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
            >>> result = service.calculate_late_fee(Decimal("1500.00"), 10, date(2025, 1, 15))
            >>> result["late_days"]
            5
            >>> result["late_fee"]
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
        return {
            "is_late": False,
            "late_days": 0,
            "late_fee": Decimal("0.00"),
            "message": "Aluguel não está atrasado.",
        }

    @staticmethod
    def _next_month(year: int, month: int) -> tuple[int, int]:
        """Return (year, month) for the month after the given one."""
        if month == 12:
            return year + 1, 1
        return year, month + 1

    @staticmethod
    def _clamp_day(year: int, month: int, day: int) -> date:
        """Build a date clamping the day to the actual days in the month."""
        _, days_in_month = monthrange(year, month)
        return date(year, month, min(day, days_in_month))

    @staticmethod
    def calculate_due_date_change_fee(
        rental_value: Decimal,
        current_due_day: int,
        new_due_day: int,
        reference_date: date | None = None,
    ) -> dict[str, int | Decimal | date]:
        """
        Calculate fee for changing the rental due date.

        Uses real calendar dates to count inclusive days between the old and new
        due dates. The "old due date" is built in the reference month; the "new
        due date" falls in the same month (if new > old) or the next month
        (if new < old).

        Inclusive day count: from old_date to new_date counting both endpoints.

        Example: due_day 22 → 5, reference March 2026
            old_date = 2026-03-22, new_date = 2026-04-05
            days = (Apr 5 − Mar 22) + 1 = 15
            daily_rate = 1250/30 = 41.67
            fee = round(41.67 × 15) = 625
            total_due = 1250 + 625 = 1875
        """
        if reference_date is None:
            reference_date = date.today()

        year, month = reference_date.year, reference_date.month

        old_date = FeeCalculatorService._clamp_day(year, month, current_due_day)

        if new_due_day > current_due_day:
            new_date = FeeCalculatorService._clamp_day(year, month, new_due_day)
        else:
            next_year, next_month = FeeCalculatorService._next_month(year, month)
            new_date = FeeCalculatorService._clamp_day(next_year, next_month, new_due_day)

        days_difference = (new_date - old_date).days + 1  # inclusive count

        daily_rate = FeeCalculatorService.calculate_daily_rate(rental_value).quantize(
            Decimal("0.01")
        )
        fee = int((daily_rate * days_difference).to_integral_value())
        total_due = rental_value + fee

        return {
            "days_difference": days_difference,
            "daily_rate": daily_rate,
            "fee": fee,
            "total_due": total_due,
            "old_due_date": old_date,
            "new_due_date": new_date,
        }

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
            msg = "Number of tenants must be at least 1"
            raise ValueError(msg)

        if num_tenants == 1:
            return Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))
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
            ...     Decimal("1500.00"), Decimal("200.00"), Decimal("80.00")
            ... )
            Decimal('1780.00')
        """
        return rental_value + cleaning_fee + tag_fee
