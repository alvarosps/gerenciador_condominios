"""
Rent schedule service for Condomínios Manager.

Single source of truth for "rent due this month" logic:
- Clamping the due day to the actual number of days in the month.
- Effective rental value honoring pending rent increases.
- Collectible leases (date-aware window, excluding owner/salary-offset/prepaid).
- Month schedule (day-by-day items) and month stats for the rent calendar.
- Toggling a monthly rent payment (create / soft-delete) with full revalidation.

Money uses Decimal; serialized values are returned as str. Date arithmetic is
pure (all relevant fields are DateField). User-facing messages are in Portuguese;
logs are in English. Late fee is reused from FeeCalculatorService and lease end
date from DateCalculatorService (no duplication).
"""

import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, QuerySet, Sum
from django.utils import timezone

from core.models import Apartment, Lease, MonthSnapshot, RentPayment
from core.services.date_calculator import DateCalculatorService
from core.services.fee_calculator import FeeCalculatorService

logger = logging.getLogger(__name__)

DAYS_OF_WEEK_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}

ZERO = Decimal("0.00")


class RentScheduleService:
    """Single source of truth for monthly rent-due scheduling and toggling."""

    @staticmethod
    def clamp_due_day(due_day: int, year: int, month: int) -> int:
        """Clamp the due day to the last day of the month.

        Example: 31 in February 2026 -> 28; in April -> 30.
        """
        _, days_in_month = monthrange(year, month)
        return min(due_day, days_in_month)

    @staticmethod
    def effective_rental_value(lease: Lease, reference_month: date) -> Decimal:
        """Effective rent for the month.

        Returns ``rental_value`` unless a pending increase is in effect for the
        month — i.e. both ``pending_rental_value`` and ``pending_rental_value_date``
        are set and the month has reached the pending date. The comparison is
        month-granular (``reference_month >= pending_rental_value_date`` clamped to
        the first of its month) to match ``RentAdjustmentService.activate_pending_adjustments``,
        so a mid-month pending date activates the increase for that whole month.
        """
        if (
            lease.pending_rental_value is not None
            and lease.pending_rental_value_date is not None
            and reference_month >= lease.pending_rental_value_date.replace(day=1)
        ):
            return lease.pending_rental_value
        return lease.rental_value

    @staticmethod
    def collectible_leases(
        reference_month: date, building_id: int | None = None
    ) -> QuerySet[Lease]:
        """Collectible leases that cover the month (single source of truth).

        Collectibility is purely date-aware (it does NOT depend on the
        ``apartment.is_rented`` boolean):
        - not soft-deleted (default ``Lease.objects`` manager),
        - ``apartment.owner`` is null (owner repass is not condominium revenue),
        - ``is_salary_offset=False``,
        - the month is not prepaid (``prepaid_until`` does not cover it),
        - the window ``start_date..end_date`` intersects the month, where
          ``end_date = DateCalculatorService.calculate_final_date(start_date, validity_months)``.

        ORM-expressible filters (owner, salary offset, prepaid, building,
        ``start_date <= last day of month``) stay in the queryset; the upper bound
        (computed end date) is applied in Python over the already-reduced queryset.
        """
        year, month = reference_month.year, reference_month.month
        _, days_in_month = monthrange(year, month)
        month_end = date(year, month, days_in_month)

        queryset = (
            Lease.objects.filter(start_date__lte=month_end)
            .exclude(apartment__owner__isnull=False)
            .exclude(is_salary_offset=True)
            .exclude(prepaid_until__gte=reference_month)
            .select_related("apartment", "apartment__building", "responsible_tenant")
        )

        if building_id is not None:
            queryset = queryset.filter(apartment__building_id=building_id)

        collectible_ids = [
            lease.pk
            for lease in queryset
            if DateCalculatorService.calculate_final_date(lease.start_date, lease.validity_months)
            >= reference_month
        ]
        return queryset.filter(id__in=collectible_ids)

    @staticmethod
    def get_month_schedule(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Full month structure for the rent calendar.

        Returns ``year``, ``month``, ``today`` (iso), ``next_due_date`` (iso|None),
        ``days`` (each with ``items``) and ``stats``. The month label is derived on
        the frontend (not returned here).
        """
        reference_month = date(year, month, 1)
        today = timezone.now().date()
        is_current_month = (year, month) == (today.year, today.month)
        month_finalized = RentScheduleService._is_month_finalized(reference_month)

        _, days_in_month = monthrange(year, month)
        leases = list(RentScheduleService.collectible_leases(reference_month, building_id))
        payments = RentScheduleService._active_payments_by_lease(reference_month)

        items_by_day: dict[int, list[dict[str, Any]]] = {}
        next_due_date: date | None = None

        for lease in leases:
            clamped_due = RentScheduleService.clamp_due_day(
                lease.responsible_tenant.due_day, year, month
            )
            clamped_due_date = date(year, month, clamped_due)
            payment = payments.get(lease.pk)
            item = RentScheduleService._build_item(
                lease=lease,
                reference_month=reference_month,
                clamped_due=clamped_due,
                clamped_due_date=clamped_due_date,
                payment=payment,
                today=today,
                is_current_month=is_current_month,
                month_finalized=month_finalized,
            )
            items_by_day.setdefault(clamped_due, []).append(item)

            if (
                not item["is_paid"]
                and clamped_due_date >= today
                and (next_due_date is None or clamped_due_date < next_due_date)
            ):
                next_due_date = clamped_due_date

        days = [
            {
                "day": day_num,
                "date": date(year, month, day_num).isoformat(),
                "weekday": DAYS_OF_WEEK_PT[date(year, month, day_num).weekday()],
                "items": items_by_day.get(day_num, []),
            }
            for day_num in range(1, days_in_month + 1)
        ]

        return {
            "year": year,
            "month": month,
            "today": today.isoformat(),
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
            "days": days,
            "stats": RentScheduleService.get_month_stats(year, month, building_id),
        }

    @staticmethod
    def get_month_stats(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Aggregated month stats for the rent calendar.

        ``received_total`` sums ``amount_paid`` of ALL active RentPayments of the
        month (reference_month = day 1) WITHOUT a collectibility filter — this is
        the canonical definition of "rent received". ``to_receive_total`` and
        ``due_count`` are based on collectible leases. Late fee is only computed
        for the current month (cross-month months report 0).
        """
        reference_month = date(year, month, 1)
        today = timezone.now().date()
        is_current_month = (year, month) == (today.year, today.month)
        is_current_or_past = (year, month) <= (today.year, today.month)

        received_total = RentScheduleService.received_total(reference_month, building_id)

        leases = list(RentScheduleService.collectible_leases(reference_month, building_id))
        payments = RentScheduleService._active_payments_by_lease(reference_month)

        to_receive_total = ZERO
        paid_count = 0
        overdue_count = 0
        overdue_total_fee = ZERO

        for lease in leases:
            effective_value = RentScheduleService.effective_rental_value(lease, reference_month)
            is_paid = lease.pk in payments
            if is_paid:
                paid_count += 1
            else:
                to_receive_total += effective_value

            clamped_due = RentScheduleService.clamp_due_day(
                lease.responsible_tenant.due_day, year, month
            )
            clamped_due_date = date(year, month, clamped_due)
            if not is_paid and clamped_due_date < today and is_current_or_past:
                overdue_count += 1
                if is_current_month:
                    fee = FeeCalculatorService.calculate_late_fee(
                        effective_value, clamped_due, today
                    )
                    overdue_total_fee += _as_decimal(fee["late_fee"])

        vacant_count, vacant_value = RentScheduleService._vacant_kitnets(building_id)

        return {
            "received_total": str(received_total),
            "to_receive_total": str(to_receive_total),
            "expected_total": str(received_total + to_receive_total),
            "paid_count": paid_count,
            "due_count": len(leases),
            "overdue_count": overdue_count,
            "overdue_total_fee": str(overdue_total_fee),
            "vacant_kitnets_count": vacant_count,
            "vacant_kitnets_value": str(vacant_value),
        }

    @staticmethod
    def received_total(reference_month: date, building_id: int | None = None) -> Decimal:
        """Canonical "rent received" for the month.

        Sum of ``amount_paid`` of all active RentPayments whose ``reference_month``
        is the first day of the month — WITHOUT pre-filtering by collectibility.
        Honors the optional ``building_id`` so building-scoped stats stay coherent
        with ``to_receive_total`` (which is already building-scoped).
        """
        payments = RentPayment.objects.filter(reference_month=reference_month)
        if building_id is not None:
            payments = payments.filter(lease__apartment__building_id=building_id)
        return payments.aggregate(total=Sum("amount_paid"))["total"] or ZERO

    @staticmethod
    def toggle_payment(lease_id: int, reference_month: date, user: User) -> dict[str, Any]:
        """Create or soft-delete the month's RentPayment (defense in depth).

        Revalidates collectibility, month finalization and the unpay guard
        (already paid AND due day passed). Returns ``{status, is_paid, message}``.
        """
        reference_month = reference_month.replace(day=1)
        today = timezone.now().date()
        is_paid = RentPayment.objects.filter(
            lease_id=lease_id, reference_month=reference_month
        ).exists()

        if RentScheduleService._is_month_finalized(reference_month):
            return _error("O mês está finalizado e não pode ser alterado.", is_paid)

        if not RentScheduleService.collectible_leases(reference_month).filter(id=lease_id).exists():
            return _error("Este aluguel não é cobrável neste mês.", is_paid)

        with transaction.atomic():
            lease = (
                Lease.objects.select_for_update()
                .select_related("responsible_tenant")
                .get(id=lease_id)
            )
            payment = (
                RentPayment.objects.filter(lease_id=lease_id, reference_month=reference_month)
                .select_for_update()
                .first()
            )

            # Re-check finalization inside the locked block (defense against a
            # concurrent month finalization between the pre-check and the mutation).
            if RentScheduleService._is_month_finalized(reference_month):
                return _error("O mês está finalizado e não pode ser alterado.", payment is not None)

            if payment is None:
                amount = RentScheduleService.effective_rental_value(lease, reference_month)
                RentPayment.objects.create(
                    lease=lease,
                    reference_month=reference_month,
                    amount_paid=amount,
                    payment_date=today,
                    created_by=user,
                    updated_by=user,
                )
                logger.info("Created rent payment for lease %s (%s)", lease_id, reference_month)
                return {"status": "ok", "is_paid": True, "message": "Aluguel marcado como pago."}

            clamped_due = RentScheduleService.clamp_due_day(
                lease.responsible_tenant.due_day, reference_month.year, reference_month.month
            )
            clamped_due_date = date(reference_month.year, reference_month.month, clamped_due)
            if clamped_due_date < today:
                return _error(
                    "Não é possível desmarcar um aluguel cujo vencimento já passou.",
                    is_paid=True,
                )

            payment.delete(deleted_by=user)
            logger.info("Soft-deleted rent payment for lease %s (%s)", lease_id, reference_month)
            return {
                "status": "ok",
                "is_paid": False,
                "message": "Aluguel desmarcado como pago.",
            }

    @staticmethod
    def _build_item(
        lease: Lease,
        reference_month: date,
        clamped_due: int,
        clamped_due_date: date,
        payment: RentPayment | None,
        today: date,
        is_current_month: bool,
        month_finalized: bool,
    ) -> dict[str, Any]:
        """Build a single day item dict for the schedule."""
        effective_value = RentScheduleService.effective_rental_value(lease, reference_month)
        is_paid = payment is not None
        day_passed = clamped_due_date < today
        is_current_or_past = reference_month <= today.replace(day=1)
        is_overdue = (not is_paid) and day_passed and is_current_or_past
        can_toggle = (not month_finalized) and not (is_paid and day_passed)

        late_fee = ZERO
        late_days = 0
        if is_overdue and is_current_month:
            fee = FeeCalculatorService.calculate_late_fee(effective_value, clamped_due, today)
            late_fee = _as_decimal(fee["late_fee"])
            late_days = int(fee["late_days"])

        return {
            "lease_id": lease.pk,
            "tenant_name": lease.responsible_tenant.name,
            "apartment_number": lease.apartment.number,
            "building_number": str(lease.apartment.building.street_number),
            "rental_value": str(effective_value),
            "is_paid": is_paid,
            "payment_date": payment.payment_date.isoformat() if payment else None,
            "is_overdue": is_overdue,
            "day_passed": day_passed,
            "can_toggle": can_toggle,
            "late_fee": str(late_fee),
            "late_days": late_days,
        }

    @staticmethod
    def _active_payments_by_lease(reference_month: date) -> dict[int, RentPayment]:
        """Active RentPayments for the month keyed by lease id."""
        return {
            payment.lease.pk: payment
            for payment in RentPayment.objects.filter(
                reference_month=reference_month
            ).select_related("lease")
        }

    @staticmethod
    def _is_month_finalized(reference_month: date) -> bool:
        """Whether a finalized MonthSnapshot exists for the month."""
        return MonthSnapshot.objects.filter(
            reference_month=reference_month, is_finalized=True
        ).exists()

    @staticmethod
    def _vacant_kitnets(building_id: int | None) -> tuple[int, Decimal]:
        """Count and summed rental value of vacant apartments."""
        apartments = Apartment.objects.filter(is_rented=False)
        if building_id is not None:
            apartments = apartments.filter(building_id=building_id)
        agg = apartments.aggregate(count=Count("id"), total=Sum("rental_value"))
        return agg["count"] or 0, agg["total"] or ZERO


def _as_decimal(value: int | Decimal | str) -> Decimal:
    """Coerce a fee-calculator value to Decimal."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _error(message: str, is_paid: bool) -> dict[str, Any]:
    """Build an error result that reports the unchanged paid state."""
    return {"status": "error", "is_paid": is_paid, "message": message}
