"""Tests for CashFlowService — monthly income, expenses, projection, and person summary."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import (
    Apartment,
    Building,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    FinancialSettings,
    Income,
    Lease,
    Person,
    PersonIncome,
    PersonIncomeType,
    RentPayment,
    Tenant,
)
from core.services.cash_flow_service import CashFlowService
from core.services.date_calculator import DateCalculatorService

# =============================================================================
# _next_month_start helper
# =============================================================================


@pytest.mark.unit
class TestNextMonthStart:
    def test_mid_year(self) -> None:
        assert DateCalculatorService.next_month_start(2026, 3) == date(2026, 4, 1)

    def test_december_wraps_to_january(self) -> None:
        assert DateCalculatorService.next_month_start(2026, 12) == date(2027, 1, 1)

    def test_november(self) -> None:
        assert DateCalculatorService.next_month_start(2026, 11) == date(2026, 12, 1)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def building() -> Building:
    return Building.objects.create(
        street_number=601, name="Cash Flow Building", address="Rua CF, 601"
    )


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return Apartment.objects.create(
        building=building, number=101, rental_value=Decimal("1500.00"), max_tenants=2
    )


@pytest.fixture
def tenant() -> Tenant:
    return Tenant.objects.create(
        name="CF Tenant",
        cpf_cnpj="52998224725",
        phone="11987654321",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
    )


@pytest.fixture
def lease(apartment: Apartment, tenant: Tenant) -> Lease:
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=24,
        rental_value=Decimal("1500.00"),
    )


@pytest.fixture
def person() -> Person:
    return Person.objects.create(name="CF Person", relationship="Filho")


# =============================================================================
# get_monthly_income
# =============================================================================


@pytest.mark.unit
class TestGetMonthlyIncome:
    def test_returns_rent_for_active_lease(self, lease: Lease) -> None:
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_income"] == Decimal("1500.00")
        assert len(result["rent_details"]) == 1

    def test_rent_detail_shows_unpaid_when_no_payment(self, lease: Lease) -> None:
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_details"][0]["is_paid"] is False
        assert result["rent_details"][0]["payment_date"] is None

    def test_rent_detail_shows_paid_when_payment_exists(self, lease: Lease) -> None:
        RentPayment.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 3, 10),
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["rent_details"][0]["is_paid"] is True
        assert result["rent_details"][0]["payment_date"] == date(2026, 3, 10)

    def test_excludes_owner_apartment(self, building: Building) -> None:
        owner = Person.objects.create(name="Owner", relationship="Dono")
        owned_apt = Apartment.objects.create(
            building=building,
            number=202,
            rental_value=Decimal("2000.00"),
            max_tenants=1,
            owner=owner,
        )
        t = Tenant.objects.create(
            name="Owner Tenant",
            cpf_cnpj="11144477735",
            phone="11912345678",
            marital_status="Solteiro(a)",
            profession="Dev",
        )
        Lease.objects.create(
            apartment=owned_apt,
            responsible_tenant=t,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("2000.00"),
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        apt_ids = [d["apartment_id"] for d in result["rent_details"]]
        assert owned_apt.pk not in apt_ids

    def test_excludes_prepaid_lease(self, lease: Lease) -> None:
        lease.prepaid_until = date(2026, 6, 1)
        lease.save()
        result = CashFlowService.get_monthly_income(2026, 3)
        assert len(result["rent_details"]) == 0

    def test_excludes_salary_offset_lease(self, lease: Lease) -> None:
        lease.is_salary_offset = True
        lease.save()
        result = CashFlowService.get_monthly_income(2026, 3)
        assert len(result["rent_details"]) == 0

    def test_includes_recurring_income(self) -> None:
        Income.objects.create(
            description="Aposentadoria",
            amount=Decimal("3000.00"),
            income_date=date(2026, 3, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("3000.00"),
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["extra_income"] >= Decimal("3000.00")

    def test_includes_received_non_recurring_income(self) -> None:
        Income.objects.create(
            description="Bônus",
            amount=Decimal("500.00"),
            income_date=date(2026, 3, 15),
            is_recurring=False,
            is_received=True,
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        assert result["extra_income"] >= Decimal("500.00")

    def test_excludes_non_received_non_recurring_income(self) -> None:
        Income.objects.create(
            description="Bônus Pendente",
            amount=Decimal("500.00"),
            income_date=date(2026, 3, 15),
            is_recurring=False,
            is_received=False,
        )
        result = CashFlowService.get_monthly_income(2026, 3)
        # Non-received non-recurring income should not be included
        descriptions = [d["description"] for d in result["extra_income_details"]]
        assert "Bônus Pendente" not in descriptions


# =============================================================================
# get_monthly_expenses
# =============================================================================


@pytest.mark.unit
class TestGetMonthlyExpenses:
    def test_returns_all_expense_keys(self) -> None:
        result = CashFlowService.get_monthly_expenses(2026, 3)
        expected_keys = [
            "owner_repayments",
            "person_stipends",
            "card_installments",
            "loan_installments",
            "utility_bills",
            "debt_installments",
            "property_tax",
            "employee_salary",
            "fixed_expenses",
            "one_time_expenses",
            "total",
        ]
        for key in expected_keys:
            assert key in result

    def test_card_installments_counted(self, person: Person) -> None:
        from core.models import CreditCard

        cc = CreditCard.objects.create(
            person=person,
            nickname="CF Card",
            last_four_digits="9999",
            closing_day=5,
            due_day=12,
            is_active=True,
        )
        expense = Expense.objects.create(
            description="Card Expense CF",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            credit_card=cc,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=2,
            total_installments=3,
            amount=Decimal("100.00"),
            due_date=date(2026, 3, 15),
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["card_installments"] >= Decimal("100.00")

    def test_utility_bills_counted(self, building: Building) -> None:
        Expense.objects.create(
            description="Água março",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 3, 10),
            building=building,
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["utility_bills"] >= Decimal("200.00")

    def test_fixed_expenses_counted(self) -> None:
        Expense.objects.create(
            description="Internet CF",
            expense_type=ExpenseType.FIXED_EXPENSE,
            total_amount=Decimal("150.00"),
            expense_date=date(2025, 1, 1),
            is_recurring=True,
            expected_monthly_amount=Decimal("150.00"),
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["fixed_expenses"] >= Decimal("150.00")

    def test_one_time_expenses_counted(self) -> None:
        Expense.objects.create(
            description="Gasto único CF",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 3, 20),
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["one_time_expenses"] >= Decimal("300.00")

    def test_is_offset_excluded_from_card_installments(self, person: Person) -> None:
        from core.models import CreditCard

        cc = CreditCard.objects.create(
            person=person,
            nickname="Offset Card",
            last_four_digits="8888",
            closing_day=5,
            due_day=12,
            is_active=True,
        )
        expense = Expense.objects.create(
            description="Offset Expense CF",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            credit_card=cc,
            is_installment=True,
            total_installments=1,
            is_offset=True,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("200.00"),
            due_date=date(2026, 3, 15),
        )
        result_before = CashFlowService.get_monthly_expenses(2026, 3)
        # The offset installment should not appear in card_installments
        assert result_before["card_installments"] == Decimal("0.00")

    def test_employee_salary_counted(self, person: Person) -> None:
        person.is_employee = True
        person.save()
        EmployeePayment.objects.create(
            person=person,
            reference_month=date(2026, 3, 1),
            base_salary=Decimal("2000.00"),
            is_paid=True,
            payment_date=date(2026, 3, 10),
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["employee_salary"] >= Decimal("2000.00")

    def test_owner_repayments_counted(self, building: Building) -> None:
        owner = Person.objects.create(name="Owner CF", relationship="Dono")
        apt = Apartment.objects.create(
            building=building,
            number=303,
            rental_value=Decimal("1800.00"),
            max_tenants=1,
            owner=owner,
        )
        t = Tenant.objects.create(
            name="Owner T",
            cpf_cnpj="12345678909",
            phone="11999888777",
            marital_status="Solteiro(a)",
            profession="Dev",
        )
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=t,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1800.00"),
        )
        result = CashFlowService.get_monthly_expenses(2026, 3)
        assert result["owner_repayments"] >= Decimal("1800.00")


# =============================================================================
# get_monthly_cash_flow
# =============================================================================


@pytest.mark.unit
class TestGetMonthlyCashFlow:
    def test_returns_balance(self, lease: Lease) -> None:
        result = CashFlowService.get_monthly_cash_flow(2026, 3)
        assert "balance" in result
        assert result["balance"] == result["income"]["total"] - result["expenses"]["total"]

    def test_returns_year_month(self) -> None:
        result = CashFlowService.get_monthly_cash_flow(2026, 3)
        assert result["year"] == 2026
        assert result["month"] == 3


# =============================================================================
# get_cash_flow_projection
# =============================================================================


@pytest.mark.unit
class TestGetCashFlowProjection:
    @freeze_time("2026-03-15")
    def test_returns_correct_number_of_months(self) -> None:
        result = CashFlowService.get_cash_flow_projection(months=6)
        assert len(result) == 6

    @freeze_time("2026-03-15")
    def test_first_month_is_current_not_projected(self) -> None:
        result = CashFlowService.get_cash_flow_projection(months=3)
        assert result[0]["is_projected"] is False

    @freeze_time("2026-03-15")
    def test_future_months_are_projected(self) -> None:
        result = CashFlowService.get_cash_flow_projection(months=3)
        for entry in result[1:]:
            assert entry["is_projected"] is True

    @freeze_time("2026-03-15")
    def test_uses_initial_balance_from_settings(self) -> None:
        FinancialSettings.objects.filter(pk=1).delete()
        FinancialSettings.objects.create(
            pk=1,
            initial_balance=Decimal("5000.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        result = CashFlowService.get_cash_flow_projection(months=1)
        # cumulative starts with initial_balance + month balance
        assert result[0]["cumulative_balance"] == Decimal("5000.00") + result[0]["balance"]

    @freeze_time("2026-03-15")
    def test_december_wraps_correctly(self) -> None:
        result = CashFlowService.get_cash_flow_projection(months=13)
        months = [(e["year"], e["month"]) for e in result]
        assert (2027, 3) in months

    @freeze_time("2026-03-15")
    def test_projected_utility_average_no_data(self) -> None:
        avg = CashFlowService._get_projected_utility_average()
        assert avg == Decimal("0.00")

    @freeze_time("2026-03-15")
    def test_projected_utility_average_with_data(self, building: Building) -> None:
        Expense.objects.create(
            description="Water bill avg",
            expense_type=ExpenseType.WATER_BILL,
            total_amount=Decimal("200.00"),
            expense_date=date(2026, 2, 10),
            building=building,
        )
        avg = CashFlowService._get_projected_utility_average()
        assert avg == Decimal("200.00")


# =============================================================================
# get_person_summary
# =============================================================================


@pytest.mark.unit
class TestGetPersonSummary:
    def test_raises_for_nonexistent_person(self) -> None:
        with pytest.raises(Person.DoesNotExist):
            CashFlowService.get_person_summary(999999, 2026, 3)

    def test_returns_summary_keys(self, person: Person) -> None:
        result = CashFlowService.get_person_summary(person.pk, 2026, 3)
        assert "person_name" in result
        assert "card_total" in result
        assert "loan_total" in result
        assert "fixed_total" in result
        assert "net_amount" in result

    def test_card_total_includes_card_installments(self, person: Person) -> None:
        from core.models import CreditCard

        cc = CreditCard.objects.create(
            person=person,
            nickname="Summary Card",
            last_four_digits="7777",
            closing_day=5,
            due_day=12,
            is_active=True,
        )
        expense = Expense.objects.create(
            description="Card Summary",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            credit_card=cc,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=2,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=date(2026, 3, 12),
        )
        result = CashFlowService.get_person_summary(person.pk, 2026, 3)
        assert result["card_total"] >= Decimal("200.00")

    def test_net_amount_subtracts_expenses(self, person: Person) -> None:
        from core.models import CreditCard

        cc = CreditCard.objects.create(
            person=person,
            nickname="Net Card",
            last_four_digits="6666",
            closing_day=5,
            due_day=12,
            is_active=True,
        )
        expense = Expense.objects.create(
            description="Net Test",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 2, 1),
            person=person,
            credit_card=cc,
            is_installment=True,
            total_installments=1,
        )
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("300.00"),
            due_date=date(2026, 3, 12),
        )
        result = CashFlowService.get_person_summary(person.pk, 2026, 3)
        # net_amount = income - expenses; person has no income, so should be negative
        assert result["net_amount"] <= Decimal("0.00")

    def test_person_income_included(self, person: Person, admin_user) -> None:
        PersonIncome.objects.create(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            fixed_amount=Decimal("500.00"),
            start_date=date(2025, 1, 1),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        result = CashFlowService.get_person_summary(person.pk, 2026, 3)
        assert (
            result["net_amount"]
            >= Decimal("500.00")
            - result["card_total"]
            - result["loan_total"]
            - result["fixed_total"]
        )
