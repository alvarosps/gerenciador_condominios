"""Service for expense business logic."""

from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from core.models import Expense, ExpenseInstallment

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
