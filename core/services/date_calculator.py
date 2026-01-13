"""
Date calculation service for Condomínios Manager.

This service handles all date-related business logic:
- Next month date calculations
- Final date calculations with leap year edge cases
- Rent due date checking
- Days until due calculations
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict

from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class DateCalculatorService:
    """
    Service class for handling date calculations in the lease management system.

    This service handles complex edge cases like leap years (Feb 29 -> Feb 28 -> March 1)
    and month boundary calculations.
    """

    @staticmethod
    def calculate_next_month_date(start_date: date) -> date:
        """
        Calculate the date one month from start_date.

        Uses relativedelta to properly handle month boundaries and leap years.

        Args:
            start_date: Starting date

        Returns:
            Date one month later

        Examples:
            >>> DateCalculatorService.calculate_next_month_date(date(2025, 1, 15))
            datetime.date(2025, 2, 15)
            >>> DateCalculatorService.calculate_next_month_date(date(2025, 1, 31))
            datetime.date(2025, 2, 28)  # No Feb 31
            >>> DateCalculatorService.calculate_next_month_date(date(2024, 1, 31))
            datetime.date(2024, 2, 29)  # Leap year
        """
        next_month = start_date + relativedelta(months=1)
        logger.debug(f"Next month from {start_date}: {next_month}")
        return next_month

    @staticmethod
    def calculate_final_date(start_date: date, validity_months: int) -> date:
        """
        Calculate lease end date.

        Handles special edge case: if start_date is Feb 29 (leap year) and the
        calculated end date would be Feb 28 (non-leap year), move it to March 1.

        Args:
            start_date: Lease start date
            validity_months: Lease duration in months

        Returns:
            Lease end date

        Examples:
            >>> DateCalculatorService.calculate_final_date(date(2025, 1, 15), 12)
            datetime.date(2026, 1, 15)
            >>> DateCalculatorService.calculate_final_date(date(2024, 2, 29), 12)
            datetime.date(2025, 3, 1)  # Feb 29 -> Feb 28 -> March 1 edge case
            >>> DateCalculatorService.calculate_final_date(date(2024, 2, 29), 24)
            datetime.date(2026, 2, 28)  # Still non-leap year, stays Feb 28
        """
        calculated_final = start_date + relativedelta(months=validity_months)

        # Special handling for Feb 29 -> Feb 28 edge case
        # If we started on Feb 29 and ended on Feb 28, move to March 1
        if start_date.month == 2 and start_date.day == 29:
            if calculated_final.month == 2 and calculated_final.day == 28:
                calculated_final = calculated_final + timedelta(days=1)
                logger.info(
                    f"Adjusted Feb 28 to March 1 for leap year edge case "
                    f"(start: {start_date}, original end: {calculated_final - timedelta(days=1)})"
                )

        logger.info(f"Final date calculated: {start_date} + {validity_months} months = {calculated_final}")
        return calculated_final

    @staticmethod
    def calculate_lease_dates(start_date: date, validity_months: int) -> Dict[str, Any]:
        """
        Calculate all relevant dates for a lease.

        This provides a complete set of dates needed for contract generation
        and lease management.

        Args:
            start_date: Lease start date
            validity_months: Lease duration in months

        Returns:
            Dictionary with:
                - start_date: Lease start date
                - next_month_date: First payment due date (1 month after start)
                - final_date: Lease end date
                - validity_months: Lease duration

        Examples:
            >>> DateCalculatorService.calculate_lease_dates(
            ...     date(2025, 1, 15), 12
            ... )
            {
                'start_date': datetime.date(2025, 1, 15),
                'next_month_date': datetime.date(2025, 2, 15),
                'final_date': datetime.date(2026, 1, 15),
                'validity_months': 12
            }
        """
        next_month = DateCalculatorService.calculate_next_month_date(start_date)
        final_date = DateCalculatorService.calculate_final_date(start_date, validity_months)

        result = {
            "start_date": start_date,
            "next_month_date": next_month,
            "final_date": final_date,
            "validity_months": validity_months,
        }

        logger.debug(f"Lease dates calculated: {result}")
        return result

    @staticmethod
    def is_rent_due(due_day: int, current_date: date | None = None) -> bool:
        """
        Check if rent is currently due.

        Rent is considered due if the current day is >= due_day.

        Args:
            due_day: Day of month when rent is due (1-31)
            current_date: Date to check (defaults to today)

        Returns:
            True if rent is due, False otherwise

        Examples:
            >>> DateCalculatorService.is_rent_due(10, date(2025, 1, 15))
            True  # Current day (15) >= due day (10)
            >>> DateCalculatorService.is_rent_due(20, date(2025, 1, 15))
            False  # Current day (15) < due day (20)
        """
        if current_date is None:
            current_date = date.today()

        return current_date.day >= due_day

    @staticmethod
    def days_until_due(due_day: int, current_date: date | None = None) -> int:
        """
        Calculate days until next rent due date.

        Args:
            due_day: Day of month when rent is due (1-31)
            current_date: Date to check (defaults to today)

        Returns:
            Number of days until due date (0 if already due or past due)

        Examples:
            >>> DateCalculatorService.days_until_due(10, date(2025, 1, 5))
            5  # 5 days until the 10th
            >>> DateCalculatorService.days_until_due(10, date(2025, 1, 15))
            0  # Already past due
            >>> DateCalculatorService.days_until_due(5, date(2025, 1, 31))
            0  # Past due, next due date is next month
        """
        if current_date is None:
            current_date = date.today()

        if current_date.day < due_day:
            # Due date is later this month
            return due_day - current_date.day
        else:
            # Due date was earlier this month or today, already due
            return 0

    @staticmethod
    def format_date_brazilian(date_obj: date) -> str:
        """
        Format date in Brazilian format (DD/MM/YYYY).

        Args:
            date_obj: Date to format

        Returns:
            Formatted date string

        Examples:
            >>> DateCalculatorService.format_date_brazilian(date(2025, 1, 15))
            '15/01/2025'
        """
        return date_obj.strftime("%d/%m/%Y")

    @staticmethod
    def format_lease_dates_for_contract(start_date: date, validity_months: int) -> Dict[str, str]:
        """
        Format all lease dates for contract template.

        Returns all dates formatted in Brazilian format for use in
        PDF contract generation.

        Args:
            start_date: Lease start date
            validity_months: Lease duration in months

        Returns:
            Dictionary with formatted date strings:
                - start_date_formatted: Start date in DD/MM/YYYY
                - next_month_date_formatted: Next month in DD/MM/YYYY
                - final_date_formatted: End date in DD/MM/YYYY

        Examples:
            >>> DateCalculatorService.format_lease_dates_for_contract(
            ...     date(2025, 1, 15), 12
            ... )
            {
                'start_date_formatted': '15/01/2025',
                'next_month_date_formatted': '15/02/2025',
                'final_date_formatted': '15/01/2026'
            }
        """
        dates = DateCalculatorService.calculate_lease_dates(start_date, validity_months)

        return {
            "start_date_formatted": DateCalculatorService.format_date_brazilian(dates["start_date"]),
            "next_month_date_formatted": DateCalculatorService.format_date_brazilian(dates["next_month_date"]),
            "final_date_formatted": DateCalculatorService.format_date_brazilian(dates["final_date"]),
        }
