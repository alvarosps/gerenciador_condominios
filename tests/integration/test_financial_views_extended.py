"""Extended integration tests for financial ViewSets — covering missing branches."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import (
    CreditCard,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    FinancialSettings,
    Income,
    Person,
)


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def person(admin_user):
    return Person.objects.create(
        name="Ana Lima",
        relationship="Proprietária",
        phone="11999990001",
        email="ana@test.com",
        is_owner=True,
        is_employee=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_person(admin_user):
    return Person.objects.create(
        name="Pedro Func",
        relationship="Funcionário",
        is_employee=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def credit_card(person, admin_user):
    return CreditCard.objects.create(
        person=person,
        nickname="Visa",
        last_four_digits="4321",
        closing_day=10,
        due_day=17,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category(admin_user):
    return ExpenseCategory.objects.create(
        name="Utilidades",
        description="Luz, água, etc.",
        color="#00FF00",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def expense(person, category, admin_user):
    return Expense.objects.create(
        description="Conta de luz",
        expense_type="variable",
        total_amount=Decimal("250.00"),
        expense_date=date(2026, 3, 1),
        person=person,
        category=category,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def installment_expense(person, category, credit_card, admin_user):
    return Expense.objects.create(
        description="Compra parcelada",
        expense_type="variable",
        total_amount=Decimal("600.00"),
        expense_date=date(2026, 3, 1),
        person=person,
        credit_card=credit_card,
        category=category,
        is_installment=True,
        total_installments=3,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def income(person, admin_user):
    return Income.objects.create(
        description="Aluguel recebido",
        amount=Decimal("1500.00"),
        income_date=date(2026, 3, 5),
        person=person,
        is_received=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


# =============================================================================
# FinancialSettings — missing branches (lines 113-114, 126)
# =============================================================================


@pytest.mark.integration
class TestFinancialSettingsMissingBranches:
    url = "/api/financial-settings/current/"

    def test_put_when_settings_do_not_exist_creates_and_saves(self, authenticated_api_client):
        """Covers lines 113-114: DoesNotExist branch in PUT/PATCH."""
        assert FinancialSettings.objects.count() == 0
        response = authenticated_api_client.put(
            self.url,
            {
                "initial_balance": "2000.00",
                "initial_balance_date": "2026-01-01",
                "notes": "Criado via PUT",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["initial_balance"]) == Decimal("2000.00")

    def test_put_with_invalid_data_returns_400(self, authenticated_api_client):
        """Covers line 126: invalid serializer returns 400."""
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        response = authenticated_api_client.put(
            self.url,
            {"initial_balance": "not-a-number", "initial_balance_date": "2026-01-01"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_when_settings_do_not_exist_creates_and_saves(self, authenticated_api_client):
        """PATCH also hits DoesNotExist branch when settings don't exist."""
        assert FinancialSettings.objects.count() == 0
        response = authenticated_api_client.patch(
            self.url,
            {"notes": "Criado via PATCH"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "Criado via PATCH"


# =============================================================================
# ExpenseViewSet — filter branches (lines 176, 179, 182, 185)
# =============================================================================


@pytest.mark.integration
class TestExpenseFilters:
    url = "/api/expenses/"

    def test_filter_by_is_installment_true(self, authenticated_api_client, installment_expense, expense):
        response = authenticated_api_client.get(f"{self.url}?is_installment=true")
        assert response.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in response.data["results"]]
        assert installment_expense.pk in ids
        assert expense.pk not in ids

    def test_filter_by_is_recurring_false(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?is_recurring=false")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_is_debt_installment(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?is_debt_installment=false")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_is_offset(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?is_offset=false")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_date_from(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?date_from=2026-03-01")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_date_to(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?date_to=2026-03-31")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_expense_type(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(f"{self.url}?expense_type=variable")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_category_id(self, authenticated_api_client, expense, category):
        response = authenticated_api_client.get(f"{self.url}?category_id={category.pk}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_credit_card_id(self, authenticated_api_client, installment_expense, credit_card):
        response = authenticated_api_client.get(f"{self.url}?credit_card_id={credit_card.pk}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1


# =============================================================================
# ExpenseViewSet — rebuild action (lines 253-297)
# =============================================================================


@pytest.mark.integration
class TestExpenseRebuild:
    def test_rebuild_replaces_installments(
        self, authenticated_api_client, installment_expense, admin_user
    ):
        """Covers the rebuild action: lines 251-297."""
        # First create some installments
        for i in range(1, 4):
            ExpenseInstallment.objects.create(
                expense=installment_expense,
                installment_number=i,
                total_installments=3,
                amount=Decimal("200.00"),
                due_date=date(2026, 3 + i - 1, 15),
                created_by=admin_user,
                updated_by=admin_user,
            )
        assert installment_expense.installments.count() == 3

        rebuild_data = {
            "description": "Compra parcelada atualizada",
            "total_amount": "900.00",
            "is_installment": True,
            "total_installments": 2,
            "installments": [
                {
                    "installment_number": 1,
                    "total_installments": 2,
                    "amount": "450.00",
                    "due_date": "2026-04-17",
                    "is_paid": False,
                },
                {
                    "installment_number": 2,
                    "total_installments": 2,
                    "amount": "450.00",
                    "due_date": "2026-05-17",
                    "is_paid": False,
                },
            ],
        }
        url = f"/api/expenses/{installment_expense.pk}/rebuild/"
        response = authenticated_api_client.post(url, rebuild_data, format="json")
        assert response.status_code == status.HTTP_200_OK

        installment_expense.refresh_from_db()
        assert installment_expense.description == "Compra parcelada atualizada"

        # Old installments deleted, new ones created
        assert ExpenseInstallment.objects.filter(expense=installment_expense).count() == 2

    def test_rebuild_with_empty_installments_clears_all(
        self, authenticated_api_client, installment_expense, admin_user
    ):
        """Rebuild with no installments list clears existing ones."""
        ExpenseInstallment.objects.create(
            expense=installment_expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("600.00"),
            due_date=date(2026, 4, 17),
            created_by=admin_user,
            updated_by=admin_user,
        )
        url = f"/api/expenses/{installment_expense.pk}/rebuild/"
        response = authenticated_api_client.post(
            url, {"installments": []}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert ExpenseInstallment.objects.filter(expense=installment_expense).count() == 0


# =============================================================================
# ExpenseViewSet — generate_installments already-exists branch (line 209-212)
# =============================================================================


@pytest.mark.integration
class TestExpenseGenerateInstallmentsEdgeCases:
    def test_generate_installments_already_exists_returns_400(
        self, authenticated_api_client, installment_expense, admin_user
    ):
        """Covers line 208-212: already-generated installments branch."""
        ExpenseInstallment.objects.create(
            expense=installment_expense,
            installment_number=1,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=date(2026, 4, 17),
            created_by=admin_user,
            updated_by=admin_user,
        )
        url = f"/api/expenses/{installment_expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Parcelas já foram geradas" in response.data["error"]

    def test_generate_installments_not_installment_returns_400(
        self, authenticated_api_client, expense
    ):
        """Covers line 202-206: expense is not installment."""
        url = f"/api/expenses/{expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_installments_without_credit_card(
        self, authenticated_api_client, person, category, admin_user
    ):
        """Covers line 231: due_date = start_date + relativedelta (no credit card path)."""
        expense = Expense.objects.create(
            description="Parcela sem cartão",
            expense_type="variable",
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 3, 1),
            person=person,
            category=category,
            is_installment=True,
            total_installments=3,
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
        url = f"/api/expenses/{expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url, {"start_date": "2026-03-01"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert expense.installments.count() == 3


# =============================================================================
# ExpenseInstallmentViewSet — bulk_mark_paid missing installments (lines 373-376)
# =============================================================================


@pytest.mark.integration
class TestBulkMarkPaidEdgeCases:
    url = "/api/expense-installments/bulk_mark_paid/"

    def test_bulk_mark_paid_missing_installments_returns_400(
        self, authenticated_api_client
    ):
        """Covers line 373-376: count mismatch."""
        response = authenticated_api_client.post(
            self.url,
            {"installment_ids": [99999, 99998], "paid_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "não foram encontradas" in response.data["error"]

    def test_bulk_mark_paid_empty_ids_returns_400(self, authenticated_api_client):
        """Covers line 366-370: empty installment_ids."""
        response = authenticated_api_client.post(
            self.url, {"installment_ids": []}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_check_and_complete_expense_when_all_paid(
        self, authenticated_api_client, installment_expense, admin_user
    ):
        """Covers _check_and_complete_expense: all installments paid marks expense paid."""
        inst = ExpenseInstallment.objects.create(
            expense=installment_expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("600.00"),
            due_date=date(2026, 4, 17),
            created_by=admin_user,
            updated_by=admin_user,
        )
        url = f"/api/expense-installments/{inst.pk}/mark_paid/"
        response = authenticated_api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        installment_expense.refresh_from_db()
        assert installment_expense.is_paid is True


# =============================================================================
# IncomeViewSet — mark_received and filter branches (lines 405, 409, etc.)
# =============================================================================


@pytest.mark.integration
class TestIncomeFilters:
    url = "/api/incomes/"

    def test_filter_by_is_recurring(self, authenticated_api_client, income):
        response = authenticated_api_client.get(f"{self.url}?is_recurring=false")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_is_received(self, authenticated_api_client, income):
        response = authenticated_api_client.get(f"{self.url}?is_received=false")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_date_from(self, authenticated_api_client, income):
        response = authenticated_api_client.get(f"{self.url}?date_from=2026-03-01")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_date_to(self, authenticated_api_client, income):
        response = authenticated_api_client.get(f"{self.url}?date_to=2026-03-31")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_category_id_no_match(self, authenticated_api_client, income):
        response = authenticated_api_client.get(f"{self.url}?category_id=999")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_mark_received_action(self, authenticated_api_client, income):
        """Covers line 429-437: mark_received action."""
        url = f"{self.url}{income.pk}/mark_received/"
        response = authenticated_api_client.post(
            url, {"received_date": "2026-03-06"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        income.refresh_from_db()
        assert income.is_received is True
        assert str(income.received_date) == "2026-03-06"


# =============================================================================
# EmployeePaymentViewSet — filter branches (lines 501, 509, 513)
# =============================================================================


@pytest.mark.integration
class TestEmployeePaymentFilters:
    url = "/api/employee-payments/"

    def test_filter_by_reference_month(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?reference_month=2026-03-01")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_is_paid(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?is_paid=false")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_month_range(self, authenticated_api_client):
        response = authenticated_api_client.get(
            f"{self.url}?month_from=2026-01-01&month_to=2026-06-01"
        )
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# PersonPaymentViewSet — filter branches (lines 561-581)
# =============================================================================


@pytest.mark.integration
class TestPersonPaymentFilters:
    url = "/api/person-payments/"

    def test_filter_by_reference_month(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?reference_month=2026-03-01")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_month_range(self, authenticated_api_client):
        response = authenticated_api_client.get(
            f"{self.url}?month_from=2026-01-01&month_to=2026-06-01"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_person_id(self, authenticated_api_client, person):
        response = authenticated_api_client.get(f"{self.url}?person_id={person.pk}")
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# PersonIncomeViewSet — filter branches (lines 551)
# =============================================================================


@pytest.mark.integration
class TestPersonIncomeFilters:
    url = "/api/person-incomes/"

    def test_filter_by_apartment_id(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?apartment_id=999")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_filter_by_is_active(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?is_active=true")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_income_type(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?income_type=rent")
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# RentPaymentViewSet — filter branches (lines 465, 477, 481)
# =============================================================================


@pytest.mark.integration
class TestRentPaymentFilters:
    url = "/api/rent-payments/"

    def test_filter_by_reference_month(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.url}?reference_month=2026-03-01")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_month_range(self, authenticated_api_client):
        response = authenticated_api_client.get(
            f"{self.url}?month_from=2026-01-01&month_to=2026-06-01"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_payment_date_range(self, authenticated_api_client):
        response = authenticated_api_client.get(
            f"{self.url}?payment_date_from=2026-03-01&payment_date_to=2026-03-31"
        )
        assert response.status_code == status.HTTP_200_OK
