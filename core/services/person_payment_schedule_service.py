"""Service for managing person payment schedules.

Provides methods to calculate a person's total due for a month,
configure payment schedules, and determine suggested payment amounts.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.cache import invalidate_legacy_financial_caches
from core.models import (
    Expense,
    ExpenseInstallment,
    ExpenseMonthSkip,
    ExpenseType,
    Person,
    PersonPayment,
    PersonPaymentSchedule,
)
from core.services.date_calculator import DateCalculatorService

MAX_DAY_OF_MONTH = 31


def _sum_person_expenses(
    person_id: int, month_start: date, next_month_start: date, *, is_offset: bool
) -> Decimal:
    """Sum all expense amounts for a person in a given month (installments + recurring + one-time)."""
    zero = Decimal("0.00")

    skipped_ids = set(
        ExpenseMonthSkip.objects.filter(reference_month=month_start).values_list(
            "expense_id", flat=True
        )
    )

    # Installments with due_date in the month
    installments_total: Decimal = (
        ExpenseInstallment.objects.filter(
            expense__person_id=person_id,
            expense__is_offset=is_offset,
            due_date__gte=month_start,
            due_date__lt=next_month_start,
        )
        .exclude(expense_id__in=skipped_ids)
        .aggregate(total=Coalesce(Sum("amount"), zero))["total"]
    )

    # Fixed recurring expenses (respect end_date)
    fixed_total: Decimal = (
        Expense.objects.filter(
            person_id=person_id,
            expense_type=ExpenseType.FIXED_EXPENSE,
            is_recurring=True,
            is_offset=is_offset,
            expected_monthly_amount__isnull=False,
        )
        .exclude(end_date__lt=month_start)
        .exclude(pk__in=skipped_ids)
        .aggregate(total=Coalesce(Sum("expected_monthly_amount"), zero))["total"]
    )

    # One-time expenses in the month
    one_time_total: Decimal = (
        Expense.objects.filter(
            person_id=person_id,
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            is_offset=is_offset,
            expense_date__gte=month_start,
            expense_date__lt=next_month_start,
        )
        .exclude(pk__in=skipped_ids)
        .aggregate(total=Coalesce(Sum("total_amount"), zero))["total"]
    )

    return installments_total + fixed_total + one_time_total


class PersonPaymentScheduleService:
    """Service for person payment schedule management and calculations."""

    @staticmethod
    def get_person_month_total(person_id: int, year: int, month: int) -> dict[str, Decimal]:
        """Calculate total due, scheduled, paid, and pending amounts for a person in a month."""
        month_start = date(year, month, 1)
        next_month_start = DateCalculatorService.next_month_start(year, month)

        total_due = _sum_person_expenses(person_id, month_start, next_month_start, is_offset=False)
        total_offsets = _sum_person_expenses(
            person_id, month_start, next_month_start, is_offset=True
        )
        net_total = total_due - total_offsets

        total_scheduled = PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=month_start,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        total_paid = PersonPayment.objects.filter(
            person_id=person_id,
            reference_month=month_start,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        pending = net_total - total_paid

        return {
            "total_due": total_due,
            "total_offsets": total_offsets,
            "net_total": net_total,
            "total_scheduled": total_scheduled,
            "total_paid": total_paid,
            "pending": pending,
        }

    @staticmethod
    @transaction.atomic
    def bulk_configure(
        person_id: int,
        reference_month: date,
        entries: list[dict[str, Any]],
    ) -> list[PersonPaymentSchedule]:
        """Replace all payment schedules for a person/month with the given entries."""
        for entry in entries:
            due_day = entry.get("due_day")
            if due_day is not None and not (1 <= due_day <= MAX_DAY_OF_MONTH):
                msg = f"due_day must be between 1 and {MAX_DAY_OF_MONTH}, got {due_day}"
                raise ValueError(msg)

        person = Person.objects.get(pk=person_id)

        # Soft-delete existing schedules for this person/month. The bulk .update() must set
        # deleted_at (a row with is_deleted=True but deleted_at=None is an inconsistent
        # soft-delete) and, since it bypasses post_save, invalidate caches explicitly.
        PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
        ).update(is_deleted=True, deleted_at=timezone.now())
        invalidate_legacy_financial_caches()

        created = []
        for entry in entries:
            schedule = PersonPaymentSchedule.objects.create(
                person=person,
                reference_month=reference_month,
                due_day=entry["due_day"],
                amount=entry["amount"],
            )
            created.append(schedule)

        return created

    @staticmethod
    def get_suggested_payment(
        person_id: int,
        reference_month: date,
        due_day: int,
    ) -> dict[str, Decimal]:
        """Calculate suggested payment amount for a person up to a given day in the month."""
        expected_until_date = PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
            due_day__lte=due_day,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        already_paid = PersonPayment.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        suggested_amount = max(Decimal("0.00"), expected_until_date - already_paid)

        return {
            "expected_until_date": expected_until_date,
            "already_paid": already_paid,
            "suggested_amount": suggested_amount,
        }

    @staticmethod
    def has_schedule(person_id: int, reference_month: date) -> bool:
        """Check if any payment schedules exist for a person/month."""
        return PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
        ).exists()

    @staticmethod
    def get_schedules_for_month(
        person_id: int, reference_month: date
    ) -> list[PersonPaymentSchedule]:
        """Return all schedules for a person/month ordered by due_day."""
        return list(
            PersonPaymentSchedule.objects.filter(
                person_id=person_id,
                reference_month=reference_month,
            ).order_by("due_day")
        )

    @staticmethod
    def is_schedule_paid(person_id: int, reference_month: date, due_day: int) -> bool:
        """Check if total paid >= total expected for schedules up to and including due_day."""
        expected: Decimal = PersonPaymentSchedule.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
            due_day__lte=due_day,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        if expected == Decimal("0.00"):
            return False

        paid: Decimal = PersonPayment.objects.filter(
            person_id=person_id,
            reference_month=reference_month,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        return paid >= expected
