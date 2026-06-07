"""
Rent schedule service for Condomínios Manager.

Single source of truth for "rent due this month" logic:
- Clamping the due day to the actual number of days in the month.
- Effective rental value honoring pending rent increases.
- Collectible leases (excluding owner/salary-offset/prepaid). A non-deleted lease is
  active by definition: Brazilian residential leases auto-renew (Lei 8.245/91 art. 46-47)
  and tenant move-out is modeled by soft-delete + the ``unique_active_lease_per_apartment``
  constraint, NOT by the original term elapsing — so there is no upper date bound.
- Displayable leases (collectible plus the surfaced non-collectible owner/salary-offset
  reasons) for the rent calendar classification layer.
- Month schedule (day-by-day items) and month stats for the rent calendar.
- Toggling a monthly rent payment (create / soft-delete) with full revalidation.

Money uses Decimal; serialized values are returned as str. Date arithmetic is
pure (all relevant fields are DateField). User-facing messages are in Portuguese;
logs are in English. Late fee is reused from FeeCalculatorService (no duplication).
"""

import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Any, Literal, NamedTuple

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, QuerySet, Sum
from django.utils import timezone

from core.models import Apartment, FinancialSettings, Lease, MonthSnapshot, RentPayment
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

NonCollectibleReason = Literal["owner_repass", "salary_offset"]


class _MonthContext(NamedTuple):
    """Month-level scalars shared by every day-item of a schedule (computed once)."""

    reference_month: date
    today: date
    is_current_month: bool
    month_finalized: bool


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
    def rent_tracking_start_month() -> date | None:
        """First day of the month from which rent is tracked, or None if unbounded.

        Driven by the FinancialSettings singleton. None means no boundary configured:
        every month is tracked (legacy behavior).
        """
        financial_settings = FinancialSettings.objects.first()
        if financial_settings is None or financial_settings.rent_tracking_start_date is None:
            return None
        return financial_settings.rent_tracking_start_date.replace(day=1)

    @staticmethod
    def is_month_tracked(year: int, month: int) -> bool:
        """Whether the system tracks rent for (year, month). Months before the configured
        tracking-start are considered already settled and are never collectible."""
        start = RentScheduleService.rent_tracking_start_month()
        return start is None or date(year, month, 1) >= start

    @staticmethod
    def is_prepaid_for_month(lease: Lease, year: int, month: int) -> bool:
        """Whether the month's rent installment is already covered by prepayment.

        Pay-to-live: the installment due on the clamped due day of (year, month) covers
        ``[due_date .. next month's due date]``. It is already paid only if
        ``prepaid_until`` is strictly AFTER that due date. The installment falling exactly
        on ``prepaid_until`` is the NEXT one due and is NOT prepaid. Compares against the
        clamped due date, never the month start (which causes an off-by-one).
        """
        if lease.prepaid_until is None:
            return False
        clamped_due = RentScheduleService.clamp_due_day(
            lease.responsible_tenant.due_day, year, month
        )
        return lease.prepaid_until > date(year, month, clamped_due)

    @staticmethod
    def is_collectible_for_month(lease: Lease, year: int, month: int) -> bool:
        """Whether this lease's rent is collectible in (year, month): it had started by the
        last day of the month and is not prepaid for that month. Owner/salary-offset exclusions
        are structural and handled by collectible_leases, not here."""
        _, days_in_month = monthrange(year, month)
        started = lease.start_date <= date(year, month, days_in_month)
        return (
            started
            and RentScheduleService.is_month_tracked(year, month)
            and not RentScheduleService.is_prepaid_for_month(lease, year, month)
        )

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
        """Collectible leases for the month (single source of truth).

        A non-deleted lease is active by definition: Brazilian residential leases auto-renew
        (Lei 8.245/91 art. 46-47) and tenant move-out is modeled by soft-delete + the
        ``unique_active_lease_per_apartment`` constraint, NOT by the original term elapsing.
        There is therefore NO upper date bound — only ``start_date <= last day of month``,
        minus the structural and prepaid exclusions. Collectibility does NOT depend on the
        ``apartment.is_rented`` boolean:
        - not soft-deleted (default ``Lease.objects`` manager),
        - ``apartment.owner`` is null (owner repass is not condominium revenue),
        - ``is_salary_offset=False``,
        - the month is not prepaid: ``prepaid_until`` does not extend PAST this month's
          clamped due date. Pay-to-live: the installment due on M/clamped_due covers
          [M/D .. (M+1)/D]; it is already paid only if ``prepaid_until`` is strictly after
          M/D. The installment due exactly on ``prepaid_until`` is the NEXT one due and
          stays collectible (e.g. prepaid_until=2026-09-29, due_day=29 → Aug excluded,
          Sep collectible).

        ORM-expressible filters (owner, salary offset, building,
        ``start_date <= last day of month``) stay in the queryset; the prepaid boundary
        (which needs the clamped due date) is applied in Python over the reduced queryset.
        """
        year, month = reference_month.year, reference_month.month
        if not RentScheduleService.is_month_tracked(year, month):
            return Lease.objects.none()
        _, days_in_month = monthrange(year, month)
        month_end = date(year, month, days_in_month)

        queryset = (
            Lease.objects.filter(start_date__lte=month_end)
            .exclude(apartment__owner__isnull=False)
            .exclude(is_salary_offset=True)
            .select_related("apartment", "apartment__building", "responsible_tenant")
        )

        if building_id is not None:
            queryset = queryset.filter(apartment__building_id=building_id)

        collectible_ids = []
        for lease in queryset:
            # Pay-to-live prepaid boundary (single source: is_prepaid_for_month). The month
            # whose due date equals prepaid_until is the next installment due and stays
            # collectible — comparing against month start would be an off-by-one.
            if RentScheduleService.is_prepaid_for_month(lease, year, month):
                continue
            collectible_ids.append(lease.pk)
        return queryset.filter(id__in=collectible_ids)

    @staticmethod
    def displayable_leases(
        reference_month: date, building_id: int | None = None
    ) -> list[tuple[Lease, bool, str | None]]:
        """Leases to display in the rent calendar, classified for collectibility.

        Returns every non-deleted lease that had started by the last day of the month
        (+ optional building filter), as ``(lease, is_collectible, non_collectible_reason)``:
        - collectible leases → ``(lease, True, None)``;
        - owner-repass leases → ``(lease, False, "owner_repass")`` (surfaced, not toggleable);
        - salary-offset leases → ``(lease, False, "salary_offset")`` (surfaced, not toggleable).

        Prepaid leases — and leases in a month before the rent-tracking boundary
        (``FinancialSettings.rent_tracking_start_date``) — are intentionally NOT surfaced:
        they stay hidden, exactly as the collectible set already hides them. That is why
        ``NonCollectibleReason`` has only the owner-repass and salary-offset literals.
        """
        year, month = reference_month.year, reference_month.month
        if not RentScheduleService.is_month_tracked(year, month):
            return []
        _, days_in_month = monthrange(year, month)
        month_end = date(year, month, days_in_month)

        collectible_ids = {
            lease.pk
            for lease in RentScheduleService.collectible_leases(reference_month, building_id)
        }

        queryset = Lease.objects.filter(start_date__lte=month_end).select_related(
            "apartment", "apartment__building", "responsible_tenant"
        )
        if building_id is not None:
            queryset = queryset.filter(apartment__building_id=building_id)

        result: list[tuple[Lease, bool, str | None]] = []
        for lease in queryset:
            if lease.pk in collectible_ids:
                result.append((lease, True, None))
            elif lease.apartment.owner_id is not None:
                result.append((lease, False, "owner_repass"))
            elif lease.is_salary_offset:
                result.append((lease, False, "salary_offset"))
            # else: excluded because prepaid or because the month precedes the rent-tracking
            # boundary → stays hidden (not surfaced as a non-collectible reason in either case).
        return result

    @staticmethod
    def get_month_schedule(year: int, month: int, building_id: int | None = None) -> dict[str, Any]:
        """Full month structure for the rent calendar.

        Returns ``year``, ``month``, ``today`` (iso), ``next_due_date`` (iso|None),
        ``days`` (each with ``items``) and ``stats``. The month label is derived on
        the frontend (not returned here).
        """
        reference_month = date(year, month, 1)
        today = timezone.now().date()
        context = _MonthContext(
            reference_month=reference_month,
            today=today,
            is_current_month=(year, month) == (today.year, today.month),
            month_finalized=RentScheduleService._is_month_finalized(reference_month),
        )

        _, days_in_month = monthrange(year, month)
        leases = RentScheduleService.displayable_leases(reference_month, building_id)
        payments = RentScheduleService._active_payments_by_lease(reference_month)

        items_by_day: dict[int, list[dict[str, Any]]] = {}
        next_due_date: date | None = None

        for lease, is_collectible, non_collectible_reason in leases:
            clamped_due = RentScheduleService.clamp_due_day(
                lease.responsible_tenant.due_day, year, month
            )
            clamped_due_date = date(year, month, clamped_due)
            payment = payments.get(lease.pk)
            item = RentScheduleService._build_item(
                lease=lease,
                clamped_due=clamped_due,
                clamped_due_date=clamped_due_date,
                payment=payment,
                context=context,
                is_collectible=is_collectible,
                non_collectible_reason=non_collectible_reason,
            )
            items_by_day.setdefault(clamped_due, []).append(item)

            if (
                is_collectible
                and not item["is_paid"]
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
    def received_collectible_total(reference_month: date, building_id: int | None = None) -> Decimal:
        """Rent received for the month, restricted to COLLECTIBLE leases (design §4.5).

        Mirrors ``received_total`` but pre-filters by ``collectible_leases`` so owner-repass
        (Tiago/Alvaro) and salary-offset payments never count toward condominium revenue.
        Used by the condominium cash/net (Phase 4). Additive — ``received_total`` is
        unchanged. In the normal case it equals ``received_total`` (only collectible leases
        ever get a RentPayment); it diverges only if a non-collectible lease has a payment.
        """
        collectible = RentScheduleService.collectible_leases(reference_month, building_id)
        payments = RentPayment.objects.filter(
            reference_month=reference_month, lease__in=collectible
        )
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
        clamped_due: int,
        clamped_due_date: date,
        payment: RentPayment | None,
        context: _MonthContext,
        *,
        is_collectible: bool,
        non_collectible_reason: str | None,
    ) -> dict[str, Any]:
        """Build a single day item dict for the schedule."""
        today = context.today
        effective_value = RentScheduleService.effective_rental_value(lease, context.reference_month)
        is_paid = payment is not None
        day_passed = clamped_due_date < today
        is_current_or_past = context.reference_month <= today.replace(day=1)
        is_overdue = (not is_paid) and day_passed and is_current_or_past
        can_toggle = (
            (not context.month_finalized) and not (is_paid and day_passed) and is_collectible
        )

        late_fee = ZERO
        late_days = 0
        if is_overdue and context.is_current_month:
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
            "is_collectible": is_collectible,
            "non_collectible_reason": non_collectible_reason,
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
