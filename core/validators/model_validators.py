"""
Model-level validators for business logic validation.

Provides validators for model fields and cross-field validation.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from core.models import Lease


def validate_due_day(value: int) -> None:
    """
    Validate that due day is between 1 and 31.

    Args:
        value: Day of month (1-31)

    Raises:
        ValidationError: If value is outside valid range

    Example:
        >>> validate_due_day(15)  # Valid
        >>> validate_due_day(0)   # Raises ValidationError
        >>> validate_due_day(32)  # Raises ValidationError
    """
    if not isinstance(value, int):
        raise ValidationError("Due day must be an integer.")

    if value < 1 or value > 31:
        raise ValidationError(
            f"Due day must be between 1 and 31. Got: {value}", code="invalid_due_day"
        )


def validate_date_range(start_date: date, end_date: date, field_name: str = "end_date") -> None:
    """
    Validate that end date is after start date.

    Args:
        start_date: Start date
        end_date: End date
        field_name: Name of end date field for error message

    Raises:
        ValidationError: If end_date is not after start_date

    Example:
        >>> validate_date_range(date(2025, 1, 1), date(2025, 12, 31))  # Valid
        >>> validate_date_range(date(2025, 12, 31), date(2025, 1, 1))  # Raises
    """
    if end_date <= start_date:
        raise ValidationError(
            {
                field_name: f"{field_name} must be after start date. "
                f"Start: {start_date}, End: {end_date}"
            },
            code="invalid_date_range",
        )


def validate_lease_dates(lease: Lease) -> None:
    """
    Validate lease date consistency.

    Checks that:
    - Start date is not in the distant past
    - Calculated end date is after start date
    - Validity months is reasonable (1-60 months)

    Args:
        lease: Lease instance to validate

    Raises:
        ValidationError: If lease dates are inconsistent
    """
    from dateutil.relativedelta import relativedelta

    errors = {}

    # Validate validity months
    if lease.validity_months < 1:
        errors["validity_months"] = "Validity must be at least 1 month."
    elif lease.validity_months > 60:
        errors["validity_months"] = "Validity cannot exceed 60 months (5 years)."

    # Calculate end date and validate
    if lease.start_date and lease.validity_months:
        end_date = lease.start_date + relativedelta(months=lease.validity_months)
        if end_date <= lease.start_date:
            errors["validity_months"] = "Calculated end date must be after start date."

    # Validate start date is not too far in the past
    if lease.start_date:
        years_ago = date.today().year - lease.start_date.year
        if years_ago > 10:
            errors["start_date"] = "Start date cannot be more than 10 years in the past."

    if errors:
        raise ValidationError(errors)


def validate_tenant_count(lease: Lease) -> None:
    """
    Validate that number_of_tenants is at least the actual tenant count.

    Allows declaring more occupants than registered tenants (e.g., for tag fee calculation
    when additional people will live there but aren't formally registered as tenants).

    Args:
        lease: Lease instance to validate

    Raises:
        ValidationError: If declared count is less than actual count

    Example:
        >>> lease.number_of_tenants = 1
        >>> lease.tenants.count() = 2
        >>> validate_tenant_count(lease)  # Raises ValidationError (can't have fewer declared)

        >>> lease.number_of_tenants = 2
        >>> lease.tenants.count() = 1
        >>> validate_tenant_count(lease)  # OK (can declare more occupants)
    """
    if lease.pk:  # Only validate if lease is saved (tenants relationship exists)
        actual_count = lease.tenants.count()
        if lease.number_of_tenants < actual_count:
            raise ValidationError(
                {
                    "number_of_tenants": f"Number of tenants ({lease.number_of_tenants}) "
                    f"cannot be less than actual registered tenant count ({actual_count}). "
                    f"You can declare more occupants, but not fewer than registered tenants."
                },
                code="tenant_count_too_low",
            )


def validate_rental_value(value: float) -> None:
    """
    Validate that rental value is reasonable.

    Args:
        value: Rental value amount

    Raises:
        ValidationError: If value is unreasonable
    """
    if value < 0:
        raise ValidationError("Rental value cannot be negative.")

    if value < 100:
        raise ValidationError(
            "Rental value seems too low. Minimum: R$ 100.00", code="rental_value_too_low"
        )

    if value > 100000:
        raise ValidationError(
            "Rental value seems too high. Maximum: R$ 100,000.00", code="rental_value_too_high"
        )
