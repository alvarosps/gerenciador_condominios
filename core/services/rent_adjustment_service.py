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
from django.utils import timezone

from core.models import Landlord, Lease, RentAdjustment
from core.services.ipca_service import IPCAService

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
        renewal_date: date | None = None,
    ) -> tuple[RentAdjustment, dict[str, Any] | None]:
        """Apply a rent adjustment to a lease.

        Args:
            lease: The lease to adjust.
            percentage: Adjustment percentage (positive = increase, negative = decrease).
            update_apartment_prices: Whether to update the apartment's rental values.
            renewal_date: Custom renewal date for the adjustment (defaults to today).

        Returns:
            Tuple of (RentAdjustment, warning_dict | None).

        Raises:
            ValidationError: If percentage is zero.
        """
        if percentage == 0:
            msg = "O percentual de reajuste não pode ser zero."
            raise ValidationError(msg)

        # Re-fetch with a row lock to prevent concurrent double-adjustments
        lease = Lease.objects.select_for_update().get(pk=lease.pk)

        today = timezone.now().date()
        adjustment_date = renewal_date or today

        multiplier = Decimal(1) + percentage / Decimal(100)
        new_value = (lease.rental_value * multiplier).quantize(
            _TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
        )

        adjustment = RentAdjustment.objects.create(
            lease=lease,
            adjustment_date=adjustment_date,
            percentage=percentage,
            previous_value=lease.rental_value,
            new_value=new_value,
            apartment_updated=update_apartment_prices,
        )

        is_future = adjustment_date.replace(day=1) > today.replace(day=1)

        if is_future:
            # Future adjustment: save as pending, don't change current values
            lease.pending_rental_value = new_value
            lease.pending_rental_value_date = adjustment_date
            lease.save()
        else:
            # Current/past adjustment: apply immediately
            RentAdjustmentService._apply_to_lease_and_apartment(
                lease, new_value, adjustment_date, update_apartment_prices, multiplier
            )

        warning = RentAdjustmentService._check_recent_adjustment_warning(lease, adjustment, today)
        return adjustment, warning

    @staticmethod
    def _apply_to_lease_and_apartment(
        lease: Lease,
        new_value: Decimal,
        adjustment_date: date,
        update_apartment_prices: bool,
        multiplier: Decimal,
    ) -> None:
        """Apply the adjustment values to lease and apartment."""
        lease.rental_value = new_value
        lease.last_rent_increase_date = adjustment_date
        lease.pending_rental_value = None
        lease.pending_rental_value_date = None
        lease.save()

        apartment = lease.apartment
        if update_apartment_prices:
            apartment.rental_value = (apartment.rental_value * multiplier).quantize(
                _TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
            )
            if apartment.rental_value_double is not None:
                apartment.rental_value_double = (
                    apartment.rental_value_double * multiplier
                ).quantize(_TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
        apartment.last_rent_increase_date = adjustment_date
        apartment.save()

    @staticmethod
    @transaction.atomic
    def activate_pending_adjustments() -> int:
        """Activate pending adjustments whose month has arrived.

        Called automatically when the dashboard is loaded. Checks all leases
        with pending values and applies them if the current month >= pending month.

        Returns:
            Number of adjustments activated.
        """
        today = timezone.now().date()
        current_month_start = today.replace(day=1)

        pending_leases = (
            Lease.objects.select_for_update()
            .filter(
                pending_rental_value__isnull=False,
                pending_rental_value_date__isnull=False,
            )
            .select_related("apartment")
        )

        activated = 0
        for lease in pending_leases:
            pending_date = lease.pending_rental_value_date
            if pending_date is None or lease.pending_rental_value is None:
                continue

            if pending_date.replace(day=1) <= current_month_start:
                # Find the original adjustment to get the multiplier
                adjustment = (
                    RentAdjustment.objects.filter(
                        lease=lease,
                        new_value=lease.pending_rental_value,
                    )
                    .order_by("-adjustment_date")
                    .first()
                )

                update_apt = adjustment.apartment_updated if adjustment else True
                previous_value = adjustment.previous_value if adjustment else lease.rental_value
                multiplier = (
                    lease.pending_rental_value / previous_value
                    if previous_value > 0
                    else Decimal(1)
                )

                RentAdjustmentService._apply_to_lease_and_apartment(
                    lease,
                    lease.pending_rental_value,
                    pending_date,
                    update_apt,
                    multiplier,
                )
                activated += 1

        return activated

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
    def get_eligible_leases(alert_months: int = 2) -> dict[str, Any]:
        """Return leases eligible for rent adjustment with IPCA data.

        Returns:
            Dict with alerts list, IPCA metadata, and fallback percentage.
        """

        today = timezone.now().date()
        alert_cutoff = today + relativedelta(months=alert_months)

        # Fetch latest IPCA data (will only hit API if new months available)
        IPCAService.fetch_latest()
        latest_ipca_month = IPCAService.get_latest_available_month()

        # Calculate a single IPCA percentage: last 12 months from latest available
        ipca_12m: Decimal | None = None
        if latest_ipca_month:
            twelve_months_ago = latest_ipca_month - relativedelta(months=11)
            ipca_12m = IPCAService.get_adjustment_percentage(twelve_months_ago, latest_ipca_month)

        # Fallback percentage from Landlord settings
        landlord = Landlord.objects.filter(is_active=True).first()
        fallback_pct = landlord.rent_adjustment_percentage if landlord else Decimal("0.00")
        effective_pct = ipca_12m if ipca_12m is not None else fallback_pct
        ipca_source = "ipca" if ipca_12m is not None else "fallback"

        leases = (
            Lease.objects.filter(
                is_deleted=False,
                is_salary_offset=False,
                apartment__is_rented=True,
                pending_rental_value__isnull=True,
            )
            .select_related("apartment", "apartment__building", "responsible_tenant")
            .prefetch_related("rent_adjustments")
        )

        alerts: list[dict[str, Any]] = []

        for lease in leases:
            reference_date: date = lease.last_rent_increase_date or lease.start_date
            eligible_date = reference_date + relativedelta(months=_ADJUSTMENT_INTERVAL_MONTHS)

            if eligible_date > alert_cutoff:
                continue

            adjustments = sorted(
                lease.rent_adjustments.all(),
                key=lambda ra: ra.adjustment_date,
                reverse=True,
            )
            last_adjustment = adjustments[0] if adjustments else None

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
            new_value = (lease.rental_value * (Decimal(1) + effective_pct / Decimal(100))).quantize(
                _TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
            )

            alerts.append(
                {
                    "lease_id": lease.pk,
                    "apartment": f"Apto {apartment.number} - {building.name}",
                    "tenant": lease.responsible_tenant.name,
                    "rental_value": str(lease.rental_value),
                    "eligible_date": eligible_date.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "status": status,
                    "last_adjustment": last_adjustment_dict,
                    "last_rent_increase_date": reference_date.strftime("%Y-%m-%d"),
                    "prepaid_warning": prepaid_warning,
                    "ipca_percentage": str(effective_pct),
                    "ipca_source": ipca_source,
                    "new_value": str(new_value),
                }
            )

        alerts.sort(key=lambda a: a["days_until"])

        return {
            "alerts": alerts,
            "ipca_latest_month": latest_ipca_month.strftime("%Y-%m-%d")
            if latest_ipca_month
            else None,
            "fallback_percentage": str(fallback_pct),
            "ipca_percentage": str(effective_pct),
        }
