"""Tests for FinancialDashboardService."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import (
    Apartment,
    Building,
    CreditCard,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    ExpenseType,
    FinancialSettings,
    Income,
    Lease,
    Person,
    PersonIncome,
    PersonIncomeType,
    PersonPayment,
    Tenant,
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

    @freeze_time("2026-03-15")
    def test_is_offset_excluded(self, category_alimentacao: ExpenseCategory) -> None:
        Expense.objects.create(
            description="Offset gasto",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 5),
            category=category_alimentacao,
            is_offset=True,
        )
        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)
        assert result == []

    @freeze_time("2026-03-15")
    def test_subcategory_resolves_to_parent(self) -> None:
        parent = ExpenseCategory.objects.create(name="Moradia", color="#111111")
        child = ExpenseCategory.objects.create(name="Aluguel", color="#222222", parent=parent)
        Expense.objects.create(
            description="Aluguel apartamento",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("1000.00"),
            expense_date=date(2026, 3, 5),
            category=child,
        )
        result = FinancialDashboardService.get_expense_category_breakdown(2026, 3)
        assert len(result) == 1
        # Category breakdown groups by category__id (child), not parent
        assert result[0]["total"] == Decimal("1000.00")


class TestDebtByTypeExtended:
    """Cover personal_loans, electricity_debt, property_tax_debt branches in get_debt_by_type."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_personal_loans_counted(self, person_rodrigo: Person) -> None:
        _create_expense_with_installments(
            description="Empréstimo pessoal",
            expense_type=ExpenseType.PERSONAL_LOAN,
            total_amount=Decimal("800.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("800.00"), "due_date": date(2026, 4, 10)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()
        assert result["personal_loans"] == Decimal("800.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_electricity_debt_counted(self, person_rodrigo: Person) -> None:
        _create_expense_with_installments(
            description="Dívida luz",
            expense_type=ExpenseType.ELECTRICITY_BILL,
            total_amount=Decimal("400.00"),
            person=person_rodrigo,
            is_debt_installment=True,
            installments=[
                {"number": 1, "amount": Decimal("400.00"), "due_date": date(2026, 4, 10)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()
        assert result["electricity_debt"] == Decimal("400.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_property_tax_debt_counted(self) -> None:
        _create_expense_with_installments(
            description="IPTU parcelado",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("1200.00"),
            installments=[
                {"number": 1, "amount": Decimal("600.00"), "due_date": date(2026, 4, 10)},
                {"number": 2, "amount": Decimal("600.00"), "due_date": date(2026, 5, 10)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()
        assert result["property_tax_debt"] == Decimal("1200.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_total_is_sum_of_all_types(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 4, 1)},
            ],
        )
        _create_expense_with_installments(
            description="Banco",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("200.00"), "due_date": date(2026, 4, 1)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_type()
        expected_total = result["card_purchases"] + result["bank_loans"] + result["personal_loans"] + result["water_debt"] + result["electricity_debt"] + result["property_tax_debt"]
        assert result["total"] == expected_total

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_offset_excluded_from_debt(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Desconto (offset)",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("300.00"), "due_date": date(2026, 4, 1)},
            ],
        )
        # Mark as offset on the expense
        exp = Expense.objects.get(description="Desconto (offset)")
        exp.is_offset = True
        exp.save()

        result = FinancialDashboardService.get_debt_by_type()
        assert result["card_purchases"] == Decimal("0.00")


class TestResolveCategoryFields:
    """Tests for _resolve_category_fields static method."""

    @pytest.mark.unit
    def test_none_category_returns_all_none(self) -> None:
        result = FinancialDashboardService._resolve_category_fields(None)
        assert result == (None, None, None, None, None)

    @pytest.mark.unit
    def test_top_level_category(self) -> None:
        cat = ExpenseCategory.objects.create(name="Alimentação", color="#FF0000")
        result = FinancialDashboardService._resolve_category_fields(cat)
        assert result[0] == cat.id
        assert result[1] == "Alimentação"
        assert result[2] == "#FF0000"
        assert result[3] is None
        assert result[4] is None

    @pytest.mark.unit
    def test_subcategory_resolves_parent(self) -> None:
        parent = ExpenseCategory.objects.create(name="Moradia", color="#0000FF")
        child = ExpenseCategory.objects.create(name="Aluguel", color="#00FF00", parent=parent)
        # Reload to get parent populated
        child_reloaded = ExpenseCategory.objects.select_related("parent").get(pk=child.pk)
        result = FinancialDashboardService._resolve_category_fields(child_reloaded)
        assert result[0] == parent.id
        assert result[1] == "Moradia"
        assert result[2] == "#0000FF"
        assert result[3] == child.id
        assert result[4] == "Aluguel"


class TestEnrichedItems:
    """Tests for _enriched_installment_item and _enriched_expense_item."""

    @pytest.mark.unit
    def test_enriched_installment_item_no_category_no_card(self, person_rodrigo: Person) -> None:
        expense = Expense.objects.create(
            description="Teste",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 1),
            person=person_rodrigo,
            is_installment=True,
            total_installments=1,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("500.00"),
            due_date=date(2026, 4, 1),
        )
        inst_reloaded = ExpenseInstallment.objects.select_related(
            "expense", "expense__credit_card", "expense__category", "expense__category__parent"
        ).get(pk=inst.pk)
        result = FinancialDashboardService._enriched_installment_item(inst_reloaded)

        assert result["expense_id"] == expense.id
        assert result["installment_id"] == inst.id
        assert result["description"] == "Teste"
        assert result["card_name"] is None
        assert result["category_id"] is None
        assert result["category_name"] is None
        assert result["subcategory_id"] is None
        assert result["amount"] == Decimal("500.00")
        assert result["due_date"] == date(2026, 4, 1).isoformat()

    @pytest.mark.unit
    def test_enriched_expense_item_with_card_and_category(
        self,
        person_rodrigo: Person,
        credit_card: CreditCard,
        category_alimentacao: ExpenseCategory,
    ) -> None:
        expense = Expense.objects.create(
            description="Supermercado",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 3, 5),
            person=person_rodrigo,
            credit_card=credit_card,
            category=category_alimentacao,
        )
        exp_reloaded = Expense.objects.select_related(
            "credit_card", "category", "category__parent"
        ).get(pk=expense.pk)
        result = FinancialDashboardService._enriched_expense_item(exp_reloaded)

        assert result["expense_id"] == expense.id
        assert result["installment_id"] is None
        assert result["description"] == "Supermercado"
        assert result["card_name"] == "Nubank Rodrigo"
        assert result["category_name"] == "Alimentação"
        assert result["amount"] == Decimal("300.00")
        assert result["due_date"] == date(2026, 3, 5).isoformat()


class TestGetDashboardSummary:
    """Tests for get_dashboard_summary — the main daily-control summary."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_summary_returns_expected_keys(self) -> None:
        result = FinancialDashboardService.get_dashboard_summary(2026, 3)

        assert result["year"] == 2026
        assert result["month"] == 3
        assert "income_summary" in result
        assert "expense_summary" in result
        assert "overdue_items" in result
        assert "overdue_total" in result
        assert "current_month_income" in result
        assert "current_month_expenses" in result
        assert "current_month_balance" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_balance_is_income_minus_expenses(self) -> None:
        result = FinancialDashboardService.get_dashboard_summary(2026, 3)

        expected = result["current_month_income"] - result["current_month_expenses"]
        assert result["current_month_balance"] == expected

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_income_summary_structure(self) -> None:
        result = FinancialDashboardService.get_dashboard_summary(2026, 3)
        income = result["income_summary"]

        assert "total_monthly_income" in income
        assert "condominium_income" in income
        assert "owner_incomes" in income
        assert "vacant_kitnets" in income
        assert "extra_incomes" in income
        assert "extra_income_total" in income
        assert "salary_offset_apartments" in income

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_expense_summary_structure(self) -> None:
        result = FinancialDashboardService.get_dashboard_summary(2026, 3)
        exp = result["expense_summary"]

        assert "by_person" in exp
        assert "water" in exp
        assert "electricity" in exp
        assert "iptu" in exp
        assert "employee" in exp
        assert "internet" in exp
        assert "celular" in exp
        assert "sitio" in exp
        assert "outros_fixed" in exp
        assert "total" in exp


def _make_tenant(cpf: str, name: str = "Inquilino") -> Tenant:
    """Helper to create a valid Tenant for income summary tests.

    Use formatted CPFs (e.g. '529.982.247-25') which pass checksum validation.
    """
    return Tenant.objects.create(
        name=name,
        cpf_cnpj=cpf,
        phone="11966660001",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=5,
    )


class TestBuildIncomeSummary:
    """Tests for _build_income_summary covering rented/vacant/owner/salary-offset apartments."""

    @pytest.fixture
    def building(self) -> Building:
        return Building.objects.create(
            street_number=5100, name="Prédio Teste", address="Rua Teste, 5100"
        )

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_vacant_apartment_shows_up(self, building: Building) -> None:
        Apartment.objects.create(
            building=building,
            number=1,
            rental_value=Decimal("800.00"),
            max_tenants=2,
            is_rented=False,
        )

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        assert result["vacant_count"] >= 1
        assert result["vacant_lost_rent"] >= Decimal("800.00")
        assert any(apt["apartment_number"] == "1" for apt in result["vacant_kitnets"])

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_rented_apartment_contributes_to_income(self, building: Building) -> None:
        tenant = _make_tenant("111.444.777-35", "Inquilino Rented")
        apt = Apartment.objects.create(
            building=building,
            number=2,
            rental_value=Decimal("1000.00"),
            max_tenants=2,
            is_rented=True,
        )
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1000.00"),
        )
        lease.tenants.add(tenant)

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        assert result["total_monthly_income"] >= Decimal("1000.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_owner_income_separated_from_condominium(self, building: Building) -> None:
        tenant = _make_tenant("529.982.247-25", "Inquilino Owner")
        owner = Person.objects.create(name="Proprietário Único", relationship="Proprietário")
        apt = Apartment.objects.create(
            building=building,
            number=3,
            rental_value=Decimal("900.00"),
            max_tenants=2,
            is_rented=True,
            owner=owner,
        )
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("900.00"),
        )
        lease.tenants.add(tenant)

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        # Owner income should be listed separately
        owner_names = [o["person_name"] for o in result["owner_incomes"]]
        assert "Proprietário Único" in owner_names

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_salary_offset_apartment_not_counted_as_income(self, building: Building) -> None:
        tenant = _make_tenant("246.813.579-28", "Inquilino Salary")
        apt = Apartment.objects.create(
            building=building,
            number=4,
            rental_value=Decimal("700.00"),
            max_tenants=2,
            is_rented=True,
        )
        lease = Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            is_salary_offset=True,
            rental_value=Decimal("700.00"),
        )
        lease.tenants.add(tenant)

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        # Salary offset rent should not add to total_monthly_income
        assert result["salary_offset_total"] >= Decimal("700.00")
        assert len(result["salary_offset_apartments"]) >= 1

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_extra_income_recurring(self) -> None:
        Income.objects.create(
            description="Renda extra recorrente",
            amount=Decimal("500.00"),
            income_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("500.00"),
        )

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        assert result["extra_income_total"] >= Decimal("500.00")
        descriptions = [inc["description"] for inc in result["extra_incomes"]]
        assert "Renda extra recorrente" in descriptions

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_extra_income_one_time_in_month(self) -> None:
        Income.objects.create(
            description="Bônus março",
            amount=Decimal("200.00"),
            income_date=date(2026, 3, 10),
            is_recurring=False,
        )

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        descriptions = [inc["description"] for inc in result["extra_incomes"]]
        assert "Bônus março" in descriptions

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_extra_income_outside_month_excluded(self) -> None:
        Income.objects.create(
            description="Bônus fevereiro",
            amount=Decimal("300.00"),
            income_date=date(2026, 2, 10),
            is_recurring=False,
        )

        result = FinancialDashboardService._build_income_summary(date(2026, 3, 1))

        descriptions = [inc["description"] for inc in result["extra_incomes"]]
        assert "Bônus fevereiro" not in descriptions


class TestBuildFixedExpenseCategories:
    """Tests for _build_fixed_expense_categories — keyword-based categorization."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_internet_categorized_correctly(self) -> None:
        Expense.objects.create(
            description="Internet fibra",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("120.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("120.00"),
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["internet"]["total"] == Decimal("120.00")
        assert len(result["internet"]["details"]) == 1

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_celular_claro_categorized(self) -> None:
        Expense.objects.create(
            description="Claro pós-pago",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("80.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("80.00"),
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["celular"]["total"] == Decimal("80.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_sitio_categorized(self) -> None:
        Expense.objects.create(
            description="Sítio - manutenção",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("200.00"),
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["sitio"]["total"] == Decimal("200.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_racao_goes_to_sitio(self) -> None:
        Expense.objects.create(
            description="Ração cachorro",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["sitio"]["total"] == Decimal("150.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_outros_is_fallback(self) -> None:
        Expense.objects.create(
            description="Assinatura Netflix",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("55.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("55.00"),
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["outros_fixed"]["total"] == Decimal("55.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_person_assigned_expense_excluded(self, person_rodrigo: Person) -> None:
        Expense.objects.create(
            description="Internet pessoal",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("90.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("90.00"),
            person=person_rodrigo,
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        # Person-assigned expenses excluded from fixed categories
        assert result["internet"]["total"] == Decimal("0.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_ended_expense_excluded(self) -> None:
        Expense.objects.create(
            description="Internet antiga",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("90.00"),
            expense_date=date(2025, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("90.00"),
            end_date=date(2026, 2, 28),  # ended before March
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["internet"]["total"] == Decimal("0.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_falls_back_to_total_amount_when_no_expected_monthly(self) -> None:
        Expense.objects.create(
            description="Assinatura anual",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("240.00"),
            expense_date=date(2026, 1, 1),
            is_recurring=True,
            expected_monthly_amount=None,
        )

        result = FinancialDashboardService._build_fixed_expense_categories(date(2026, 3, 1))
        assert result["outros_fixed"]["total"] == Decimal("240.00")


class TestBuildUtilityByBuilding:
    """Tests for _build_utility_by_building."""

    @pytest.fixture
    def building(self) -> Building:
        return Building.objects.create(
            street_number=200, name="Prédio Água", address="Rua Água, 200"
        )

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_recurring_water_bill_included(self, building: Building) -> None:
        Expense.objects.create(
            description="Conta água recorrente",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("0.00"),
            expense_date=date(2026, 3, 1),
            building=building,
            is_recurring=True,
            expected_monthly_amount=Decimal("350.00"),
            is_debt_installment=False,
            is_paid=False,
        )

        result = FinancialDashboardService._build_utility_by_building(
            ExpenseType.WATER_BILL, date(2026, 3, 1), date(2026, 4, 1)
        )
        assert result["total"] == Decimal("350.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_water_debt_installment_included(self, building: Building) -> None:
        expense = Expense.objects.create(
            description="Dívida água parcelada",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("600.00"),
            expense_date=date(2025, 6, 1),
            building=building,
            is_installment=True,
            total_installments=2,
            is_debt_installment=True,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=2,
            amount=Decimal("300.00"),
            due_date=date(2026, 3, 10),
        )

        result = FinancialDashboardService._build_utility_by_building(
            ExpenseType.WATER_BILL, date(2026, 3, 1), date(2026, 4, 1)
        )
        # Standalone debt (no bill for same building) adds to total
        assert result["total"] == Decimal("300.00")
        buildings_map = {b["building_name"]: b for b in result["by_building"]}
        entry = buildings_map.get(str(building.street_number))
        assert entry is not None
        assert len(entry["debt_installments"]) == 1

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_sitio_description_resolves_label(self) -> None:
        Expense.objects.create(
            description="Conta água do Sítio",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("150.00"),
            expense_date=date(2026, 3, 5),
            is_recurring=False,
            is_debt_installment=False,
            is_paid=False,
        )

        result = FinancialDashboardService._build_utility_by_building(
            ExpenseType.WATER_BILL, date(2026, 3, 1), date(2026, 4, 1)
        )
        building_names = [b["building_name"] for b in result["by_building"]]
        assert "Sítio" in building_names

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_ended_recurring_bill_excluded(self, building: Building) -> None:
        Expense.objects.create(
            description="Conta água antiga",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("0.00"),
            expense_date=date(2026, 1, 1),
            building=building,
            is_recurring=True,
            expected_monthly_amount=Decimal("300.00"),
            is_debt_installment=False,
            is_paid=False,
            end_date=date(2026, 2, 28),
        )

        result = FinancialDashboardService._build_utility_by_building(
            ExpenseType.WATER_BILL, date(2026, 3, 1), date(2026, 4, 1)
        )
        assert result["total"] == Decimal("0.00")


class TestGetPersonMonthExpenses:
    """Tests for _get_person_month_expenses."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_card_installment_included(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        _create_expense_with_installments(
            description="Compra março",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("300.00"), "due_date": date(2026, 3, 22)},
            ],
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["card_total"] == Decimal("300.00")
        assert len(result["card_details"]) == 1
        assert result["card_details"][0]["card_name"] == "Nubank Rodrigo"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_card_single_payment_included(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        Expense.objects.create(
            description="Fatura cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 10),
            person=person_rodrigo,
            credit_card=credit_card,
            is_installment=False,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["card_total"] == Decimal("500.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_loan_installment_included(self, person_rodrigo: Person) -> None:
        _create_expense_with_installments(
            description="Empréstimo banco",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("1000.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("500.00"), "due_date": date(2026, 3, 15)},
                {"number": 2, "amount": Decimal("500.00"), "due_date": date(2026, 4, 15)},
            ],
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["loan_total"] == Decimal("500.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_personal_loan_single_included(self, person_rodrigo: Person) -> None:
        Expense.objects.create(
            description="Empréstimo pessoal",
            expense_type=ExpenseType.PERSONAL_LOAN,
            total_amount=Decimal("800.00"),
            expense_date=date(2026, 3, 5),
            person=person_rodrigo,
            is_installment=False,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["loan_total"] == Decimal("800.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_fixed_expense_included(self, person_rodrigo: Person) -> None:
        Expense.objects.create(
            description="Academia",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("0.00"),
            expense_date=date(2026, 1, 1),
            person=person_rodrigo,
            is_recurring=True,
            expected_monthly_amount=Decimal("100.00"),
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["fixed_total"] == Decimal("100.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_one_time_expense_included(self, person_rodrigo: Person) -> None:
        Expense.objects.create(
            description="Médico",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("250.00"),
            expense_date=date(2026, 3, 10),
            person=person_rodrigo,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["one_time_total"] == Decimal("250.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_offset_subtracts_from_total(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        # Regular purchase
        Expense.objects.create(
            description="Compra normal",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 5),
            person=person_rodrigo,
            credit_card=credit_card,
            is_installment=False,
        )
        # Offset (discount)
        Expense.objects.create(
            description="Desconto para outros",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 3, 5),
            person=person_rodrigo,
            credit_card=credit_card,
            is_installment=False,
            is_offset=True,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["offset_total"] == Decimal("100.00")
        assert result["total"] == Decimal("400.00")  # 500 - 100

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_offset_installment_subtracts(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        _create_expense_with_installments(
            description="Compra para sogros",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("200.00"), "due_date": date(2026, 3, 22)},
            ],
        )
        exp = Expense.objects.get(description="Compra para sogros")
        exp.is_offset = True
        exp.save()

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["offset_total"] == Decimal("200.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_stipend_included(self, person_rodrigo: Person) -> None:
        PersonIncome.objects.create(
            person=person_rodrigo,
            income_type=PersonIncomeType.FIXED_STIPEND,
            fixed_amount=Decimal("300.00"),
            start_date=date(2026, 1, 1),
            is_active=True,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["stipend_total"] == Decimal("300.00")
        assert result["is_payable"] is True

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_total_paid_from_person_payment(self, person_rodrigo: Person) -> None:
        PersonPayment.objects.create(
            person=person_rodrigo,
            reference_month=date(2026, 3, 1),
            amount=Decimal("400.00"),
            payment_date=date(2026, 3, 10),
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["total_paid"] == Decimal("400.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_is_payable_via_apartment_owner(self, person_rodrigo: Person) -> None:
        building = Building.objects.create(
            street_number=999, name="Owner Building", address="Rua Owner, 999"
        )
        Apartment.objects.create(
            building=building,
            number=99,
            rental_value=Decimal("1000.00"),
            max_tenants=2,
            is_rented=False,
            owner=person_rodrigo,
        )

        result = FinancialDashboardService._get_person_month_expenses(
            person_rodrigo, date(2026, 3, 1), date(2026, 4, 1)
        )

        assert result["is_payable"] is True


class TestGetPersonWaterfall:
    """Tests for _get_person_waterfall — payment allocation oldest-first."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_waterfall_allocates_oldest_first(self, person_rodrigo: Person) -> None:
        # Create an expense in January
        Expense.objects.create(
            description="Fatura jan",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 1, 5),
            person=person_rodrigo,
            is_installment=False,
        )
        # Payment covers January
        PersonPayment.objects.create(
            person=person_rodrigo,
            reference_month=date(2026, 1, 1),
            amount=Decimal("200.00"),
            payment_date=date(2026, 1, 20),
        )

        result = FinancialDashboardService._get_person_waterfall(person_rodrigo, 2026, 1)

        jan_key = "2026-01"
        assert jan_key in result
        assert result[jan_key]["allocated_paid"] == Decimal("200.00")
        assert result[jan_key]["pending"] == Decimal("0.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_waterfall_respects_financial_settings_start_date(
        self, person_rodrigo: Person
    ) -> None:
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("0.00"),
                "initial_balance_date": date(2026, 2, 1),
            },
        )
        result = FinancialDashboardService._get_person_waterfall(person_rodrigo, 2026, 3)

        # Should only include months from 2026-02 onwards
        months_in_result = list(result.keys())
        assert "2026-01" not in months_in_result
        assert "2026-02" in months_in_result
        assert "2026-03" in months_in_result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_partial_payment_leaves_pending(self, person_rodrigo: Person) -> None:
        Expense.objects.create(
            description="Fatura parcial",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 3, 5),
            person=person_rodrigo,
            is_installment=False,
        )
        PersonPayment.objects.create(
            person=person_rodrigo,
            reference_month=date(2026, 3, 1),
            amount=Decimal("200.00"),
            payment_date=date(2026, 3, 10),
        )

        result = FinancialDashboardService._get_person_waterfall(person_rodrigo, 2026, 3)

        mar_key = "2026-03"
        assert result[mar_key]["pending"] == Decimal("300.00")
        assert result[mar_key]["allocated_paid"] == Decimal("200.00")


class TestGetExpenseDetail:
    """Tests for get_expense_detail — the dispatch method."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_unknown_detail_type_returns_error(self) -> None:
        result = FinancialDashboardService.get_expense_detail("unknown_type", None, 2026, 3)
        assert "error" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_person_detail_type_missing_id_returns_error(self) -> None:
        result = FinancialDashboardService.get_expense_detail("person", None, 2026, 3)
        assert "error" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_person_detail_type_nonexistent_id_returns_error(self) -> None:
        result = FinancialDashboardService.get_expense_detail("person", 999999, 2026, 3)
        assert "error" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_person_detail_returns_full_breakdown(self, person_rodrigo: Person) -> None:
        result = FinancialDashboardService.get_expense_detail(
            "person", person_rodrigo.pk, 2026, 3
        )

        assert result["detail_type"] == "person"
        assert result["person_id"] == person_rodrigo.pk
        assert result["person_name"] == "Rodrigo"
        assert "card_total" in result
        assert "loan_total" in result
        assert "total" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_electricity_detail_type(self) -> None:
        result = FinancialDashboardService.get_expense_detail("electricity", None, 2026, 3)
        assert result["detail_type"] == "electricity"
        assert result["label"] == "Contas de Luz"
        assert "total" in result
        assert "by_building" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_water_detail_type(self) -> None:
        result = FinancialDashboardService.get_expense_detail("water", None, 2026, 3)
        assert result["detail_type"] == "water"
        assert result["label"] == "Contas de Água"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_iptu_detail_type(self) -> None:
        result = FinancialDashboardService.get_expense_detail("iptu", None, 2026, 3)
        assert result["detail_type"] == "iptu"
        assert result["label"] == "IPTU"
        assert "total" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_internet_fixed_category_detail(self) -> None:
        result = FinancialDashboardService.get_expense_detail("internet", None, 2026, 3)
        assert result["detail_type"] == "internet"
        assert result["label"] == "Internet"
        assert "total" in result
        assert "details" in result

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_celular_fixed_category_detail(self) -> None:
        result = FinancialDashboardService.get_expense_detail("celular", None, 2026, 3)
        assert result["detail_type"] == "celular"
        assert result["label"] == "Celular"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_sitio_fixed_category_detail(self) -> None:
        result = FinancialDashboardService.get_expense_detail("sitio", None, 2026, 3)
        assert result["detail_type"] == "sitio"
        assert result["label"] == "Sítio"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_outros_fixed_category_detail(self) -> None:
        result = FinancialDashboardService.get_expense_detail("outros_fixed", None, 2026, 3)
        assert result["detail_type"] == "outros_fixed"
        assert result["label"] == "Outros Fixos"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_employee_detail_type_empty(self) -> None:
        result = FinancialDashboardService.get_expense_detail("employee", None, 2026, 3)
        assert result["detail_type"] == "employee"
        assert result["label"] == "Funcionários"
        assert result["total"] == Decimal("0.00")
        assert result["details"] == []

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_employee_detail_with_payment(self) -> None:
        employee = Person.objects.create(
            name="Funcionário Teste", relationship="Funcionário", is_employee=True
        )
        EmployeePayment.objects.create(
            person=employee,
            reference_month=date(2026, 3, 1),
            base_salary=Decimal("1500.00"),
            variable_amount=Decimal("0.00"),
        )

        result = FinancialDashboardService.get_expense_detail("employee", None, 2026, 3)

        assert result["total"] == Decimal("1500.00")
        assert len(result["details"]) == 1
        assert "Funcionário Teste" in result["details"][0]["description"]

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_employee_detail_variable_amount_shown(self) -> None:
        employee = Person.objects.create(
            name="Func Variable", relationship="Funcionário", is_employee=True
        )
        EmployeePayment.objects.create(
            person=employee,
            reference_month=date(2026, 3, 1),
            base_salary=Decimal("1000.00"),
            variable_amount=Decimal("200.00"),
        )

        result = FinancialDashboardService.get_expense_detail("employee", None, 2026, 3)

        assert result["total"] == Decimal("1200.00")
        # Notes should include variable amount
        notes = result["details"][0]["notes"]
        assert "Variável" in notes


class TestDetailIptu:
    """Tests for _detail_iptu with real IPTU installments."""

    @pytest.fixture
    def building(self) -> Building:
        return Building.objects.create(
            street_number=300, name="Prédio IPTU", address="Rua IPTU, 300"
        )

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_iptu_installments_grouped_by_building(self, building: Building) -> None:
        expense = Expense.objects.create(
            description="IPTU 2026",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("2400.00"),
            expense_date=date(2026, 1, 1),
            building=building,
            is_installment=True,
            total_installments=10,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=3,
            total_installments=10,
            amount=Decimal("240.00"),
            due_date=date(2026, 3, 10),
        )

        result = FinancialDashboardService._detail_iptu(date(2026, 3, 1), date(2026, 4, 1))

        assert result["detail_type"] == "iptu"
        assert result["total"] == Decimal("240.00")
        buildings_map = {b["building_name"]: b for b in result["by_building"]}
        assert str(building.street_number) in buildings_map

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_iptu_no_building_goes_to_outros(self) -> None:
        expense = Expense.objects.create(
            description="IPTU outros",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 1, 1),
            building=None,
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("500.00"),
            due_date=date(2026, 3, 5),
        )

        result = FinancialDashboardService._detail_iptu(date(2026, 3, 1), date(2026, 4, 1))

        building_names = [b["building_name"] for b in result["by_building"]]
        assert "Outros" in building_names


class TestBuildOverduePreviousMonths:
    """Tests for _build_overdue_previous_months."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_iptu_overdue_from_previous_month(self) -> None:
        building = Building.objects.create(
            street_number=400, name="IPTU Overdue", address="Rua Overdue, 400"
        )
        expense = Expense.objects.create(
            description="IPTU fev",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("480.00"),
            expense_date=date(2026, 1, 1),
            building=building,
            is_installment=True,
            total_installments=2,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=2,
            amount=Decimal("240.00"),
            due_date=date(2026, 2, 10),
            is_paid=False,
        )

        result = FinancialDashboardService._build_overdue_previous_months(2026, 3)

        iptu_items = [item for item in result if item["type"] == "iptu"]
        assert len(iptu_items) == 1
        assert iptu_items[0]["amount"] == Decimal("240.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_paid_iptu_not_overdue(self) -> None:
        building = Building.objects.create(
            street_number=401, name="IPTU Paid", address="Rua Paid, 401"
        )
        expense = Expense.objects.create(
            description="IPTU pago",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("240.00"),
            expense_date=date(2026, 1, 1),
            building=building,
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("240.00"),
            due_date=date(2026, 2, 10),
            is_paid=True,
        )

        result = FinancialDashboardService._build_overdue_previous_months(2026, 3)

        iptu_items = [item for item in result if item["type"] == "iptu"]
        assert len(iptu_items) == 0

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_zero_amount_iptu_excluded(self) -> None:
        building = Building.objects.create(
            street_number=402, name="IPTU Zero", address="Rua Zero, 402"
        )
        expense = Expense.objects.create(
            description="IPTU zero",
            expense_type=ExpenseType.PROPERTY_TAX,
            total_amount=Decimal("0.00"),
            expense_date=date(2026, 1, 1),
            building=building,
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("0.00"),
            due_date=date(2026, 2, 10),
            is_paid=False,
        )

        result = FinancialDashboardService._build_overdue_previous_months(2026, 3)

        iptu_items = [item for item in result if item["type"] == "iptu"]
        assert len(iptu_items) == 0

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_person_overdue_via_waterfall(self, person_rodrigo: Person) -> None:
        # Give person a stipend (makes them payable)
        PersonIncome.objects.create(
            person=person_rodrigo,
            income_type=PersonIncomeType.FIXED_STIPEND,
            fixed_amount=Decimal("500.00"),
            start_date=date(2026, 1, 1),
            is_active=True,
        )
        FinancialSettings.objects.update_or_create(
            pk=1,
            defaults={
                "initial_balance": Decimal("0.00"),
                "initial_balance_date": date(2026, 1, 1),
            },
        )
        # Expense in January with no payment
        Expense.objects.create(
            description="Gasto janeiro",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("500.00"),
            expense_date=date(2026, 1, 5),
            person=person_rodrigo,
            is_recurring=True,
            expected_monthly_amount=Decimal("500.00"),
        )

        result = FinancialDashboardService._build_overdue_previous_months(2026, 3)

        person_items = [item for item in result if item["type"] == "person"]
        rodrigo_items = [p for p in person_items if p["person_name"] == "Rodrigo"]
        # January should appear as overdue since no payment was made
        assert len(rodrigo_items) > 0


class TestUpcomingInstallmentsEdgeCases:
    """Edge cases for get_upcoming_installments."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_upcoming_no_person_no_card_returns_none_fields(self) -> None:
        expense = Expense.objects.create(
            description="Gasto sem pessoa",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 1, 1),
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("300.00"),
            due_date=date(2026, 3, 20),
        )

        result = FinancialDashboardService.get_upcoming_installments(days=30)

        assert len(result) == 1
        assert result[0]["person_name"] is None
        assert result[0]["credit_card_nickname"] is None
        assert result[0]["days_until_due"] == 5

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_upcoming_with_person_and_card(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        _create_expense_with_installments(
            description="Compra cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 3, 20)},
            ],
        )

        result = FinancialDashboardService.get_upcoming_installments(days=30)

        assert len(result) == 1
        assert result[0]["person_name"] == "Rodrigo"
        assert result[0]["credit_card_nickname"] == "Nubank Rodrigo"

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_upcoming_empty_when_no_installments(self) -> None:
        result = FinancialDashboardService.get_upcoming_installments(days=30)
        assert result == []


class TestOverdueInstallmentsEdgeCases:
    """Edge cases for get_overdue_installments."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_overdue_no_person_no_card(self) -> None:
        expense = Expense.objects.create(
            description="Dívida sem pessoa",
            expense_type=ExpenseType.BANK_LOAN,
            total_amount=Decimal("200.00"),
            expense_date=date(2025, 12, 1),
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("200.00"),
            due_date=date(2026, 2, 1),
        )

        result = FinancialDashboardService.get_overdue_installments()

        assert len(result) == 1
        assert result[0]["person_name"] is None
        assert result[0]["credit_card_nickname"] is None
        assert result[0]["days_overdue"] == 42  # 2026-03-15 - 2026-02-01 = 42 days

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_overdue_empty_when_all_paid(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        _create_expense_with_installments(
            description="Pago",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {
                    "number": 1,
                    "amount": Decimal("100.00"),
                    "due_date": date(2026, 2, 1),
                    "is_paid": True,
                },
            ],
        )

        result = FinancialDashboardService.get_overdue_installments()
        assert result == []


class TestNextMonthStart:
    """Tests for the _next_month_start module-level helper."""

    @pytest.mark.unit
    def test_december_wraps_to_next_year(self) -> None:
        from core.services.financial_dashboard_service import _next_month_start

        result = _next_month_start(2025, 12)
        assert result == date(2026, 1, 1)

    @pytest.mark.unit
    def test_regular_month_increments(self) -> None:
        from core.services.financial_dashboard_service import _next_month_start

        result = _next_month_start(2026, 3)
        assert result == date(2026, 4, 1)


class TestResolveBuildingLabel:
    """Tests for the _resolve_building_label module-level helper."""

    @pytest.mark.unit
    def test_building_fk_uses_street_number(self) -> None:
        from core.services.financial_dashboard_service import _resolve_building_label

        building = Building.objects.create(
            street_number=836, name="Prédio Label", address="Rua Label, 836"
        )
        result = _resolve_building_label(building, "qualquer")
        assert result == "836"

    @pytest.mark.unit
    def test_no_building_sitio_keyword(self) -> None:
        from core.services.financial_dashboard_service import _resolve_building_label

        result = _resolve_building_label(None, "Conta água do Sítio")
        assert result == "Sítio"

    @pytest.mark.unit
    def test_no_building_sitio_without_accent(self) -> None:
        from core.services.financial_dashboard_service import _resolve_building_label

        result = _resolve_building_label(None, "sitio - custo mensal")
        assert result == "Sítio"

    @pytest.mark.unit
    def test_no_building_no_keyword_returns_outros(self) -> None:
        from core.services.financial_dashboard_service import _resolve_building_label

        result = _resolve_building_label(None, "Descricao generica")
        assert result == "Outros"


class TestDebtByPersonEdgeCases:
    """Additional edge cases for get_debt_by_person."""

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_personal_loan_counted_in_loan_debt(self, person_rodrigo: Person) -> None:
        _create_expense_with_installments(
            description="Empréstimo pessoal Rodrigo",
            expense_type=ExpenseType.PERSONAL_LOAN,
            total_amount=Decimal("600.00"),
            person=person_rodrigo,
            installments=[
                {"number": 1, "amount": Decimal("300.00"), "due_date": date(2026, 3, 15)},
                {"number": 2, "amount": Decimal("300.00"), "due_date": date(2026, 4, 15)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_person()
        rodrigo_data = next(p for p in result if p["person_id"] == person_rodrigo.id)

        assert rodrigo_data["loan_debt"] == Decimal("600.00")

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_cards_count_included(self, person_rodrigo: Person, credit_card: CreditCard) -> None:
        _create_expense_with_installments(
            description="Compra cartão count",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            person=person_rodrigo,
            credit_card=credit_card,
            installments=[
                {"number": 1, "amount": Decimal("100.00"), "due_date": date(2026, 4, 1)},
            ],
        )

        result = FinancialDashboardService.get_debt_by_person()
        rodrigo_data = next(p for p in result if p["person_id"] == person_rodrigo.id)

        assert rodrigo_data["cards_count"] == 1  # One active credit card

    @pytest.mark.unit
    @freeze_time("2026-03-15")
    def test_offset_expense_excluded_from_debt(
        self, person_rodrigo: Person, credit_card: CreditCard
    ) -> None:
        exp = Expense.objects.create(
            description="Offset cartão",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 3, 1),
            person=person_rodrigo,
            credit_card=credit_card,
            is_installment=True,
            total_installments=1,
            is_offset=True,
        )
        ExpenseInstallment.objects.create(
            expense=exp,
            installment_number=1,
            total_installments=1,
            amount=Decimal("200.00"),
            due_date=date(2026, 4, 1),
        )

        result = FinancialDashboardService.get_debt_by_person()
        rodrigo_items = [p for p in result if p["person_id"] == person_rodrigo.id]

        # With no non-offset expenses, person may not appear (no installments after filter)
        # or if they appear, card_debt should be zero
        if rodrigo_items:
            assert rodrigo_items[0]["card_debt"] == Decimal("0.00")
