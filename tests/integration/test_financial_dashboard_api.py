"""Integration tests for FinancialDashboardViewSet endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import (
    CreditCard,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    Person,
)


@pytest.fixture
def person(admin_user):
    return Person.objects.create(
        name="Carlos Dashboard",
        relationship="Proprietário",
        phone="11911112222",
        email="carlos_dashboard@test.com",
        is_owner=True,
        is_employee=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def credit_card(person, admin_user):
    return CreditCard.objects.create(
        person=person,
        nickname="Itaú",
        last_four_digits="5678",
        closing_day=10,
        due_day=20,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category(admin_user):
    return ExpenseCategory.objects.create(
        name="Alimentação Dashboard",
        description="Gastos com alimentação",
        color="#33A1FF",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def card_expense(person, credit_card, category, admin_user):
    return Expense.objects.create(
        description="Compra supermercado",
        expense_type="card_purchase",
        total_amount=Decimal("600.00"),
        expense_date=date(2026, 3, 5),
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
def expense_with_upcoming_installments(card_expense, admin_user):
    """Three installments: due 2026-03-22, 2026-04-20, 2026-05-20."""
    due_dates = [date(2026, 3, 22), date(2026, 4, 20), date(2026, 5, 20)]
    for i, due_date in enumerate(due_dates, start=1):
        ExpenseInstallment.objects.create(
            expense=card_expense,
            installment_number=i,
            total_installments=3,
            amount=Decimal("200.00"),
            due_date=due_date,
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
    return card_expense


@pytest.fixture
def expense_with_overdue_installments(person, category, admin_user):
    """Expense with two installments already overdue (due in January 2026)."""
    loan_expense = Expense.objects.create(
        description="Empréstimo vencido",
        expense_type="bank_loan",
        total_amount=Decimal("2000.00"),
        expense_date=date(2026, 1, 1),
        person=person,
        bank_name="Bradesco",
        interest_rate=Decimal("2.00"),
        is_installment=True,
        total_installments=2,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )
    for i in range(1, 3):
        ExpenseInstallment.objects.create(
            expense=loan_expense,
            installment_number=i,
            total_installments=2,
            amount=Decimal("1000.00"),
            due_date=date(2026, 1, i * 10),
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
    return loan_expense


@pytest.fixture
def category_expense(category, person, admin_user):
    """A simple expense in March 2026 linked to category, for category_breakdown."""
    return Expense.objects.create(
        description="Almoço restaurante",
        expense_type="one_time_expense",
        total_amount=Decimal("150.00"),
        expense_date=date(2026, 3, 10),
        person=person,
        category=category,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestFinancialDashboardAPI:
    base_url = "/api/financial-dashboard"

    def test_overview_endpoint(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.base_url}/overview/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "current_month_balance" in data
        assert "current_month_income" in data
        assert "current_month_expenses" in data
        assert "total_debt" in data
        assert "total_monthly_obligations" in data
        assert "total_monthly_income" in data
        assert "months_until_break_even" in data

    def test_debt_by_person_endpoint(
        self, authenticated_api_client, expense_with_upcoming_installments
    ):
        response = authenticated_api_client.get(f"{self.base_url}/debt_by_person/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_debt_by_person_contains_expected_keys(
        self, authenticated_api_client, expense_with_upcoming_installments
    ):
        response = authenticated_api_client.get(f"{self.base_url}/debt_by_person/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        entry = response.data[0]
        assert "person_id" in entry
        assert "person_name" in entry
        assert "card_debt" in entry
        assert "loan_debt" in entry
        assert "total_debt" in entry
        assert "monthly_card" in entry
        assert "monthly_loan" in entry
        assert "cards_count" in entry

    def test_debt_by_type_endpoint(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.base_url}/debt_by_type/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "card_purchases" in data
        assert "bank_loans" in data
        assert "personal_loans" in data
        assert "water_debt" in data
        assert "electricity_debt" in data
        assert "property_tax_debt" in data
        assert "total" in data

    @freeze_time("2026-03-22")
    def test_upcoming_installments_endpoint(
        self, authenticated_api_client, expense_with_upcoming_installments
    ):
        response = authenticated_api_client.get(f"{self.base_url}/upcoming_installments/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    @freeze_time("2026-03-22")
    def test_upcoming_installments_default_window_contains_near_due(
        self, authenticated_api_client, expense_with_upcoming_installments
    ):
        # Default window is 30 days: 2026-03-22 to 2026-04-21
        # Installments due 2026-03-22 and 2026-04-20 should appear; 2026-05-20 should not
        response = authenticated_api_client.get(f"{self.base_url}/upcoming_installments/")
        assert response.status_code == status.HTTP_200_OK
        due_dates = [str(item["due_date"]) for item in response.data]
        assert "2026-03-22" in due_dates
        assert "2026-04-20" in due_dates
        assert "2026-05-20" not in due_dates

    @freeze_time("2026-03-22")
    def test_upcoming_installments_custom_days(
        self, authenticated_api_client, expense_with_upcoming_installments
    ):
        # With ?days=7 only the installment due on 2026-03-22 should appear
        response = authenticated_api_client.get(f"{self.base_url}/upcoming_installments/?days=7")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        due_dates = [str(item["due_date"]) for item in response.data]
        assert "2026-04-20" not in due_dates

    def test_upcoming_installments_invalid_days(self, authenticated_api_client):
        response = authenticated_api_client.get(f"{self.base_url}/upcoming_installments/?days=abc")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-22")
    def test_overdue_installments_endpoint(
        self, authenticated_api_client, expense_with_overdue_installments
    ):
        response = authenticated_api_client.get(f"{self.base_url}/overdue_installments/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 2

    @freeze_time("2026-03-22")
    def test_overdue_installments_contain_expected_keys(
        self, authenticated_api_client, expense_with_overdue_installments
    ):
        response = authenticated_api_client.get(f"{self.base_url}/overdue_installments/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        entry = response.data[0]
        assert "id" in entry
        assert "expense_description" in entry
        assert "expense_type" in entry
        assert "amount" in entry
        assert "due_date" in entry
        assert "days_overdue" in entry

    def test_category_breakdown_endpoint(self, authenticated_api_client, category_expense):
        response = authenticated_api_client.get(
            f"{self.base_url}/category_breakdown/?year=2026&month=3"
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_category_breakdown_contains_expected_keys(
        self, authenticated_api_client, category_expense
    ):
        response = authenticated_api_client.get(
            f"{self.base_url}/category_breakdown/?year=2026&month=3"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        entry = response.data[0]
        assert "category_name" in entry
        assert "color" in entry
        assert "total" in entry
        assert "percentage" in entry
        assert "count" in entry

    def test_category_breakdown_empty_month(self, authenticated_api_client):
        # Month with no expenses returns empty list
        response = authenticated_api_client.get(
            f"{self.base_url}/category_breakdown/?year=2020&month=1"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_category_breakdown_invalid_params(self, authenticated_api_client):
        response = authenticated_api_client.get(
            f"{self.base_url}/category_breakdown/?year=abc&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, api_client):
        # DRF returns 401 when no credentials are provided (WWW-Authenticate challenge)
        endpoints = [
            f"{self.base_url}/overview/",
            f"{self.base_url}/debt_by_person/",
            f"{self.base_url}/debt_by_type/",
            f"{self.base_url}/upcoming_installments/",
            f"{self.base_url}/overdue_installments/",
            f"{self.base_url}/category_breakdown/?year=2026&month=3",
        ]
        for url in endpoints:
            response = api_client.get(url)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Expected 401 for {url}, got {response.status_code}"
            )
