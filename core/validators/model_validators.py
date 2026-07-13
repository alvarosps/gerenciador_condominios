"""
Model-level validators for business logic validation.

Provides validators for model fields and cross-field validation.
"""

from datetime import date
from typing import Any

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

# Validation constants
_DUE_DAY_MIN = 1
_DUE_DAY_MAX = 31
_VALIDITY_MONTHS_MIN = 1
_VALIDITY_MONTHS_MAX = 60
_LEASE_HISTORY_YEARS_MAX = 10
_RENTAL_VALUE_MIN = 100
_RENTAL_VALUE_MAX = 100_000


def validate_due_day(value: int) -> None:
    """
    Validate that due day is between 1 and 31.

    Args:
        value: Day of month (1-31)

    Raises:
        ValidationError: If value is outside valid range

    Example:
        >>> validate_due_day(15)  # Valid
        >>> validate_due_day(0)  # Raises ValidationError
        >>> validate_due_day(32)  # Raises ValidationError
    """
    if value < _DUE_DAY_MIN or value > _DUE_DAY_MAX:
        msg = f"Due day must be between 1 and 31. Got: {value}"
        raise ValidationError(msg, code="invalid_due_day")


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
                field_name: f"{field_name} must be after start date. Start: {start_date}, End: {end_date}"
            },
            code="invalid_date_range",
        )


def validate_lease_dates(lease: Any) -> None:
    """
    Validate lease date consistency.

    Checks that:
    - Start date is not in the distant past (only enforced when start_date is being
      changed — see below)
    - Calculated end date is after start date
    - Validity months is reasonable (1-60 months)

    Args:
        lease: Lease instance to validate

    Raises:
        ValidationError: If lease dates are inconsistent
    """
    # Local import: core.models imports this module at load time, and
    # core.services.timezone is reached through the core.services package
    # __init__ (which imports ContractService -> core.models) — a top-level
    # import here would create a circular import during core.models init.
    from core.services.timezone import today_sp

    errors = {}

    # Validate validity months
    if lease.validity_months < _VALIDITY_MONTHS_MIN:
        errors["validity_months"] = "Validity must be at least 1 month."
    elif lease.validity_months > _VALIDITY_MONTHS_MAX:
        errors["validity_months"] = "Validity cannot exceed 60 months (5 years)."

    # Calculate end date and validate
    if lease.start_date and lease.validity_months:
        end_date = lease.start_date + relativedelta(months=lease.validity_months)
        if end_date <= lease.start_date:
            errors["validity_months"] = "Calculated end date must be after start date."

    # Validate start date is not too far in the past — only when start_date is actually
    # being changed. ``save()`` calls ``full_clean()`` on every save (not just create), so
    # without this guard a genuinely historical lease (start_date > 10 years ago, created
    # legitimately when it was recent) would become permanently uneditable: any unrelated
    # field update would re-trigger this check against today's date and fail.
    if lease.start_date and _is_start_date_changing(lease):
        years_ago = today_sp().year - lease.start_date.year
        if years_ago > _LEASE_HISTORY_YEARS_MAX:
            errors["start_date"] = "Start date cannot be more than 10 years in the past."

    if errors:
        raise ValidationError(errors)


def _is_start_date_changing(lease: Any) -> bool:
    """Whether ``lease.start_date`` differs from the value currently persisted.

    A new (unsaved) lease has no persisted value, so its start_date is always
    "changing". An existing lease is compared against its current DB value.
    """
    if not lease.pk:
        return True
    persisted_start_date = (
        type(lease).objects.filter(pk=lease.pk).values_list("start_date", flat=True).first()
    )
    return bool(persisted_start_date != lease.start_date)


def validate_tenant_count(lease: Any) -> None:
    """
    Validate that number_of_tenants is 1 or 2 and does not exceed apartment max_tenants.

    Args:
        lease: Lease instance to validate

    Raises:
        ValidationError: If number_of_tenants is not 1 or 2, or exceeds apartment.max_tenants

    Example:
        >>> lease.number_of_tenants = 1
        >>> validate_tenant_count(lease)  # OK

        >>> lease.number_of_tenants = 3
        >>> validate_tenant_count(lease)  # Raises ValidationError (must be 1 or 2)

        >>> lease.number_of_tenants = 2
        >>> lease.apartment.max_tenants = 1
        >>> validate_tenant_count(lease)  # Raises ValidationError (exceeds max_tenants)
    """
    if lease.number_of_tenants not in (1, 2):
        raise ValidationError(
            {"number_of_tenants": "Number of tenants must be 1 or 2."},
            code="tenant_count_invalid",
        )

    if lease.apartment_id and lease.number_of_tenants > lease.apartment.max_tenants:
        raise ValidationError(
            {
                "number_of_tenants": f"Number of tenants ({lease.number_of_tenants}) "
                f"exceeds apartment maximum ({lease.apartment.max_tenants})."
            },
            code="tenant_count_exceeds_max",
        )


def validate_tenant_deletable(tenant: Any) -> None:
    """
    Validate that a tenant can be soft-deleted.

    A tenant who is the responsible party on a non-deleted (active) lease cannot be
    deleted — the lease must be terminated or transferred to another tenant first.

    Args:
        tenant: Tenant instance to validate

    Raises:
        ValidationError: If the tenant is the responsible_tenant of an active lease
    """
    if tenant.leases_responsible.exists():
        msg = (
            "Não é possível excluir um inquilino responsável por uma locação ativa. "
            "Encerre ou transfira a locação primeiro."
        )
        raise ValidationError(msg, code="tenant_has_active_lease")


def validate_rental_value(value: float) -> None:
    """
    Validate that rental value is reasonable.

    Args:
        value: Rental value amount

    Raises:
        ValidationError: If value is unreasonable
    """
    if value < 0:
        msg = "Rental value cannot be negative."
        raise ValidationError(msg)

    if value < _RENTAL_VALUE_MIN:
        msg = "Rental value seems too low. Minimum: R$ 100.00"
        raise ValidationError(msg, code="rental_value_too_low")

    if value > _RENTAL_VALUE_MAX:
        msg = "Rental value seems too high. Maximum: R$ 100,000.00"
        raise ValidationError(msg, code="rental_value_too_high")
