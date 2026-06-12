"""Service for expense business logic."""

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from core.models import Expense, ExpenseInstallment

_CENTS = Decimal("0.01")
_NOT_INSTALLMENT_ERROR = "Despesa não é parcelada ou não tem total de parcelas definido."


def _clamp_day(reference: date, day: int) -> int:
    """Clamp a day-of-month to the last valid day of the reference month (no ValueError)."""
    return min(day, calendar.monthrange(reference.year, reference.month)[1])


REBUILD_ALLOWED_FIELDS = frozenset(
    {
        "description",
        "total_amount",
        "category_id",
        "notes",
        "is_installment",
        "total_installments",
        "is_offset",
    }
)


class ExpenseService:
    """Stateless service for expense operations."""

    @staticmethod
    @transaction.atomic
    def rebuild_installments(
        *,
        expense: Expense,
        field_updates: dict[str, Any],
        installments_data: list[dict[str, Any]],
        user: User,
    ) -> Expense:
        """Replace expense fields and all installments atomically."""
        for field, value in field_updates.items():
            if field not in REBUILD_ALLOWED_FIELDS:
                continue
            if field == "category_id":
                expense.category_id = value
            else:
                setattr(expense, field, value)
        expense.save()

        ExpenseInstallment.all_objects.filter(expense=expense).delete()

        to_create = [
            ExpenseInstallment(
                expense=expense,
                installment_number=inst["installment_number"],
                total_installments=inst["total_installments"],
                amount=inst["amount"],
                due_date=inst["due_date"],
                is_paid=inst.get("is_paid", False),
                paid_date=inst.get("paid_date"),
                created_by=user,
                updated_by=user,
            )
            for inst in installments_data
        ]
        if to_create:
            ExpenseInstallment.objects.bulk_create(to_create)

        return expense

    @staticmethod
    @transaction.atomic
    def generate_installments(*, expense: Expense, start_date: date, user: User) -> Expense:
        """Generate the expense's installments, with the residual on the last parcel.

        Splitting ``total_amount`` by ``n`` and rounding each parcel can drift from the
        total (e.g. 100.00 / 3); the last parcel absorbs the residual so the parcels
        always sum to ``total_amount``. Credit-card installments fall on the card's
        ``due_day``, clamped to the month's last day to avoid a ValueError on short months.
        """
        n = expense.total_installments
        if not n:
            raise serializers.ValidationError(_NOT_INSTALLMENT_ERROR)
        base = (expense.total_amount / n).quantize(_CENTS, rounding=ROUND_HALF_UP)
        last = expense.total_amount - base * (n - 1)

        credit_card = expense.credit_card
        due_day = credit_card.due_day if credit_card is not None else None

        installments = []
        for i in range(1, n + 1):
            month_date = start_date + relativedelta(months=i - 1)
            if due_day is not None:
                due_date = month_date.replace(day=_clamp_day(month_date, due_day))
            else:
                due_date = month_date
            installments.append(
                ExpenseInstallment(
                    expense=expense,
                    installment_number=i,
                    total_installments=n,
                    amount=last if i == n else base,
                    due_date=due_date,
                    created_by=user,
                    updated_by=user,
                )
            )
        ExpenseInstallment.objects.bulk_create(installments)
        return expense
