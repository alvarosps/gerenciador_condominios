from decimal import Decimal

import pytest
from model_bakery import baker

from core.models import ExpenseInstallment
from core.services.expense_service import ExpenseService

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestExpenseServiceRebuild:
    def test_rebuild_replaces_all_installments(self, admin_user):
        expense = baker.make(
            "core.Expense",
            description="Test expense",
            total_amount=Decimal("300.00"),
            is_installment=True,
            total_installments=3,
            created_by=admin_user,
            updated_by=admin_user,
        )
        for i in range(1, 4):
            baker.make(
                "core.ExpenseInstallment",
                expense=expense,
                installment_number=i,
                total_installments=3,
                amount=Decimal("100.00"),
                due_date="2026-05-01",
                created_by=admin_user,
                updated_by=admin_user,
            )

        new_installments = [
            {
                "installment_number": 1,
                "total_installments": 2,
                "amount": Decimal("150.00"),
                "due_date": "2026-06-01",
            },
            {
                "installment_number": 2,
                "total_installments": 2,
                "amount": Decimal("150.00"),
                "due_date": "2026-07-01",
            },
        ]

        result = ExpenseService.rebuild_installments(
            expense=expense,
            field_updates={"description": "Updated", "total_installments": 2},
            installments_data=new_installments,
            user=admin_user,
        )

        assert result.description == "Updated"
        assert result.total_installments == 2
        assert ExpenseInstallment.objects.filter(expense=expense).count() == 2

    def test_rebuild_updates_allowed_fields(self, admin_user):
        expense = baker.make(
            "core.Expense",
            description="Original",
            total_amount=Decimal("100.00"),
            is_offset=False,
            created_by=admin_user,
            updated_by=admin_user,
        )

        ExpenseService.rebuild_installments(
            expense=expense,
            field_updates={"description": "New", "is_offset": True},
            installments_data=[],
            user=admin_user,
        )

        expense.refresh_from_db()
        assert expense.description == "New"
        assert expense.is_offset is True

    def test_rebuild_ignores_disallowed_fields(self, admin_user):
        expense = baker.make(
            "core.Expense",
            expense_type="one_time_expense",
            created_by=admin_user,
            updated_by=admin_user,
        )

        ExpenseService.rebuild_installments(
            expense=expense,
            field_updates={"expense_type": "card_purchase"},
            installments_data=[],
            user=admin_user,
        )

        expense.refresh_from_db()
        assert expense.expense_type == "one_time_expense"
