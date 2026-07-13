from datetime import date
from decimal import Decimal

import pytest
from model_bakery import baker

from core.models import ExpenseInstallment
from core.services.expense_service import ExpenseService
from tests.factories import make_credit_card, make_expense

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


class TestExpenseServiceGenerateInstallments:
    def test_sum_equals_total_with_residual_on_last(self, admin_user):
        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("100.00"),
            is_installment=True,
            total_installments=3,
        )
        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 1, 10), user=admin_user
        )
        amounts = list(
            ExpenseInstallment.objects.filter(expense=expense)
            .order_by("installment_number")
            .values_list("amount", flat=True)
        )
        assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
        assert sum(amounts) == Decimal("100.00")

    def test_last_installment_never_negative_for_tiny_total(self, admin_user):
        """B15(d) regression: rounding the base UP (ROUND_HALF_UP) on a tiny total split
        across many installments could push the last installment negative
        (0.05 / 9 -> base=0.01, last=0.05-0.01*8=-0.03). The base must round DOWN so the
        last installment absorbs the (non-negative) residual instead — mirrors
        finances/services/installment_plan_service.py::_split_amount.
        """
        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("0.05"),
            is_installment=True,
            total_installments=9,
        )
        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 1, 10), user=admin_user
        )
        amounts = list(
            ExpenseInstallment.objects.filter(expense=expense)
            .order_by("installment_number")
            .values_list("amount", flat=True)
        )
        assert amounts == [Decimal("0.00")] * 8 + [Decimal("0.05")]
        assert all(amount >= Decimal("0.00") for amount in amounts)
        assert sum(amounts) == Decimal("0.05")

    def test_clamps_due_day_31_in_february(self, admin_user):
        card = make_credit_card(user=admin_user, due_day=31)
        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("300.00"),
            is_installment=True,
            total_installments=3,
            credit_card=card,
            expense_type="card_purchase",
        )
        # Jan -> Feb -> Mar; February (2026, non-leap) has 28 days.
        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 1, 31), user=admin_user
        )
        due_days = list(
            ExpenseInstallment.objects.filter(expense=expense)
            .order_by("installment_number")
            .values_list("due_date", flat=True)
        )
        assert due_days[0] == date(2026, 1, 31)
        assert due_days[1] == date(2026, 2, 28)
        assert due_days[2] == date(2026, 3, 31)

    def test_clamps_due_day_31_in_30day_month(self, admin_user):
        card = make_credit_card(user=admin_user, due_day=31)
        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("200.00"),
            is_installment=True,
            total_installments=2,
            credit_card=card,
            expense_type="card_purchase",
        )
        # April has 30 days.
        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 4, 15), user=admin_user
        )
        installment = ExpenseInstallment.objects.get(expense=expense, installment_number=1)
        assert installment.due_date == date(2026, 4, 30)

    def test_without_credit_card_uses_relativedelta(self, admin_user):
        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("90.00"),
            is_installment=True,
            total_installments=3,
        )
        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 1, 20), user=admin_user
        )
        due_days = list(
            ExpenseInstallment.objects.filter(expense=expense)
            .order_by("installment_number")
            .values_list("due_date", flat=True)
        )
        assert due_days == [date(2026, 1, 20), date(2026, 2, 20), date(2026, 3, 20)]

    def test_bulk_create_invalidates_financial_caches(self, admin_user, mocker):
        """B17(a) regression: bulk_create() bypasses post_save, so
        signals.invalidate_expense_installment_cache_on_save never fires — the service must
        invalidate the same real prefixes explicitly (invalidate_legacy_financial_caches),
        not leave the caches stale until the TTL."""
        from core.cache import CacheManager

        expense = make_expense(
            user=admin_user,
            total_amount=Decimal("90.00"),
            is_installment=True,
            total_installments=3,
        )
        spy = mocker.spy(CacheManager, "invalidate_pattern")

        ExpenseService.generate_installments(
            expense=expense, start_date=date(2026, 1, 20), user=admin_user
        )

        patterns = [call.args[0] for call in spy.call_args_list]
        assert "cash-flow*" in patterns
        assert "financial-dashboard*" in patterns
