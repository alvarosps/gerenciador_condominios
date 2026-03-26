"""Rent adjustment service for Condomínios Manager.

Handles applying rent adjustments to leases and querying leases eligible
for their next annual adjustment.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Lease, RentAdjustment

_ADJUSTMENT_INTERVAL_MONTHS = 12
_RECENT_ADJUSTMENT_WARNING_MONTHS = 10
_TWO_DECIMAL_PLACES = Decimal("0.01")


class RentAdjustmentService:
    """Service for applying and querying rent adjustments."""

    @staticmethod
    @transaction.atomic
    def apply_adjustment(
        lease: Lease,
        percentage: Decimal,
        update_apartment_prices: bool,
    ) -> tuple[RentAdjustment, dict[str, Any] | None]:
        """Apply a rent adjustment to a lease.

        Args:
            lease: The lease to adjust.
            percentage: Adjustment percentage (positive = increase, negative = decrease).
            update_apartment_prices: Whether to update the apartment's rental values.

        Returns:
            Tuple of (RentAdjustment, warning_dict | None).
            Warning is present when a prior adjustment was made within the last
            _RECENT_ADJUSTMENT_WARNING_MONTHS months.

        Raises:
            ValidationError: If percentage is zero or lease is not active.
        """
        if percentage == 0:
            msg = "O percentual de reajuste não pode ser zero."
            raise ValidationError(msg)

        today = date.today()
        end_date = lease.start_date + relativedelta(months=lease.validity_months)
        if end_date <= today:
            msg = "Não é possível reajustar uma locação encerrada."
            raise ValidationError(msg)

        multiplier = Decimal(1) + percentage / Decimal(100)
        new_value = (lease.rental_value * multiplier).quantize(
            _TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
        )

        adjustment = RentAdjustment.objects.create(
            lease=lease,
            adjustment_date=today,
            percentage=percentage,
            previous_value=lease.rental_value,
            new_value=new_value,
            apartment_updated=update_apartment_prices,
        )

        lease.rental_value = new_value
        lease.save()

        if update_apartment_prices:
            apartment = lease.apartment
            apartment.rental_value = (apartment.rental_value * multiplier).quantize(
                _TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
            )
            if apartment.rental_value_double is not None:
                apartment.rental_value_double = (
                    apartment.rental_value_double * multiplier
                ).quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
            apartment.last_rent_increase_date = today
            apartment.save()

        warning = RentAdjustmentService._check_recent_adjustment_warning(lease, adjustment, today)
        return adjustment, warning

    @staticmethod
    def _check_recent_adjustment_warning(
        lease: Lease, current_adjustment: RentAdjustment, today: date
    ) -> dict[str, Any] | None:
        """Return a warning dict if a prior adjustment exists within the warning window."""
        cutoff = today - relativedelta(months=_RECENT_ADJUSTMENT_WARNING_MONTHS)
        prior = (
            RentAdjustment.objects.filter(
                lease=lease,
                adjustment_date__gte=cutoff,
            )
            .exclude(pk=current_adjustment.pk)
            .order_by("-adjustment_date")
            .first()
        )
        if prior is None:
            return None
        return {
            "type": "recent_adjustment",
            "last_date": prior.adjustment_date.strftime("%Y-%m-%d"),
        }

    @staticmethod
    def get_eligible_leases(alert_months: int = 2) -> list[dict[str, Any]]:
        """Return leases that are eligible or nearly eligible for a rent adjustment.

        A lease is eligible 12 months after its last adjustment (or start date
        if never adjusted). Leases are included when the eligible date falls
        within the next ``alert_months`` months or is already past.

        Args:
            alert_months: How many months ahead to look for upcoming eligibility.

        Returns:
            List of dicts with lease info and adjustment eligibility metadata.
        """
        today = date.today()
        alert_cutoff = today + relativedelta(months=alert_months)

        leases = (
            Lease.objects.filter(is_deleted=False, is_salary_offset=False)
            .select_related("apartment", "apartment__building", "responsible_tenant")
            .prefetch_related("rent_adjustments")
        )

        result: list[dict[str, Any]] = []

        for lease in leases:
            end_date = lease.start_date + relativedelta(months=lease.validity_months)
            if end_date <= today:
                continue

            adjustments = sorted(
                lease.rent_adjustments.all(),
                key=lambda ra: ra.adjustment_date,
                reverse=True,
            )
            last_adjustment = adjustments[0] if adjustments else None

            reference_date: date = (
                last_adjustment.adjustment_date if last_adjustment else lease.start_date
            )
            eligible_date = reference_date + relativedelta(months=_ADJUSTMENT_INTERVAL_MONTHS)

            if eligible_date > alert_cutoff:
                continue

            days_until = (eligible_date - today).days
            status = "overdue" if days_until < 0 else "upcoming"

            prepaid_warning = bool(lease.prepaid_until is not None and lease.prepaid_until > today)

            last_adjustment_dict: dict[str, Any] | None = None
            if last_adjustment is not None:
                last_adjustment_dict = {
                    "id": last_adjustment.pk,
                    "date": last_adjustment.adjustment_date.strftime("%Y-%m-%d"),
                    "percentage": str(last_adjustment.percentage),
                }

            apartment = lease.apartment
            building = apartment.building
            result.append(
                {
                    "lease_id": lease.pk,
                    "apartment": f"Apto {apartment.number} - {building.name}",
                    "tenant": lease.responsible_tenant.name,
                    "rental_value": str(lease.rental_value),
                    "eligible_date": eligible_date.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "status": status,
                    "last_adjustment": last_adjustment_dict,
                    "prepaid_warning": prepaid_warning,
                }
            )

        return result
