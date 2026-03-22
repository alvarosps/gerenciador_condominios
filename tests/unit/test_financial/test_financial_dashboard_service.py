"""Tests for FinancialDashboardService."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import (
    CreditCard,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    ExpenseType,
    FinancialSettings,
    Person,
)
from core.services.financial_dashboard_service import FinancialDashboardService


@pytest.fixture
def person_rodrigo() -> Person:
    return Person.objects.create(name="Rodrigo", relationship="Filho")


@pytest.fixture
def person_tiago() -> Person:
    return Person.objects.create(name="Tiago", relationship="Filho")


@pytest.fixture
def credit_card(person_rodrigo: Person) -> CreditCard:
    return CreditCard.objects.create(
        person=person_rodrigo,
        nickname="Nubank Rodrigo",
        closing_day=15,
        due_day=22,
        is_active=True,
    )


@pytest.fixture
def category_alimentacao() -> ExpenseCategory:
    return ExpenseCategory.objects.create(name="Alimentação", color="#EF4444")


@pytest.fixture
def category_transporte() -> ExpenseCategory:
    return ExpenseCategory.objects.create(name="Transporte", color="#3B82F6")


def _create_expense_with_installments(
    *,
    description: str,
    expense_type: str,
    total_amount: Decimal,
    person: Person | None = None,
    credit_card: CreditCard | None = None,
    category: ExpenseCategory | None = None,
    is_debt_installment: bool = False,
    installments: list[dict],
) -> Expense:
    expense = Expense.objects.create(
        description=description,
        expense_type=expense_type,
        total_amount=total_amount,
        expense_date=date(2026, 1, 1),
        person=person,
        credit_card=credit_card,
        category=category,
        is_installment=True,
        total_installments=len(installments),
        is_debt_installment=is_debt_installment,
    )
    for inst in installments:
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=inst["number"],
            total_installments=len(installments),
            amount=inst["amount"],
            due_date=inst["due_date"],
            is_paid=inst.get("is_paid", False),
        )
    return expense


class TestFinancialDashboardOverview:
    @freeze_time("2026-03-15")
    def test_overview_basic(self) -> None:
        result = FinancialDashboardService.get_overview()

        assert "current_month_balance" in result
        assert "current_month_income" in result
        assert "current_month_expenses" in result
        assert "total_debt" in result
        assert "total_monthly_obligations" in result
        assert "total_monthly_income" in result
        assert "months_until_break_even" in result

    @freeze_time("2026-03-15")
    def test_overview_with_debts(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {
                    "number": 1,
                    "amount": Decimal("200.00"),
                    "due_date": date(2026, 2, 22),
                    "is_paid": True,
                },
                {"number": 2, "amount": Decimal("200.00"), "due_date": date(2026, 3, 22)},
                {"number": 3, "amount": Decimal("200.00"), "due_date": date(2026, 4, 22)},
            ],
        )

        result = FinancialDashboardService.get_overview()

        # total_debt = sum of future unpaid installments (march + april = 400)
        assert result["total_debt"] == Decimal("400.00")

    @freeze_time("2026-03-15")
    def test_months_until_break_even(self) -> None:
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("-1000.00"),
                "initial_balance_date": date(2026, 1, 1),
            },
        )

        result = FinancialDashboardService.get_overview()

        # Should calculate how many months until cumulative balance becomes positive
        # With negative balance and no income, could be None
        assert result["months_until_break_even"] is None or isinstance(
            result["months_until_break_even"], int
        )

    @freeze_time("2026-03-15")
    def test_months_until_break_even_already_positive(self) -> None:
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("5000.00"),
                "initial_balance_date": date(2026, 1, 1),
            },
        )

        result = FinancialDashboardService.get_overview()
        assert result["months_until_break_even"] == 0

    @freeze_time("2026-03-15")
    def test_months_until_break_even_never(self) -> None:
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("-999999.00"),
                "initial_balance_date": date(2026, 1, 1),
            },
        )

        result = FinancialDashboardService.get_overview()
        # If never reaches positive in 60 months, returns None
        assert result["months_until_break_even"] is None


class TestFinancialDashboardDebtByPerson:
    @freeze_time("2026-03-15")
    def test_debt_per_person(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        # Card purchase
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("200.00"), "due_date": date(2026, 3, 22)},
                {"number": 2, "amount": Decimal("200.00"), "due_date": date(2026, 4, 22)},
                {"number": 3, "amount": Decimal("200.00"), "due_date": date(2026, 5, 22)},
            ],
        )
        # Loan
        _create_expense_with_installments(
            description="Empréstimo",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("1000.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("500.00"), "due_date": date(2026, 3, 22)},
                {"number": 2, "amount": Decimal("500.00"), "due_date": date(2026, 4, 22)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_person()
        rodrigo_data = next(p for p in result if p["person_id"] == person_rodrigo.id)

        assert rodrigo_data["card_debt"] == Decimal("600.00")
        assert rodrigo_data["loan_debt"] == Decimal("1000.00")
        assert rodrigo_data["total_debt"] == Decimal("1600.00")
        assert rodrigo_data["monthly_card"] == Decimal("200.00")
        assert rodrigo_data["monthly_loan"] == Decimal("500.00")

    @freeze_time("2026-03-15")
    def test_person_no_debt(self, person_rodrigo: Person) -> None:
        result = FinancialDashboardService.get_debt_by_person()
        rodrigo_data = [p for p in result if p["person_id"] == person_rodrigo.id]

        # Person with no expenses should either not appear or have zeros
        if rodrigo_data:
            assert rodrigo_data[0]["total_debt"] == Decimal("0.00")

    @freeze_time("2026-03-15")
    def test_multiple_persons(
        self,
        person_rodrigo: Person,
        person_tiago: Person,
        credit_card: CreditCard,
    ) -> None:
        _create_expense_with_installments(
            description="Compra Rodrigo",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("300.00"), "due_date": date(2026, 4, 22)},
            ],
        )
        tiago_card = CreditCard.objects.create(
            person=person_tiago, nickname="Nubank Tiago", closing_day=10, due_day=17, is_active=True
        )
        _create_expense_with_installments(
            description="Compra Tiago",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("500.00"),
            person=person_tiago,
            credit_card=tiago_card,
            installments=[
                {"number": 1, "amount": Decimal("500.00"), "due_date": date(2026, 4, 17)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_person()
        person_ids = {p["person_id"] for p in result}

        assert person_rodrigo.id in person_ids
        assert person_tiago.id in person_ids


class TestFinancialDashboardDebtByType:
    @freeze_time("2026-03-15")
    def test_debt_by_type(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("300.00"), "due_date": date(2026, 4, 22)},
            ],
        )
        _create_expense_with_installments(
            description="Empréstimo bancário",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("1000.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("1000.00"), "due_date": date(2026, 5, 15)},
            ],
        )
        _create_expense_with_installments(
            description="Dívida água",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            is_debt_installment=True,
            installments=[
                {"number": 1, "amount": Decimal("200.00"), "due_date": date(2026, 6, 10)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()

        assert result["card_purchases"] == Decimal("300.00")
        assert result["bank_loans"] == Decimal("1000.00")
        assert result["water_debt"] == Decimal("200.00")
        assert "total" in result

    @freeze_time("2026-03-15")
    def test_only_future_unpaid(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                # Past and paid — should be excluded
                {
                    "number": 1,
                    "amount": Decimal("200.00"),
                    "due_date": date(2026, 1, 22),
                    "is_paid": True,
                },
                # Past and unpaid — should still count as debt
                {"number": 2, "amount": Decimal("200.00"), "due_date": date(2026, 2, 22)},
                # Future — should count
                {"number": 3, "amount": Decimal("200.00"), "due_date": date(2026, 4, 22)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()

        # Unpaid installments: #2 (past but unpaid) + #3 (future) = 400
        assert result["card_purchases"] == Decimal("400.00")


class TestFinancialDashboardUpcoming:
    @freeze_time("2026-03-15")
    def test_upcoming_30_days(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 3, 22)},
                {"number": 2, "amount": Decimal("100.00"), "due_date": date(2026, 4, 10)},
                {"number": 3, "amount": Decimal("100.00"), "due_date": date(2026, 5, 22)},
            ],
        )

        result = FinancialDashboardService.get_upcoming_installments(days=30)

        # Within 30 days from 2026-03-15: 2026-03-22 and 2026-04-10
        assert len(result) == 2
        assert result[0]["due_date"] == date(2026, 3, 22)
        assert result[1]["due_date"] == date(2026, 4, 10)

    @freeze_time("2026-03-15")
    def test_upcoming_custom_days(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 3, 20)},
                {"number": 2, "amount": Decimal("100.00"), "due_date": date(2026, 3, 25)},
            ],
        )

        result = FinancialDashboardService.get_upcoming_installments(days=7)

        # Within 7 days from 2026-03-15: only 2026-03-20
        assert len(result) == 1
        assert result[0]["due_date"] == date(2026, 3, 20)

    @freeze_time("2026-03-15")
    def test_upcoming_excludes_paid(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {
                    "number": 1,
                    "amount": Decimal("100.00"),
                    "due_date": date(2026, 3, 20),
                    "is_paid": True,
                },
                {"number": 2, "amount": Decimal("100.00"), "due_date": date(2026, 3, 25)},
            ],
        )

        result = FinancialDashboardService.get_upcoming_installments(days=30)

        assert len(result) == 1
        assert result[0]["installment_number"] == 2

    @freeze_time("2026-03-15")
    def test_upcoming_ordering(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra B",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 4, 1)},
            ],
        )
        _create_expense_with_installments(
            description="Empréstimo A",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 3, 20)},
            ],
        )

        result = FinancialDashboardService.get_upcoming_installments(days=30)

        # Should be ordered by due_date ASC
        assert result[0]["due_date"] <= result[1]["due_date"]


class TestFinancialDashboardOverdue:
    @freeze_time("2026-03-15")
    def test_overdue_installments(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 2, 22)},
                {"number": 2, "amount": Decimal("100.00"), "due_date": date(2026, 3, 22)},
                {"number": 3, "amount": Decimal("100.00"), "due_date": date(2026, 4, 22)},
            ],
        )

        result = FinancialDashboardService.get_overdue_installments()

        # Only installment #1 is overdue (due 2026-02-22 < today 2026-03-15)
        assert len(result) == 1
        assert result[0]["installment_number"] == 1
        assert "days_overdue" in result[0]

    @freeze_time("2026-03-15")
    def test_overdue_excludes_paid(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {
                    "number": 1,
                    "amount": Decimal("100.00"),
                    "due_date": date(2026, 2, 22),
                    "is_paid": True,
                },
                {"number": 2, "amount": Decimal("100.00"), "due_date": date(2026, 3, 1)},
            ],
        )

        result = FinancialDashboardService.get_overdue_installments()

        # #1 is paid so excluded, #2 is overdue and unpaid
        assert len(result) == 1
        assert result[0]["installment_number"] == 2

    @freeze_time("2026-03-15")
    def test_days_overdue_calculation(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 3, 10)},
            ],
        )

        result = FinancialDashboardService.get_overdue_installments()

        assert len(result) == 1
        # 2026-03-15 - 2026-03-10 = 5 days
        assert result[0]["days_overdue"] == 5


class TestFinancialDashboardCategoryBreakdown:
    @freeze_time("2026-03-15")
    def test_breakdown_by_category(
        self,
        category_alimentacao: ExpenseCategory,
        category_transporte: ExpenseCategory,
    ) -> None:
        Expense.objects.create(
            description="Supermercado",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 3, 5),
            category=category_alimentacao,
        )
        Expense.objects.create(
            description="Uber",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 3, 10),
            category=category_transporte,
        )

        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)

        assert len(result) == 2
        # Ordered by total DESC
        assert result[0]["category_name"] == "Alimentação"
        assert result[0]["total"] == Decimal("300.00")
        assert result[1]["category_name"] == "Transporte"
        assert result[1]["total"] == Decimal("100.00")

    @freeze_time("2026-03-15")
    def test_null_category(self) -> None:
        Expense.objects.create(
            description="Gasto sem categoria",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 3, 8),
            category=None,
        )

        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)

        assert len(result) == 1
        assert result[0]["category_name"] == "Sem Categoria"
        assert result[0]["category_id"] is None

    @freeze_time("2026-03-15")
    def test_percentage_calculation(
        self,
        category_alimentacao: ExpenseCategory,
        category_transporte: ExpenseCategory,
    ) -> None:
        Expense.objects.create(
            description="Supermercado",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("750.00"),
            expense_date=date(2026, 3, 5),
            category=category_alimentacao,
        )
        Expense.objects.create(
            description="Uber",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("250.00"),
            expense_date=date(2026, 3, 10),
            category=category_transporte,
        )

        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)

        total_pct = sum(item["percentage"] for item in result)
        assert abs(total_pct - 100.0) < 0.1
        assert result[0]["percentage"] == pytest.approx(75.0, abs=0.1)
        assert result[1]["percentage"] == pytest.approx(25.0, abs=0.1)

    @freeze_time("2026-03-15")
    def test_empty_month(self) -> None:
        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)
        assert result == []
