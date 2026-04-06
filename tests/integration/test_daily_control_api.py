"""Integration tests for DailyControlViewSet — breakdown, summary, mark_paid."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Expense, ExpenseInstallment, Income, Person


@pytest.fixture
def person(admin_user):
    return Person.objects.create(
        name="Rodrigo Daily Control",
        relationship="Proprietário",
        phone="11999998001",
        is_owner=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def installment(person, admin_user):
    expense = Expense.objects.create(
        description="Parcela TV",
        expense_type="installment_expense",
        total_amount=Decimal("600.00"),
        expense_date=date(2026, 3, 1),
        person=person,
        is_installment=True,
        total_installments=3,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )
    return ExpenseInstallment.objects.create(
        expense=expense,
        installment_number=1,
        total_installments=3,
        amount=Decimal("200.00"),
        due_date=date(2026, 3, 15),
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def one_time_expense(person, admin_user):
    return Expense.objects.create(
        description="Material de limpeza",
        expense_type="one_time_expense",
        total_amount=Decimal("150.00"),
        expense_date=date(2026, 3, 10),
        person=person,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def income_obj(person, admin_user):
    return Income.objects.create(
        description="Receita extra março",
        amount=Decimal("300.00"),
        income_date=date(2026, 3, 5),
        person=person,
        is_recurring=False,
        is_received=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
class TestDailyControlBreakdown:
    url = "/api/daily-control/breakdown/"

    def test_breakdown_returns_days_list(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 31  # March has 31 days

    def test_breakdown_day_structure(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        first_day = response.data[0]
        assert "date" in first_day
        assert "day_of_week" in first_day
        assert "entries" in first_day
        assert "exits" in first_day
        assert "total_entries" in first_day
        assert "total_exits" in first_day
        assert "day_balance" in first_day
        assert "cumulative_balance" in first_day

    def test_breakdown_includes_installment_in_exits(
        self, authenticated_api_client, installment
    ):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        # Day 15 is index 14
        day_15 = response.data[14]
        exit_types = [e["type"] for e in day_15["exits"]]
        assert "installment" in exit_types

    def test_breakdown_includes_income_in_entries(
        self, authenticated_api_client, income_obj
    ):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        # Day 5 is index 4
        day_5 = response.data[4]
        entry_types = [e["type"] for e in day_5["entries"]]
        assert "income" in entry_types

    def test_breakdown_invalid_month_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 13})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_breakdown_non_integer_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": "abc", "month": 3})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_breakdown_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestDailyControlSummary:
    url = "/api/daily-control/summary/"

    def test_summary_returns_expected_fields(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_expected_income" in data
        assert "total_received_income" in data
        assert "total_expected_expenses" in data
        assert "total_paid_expenses" in data
        assert "overdue_count" in data
        assert "overdue_total" in data
        assert "current_balance" in data
        assert "projected_balance" in data

    def test_summary_expense_totals_include_installment(
        self, authenticated_api_client, installment
    ):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_200_OK
        assert float(response.data["total_expected_expenses"]) >= 200.0

    def test_summary_invalid_month_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(self.url, {"year": 2026, "month": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_summary_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.url, {"year": 2026, "month": 3})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
class TestDailyControlMarkPaid:
    url = "/api/daily-control/mark_paid/"

    def test_mark_installment_paid(self, authenticated_api_client, installment):
        payload = {
            "item_type": "installment",
            "item_id": installment.id,
            "payment_date": "2026-03-15",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

        installment.refresh_from_db()
        assert installment.is_paid is True
        assert str(installment.paid_date) == "2026-03-15"

    def test_mark_expense_paid(self, authenticated_api_client, one_time_expense):
        payload = {
            "item_type": "expense",
            "item_id": one_time_expense.id,
            "payment_date": "2026-03-10",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

        one_time_expense.refresh_from_db()
        assert one_time_expense.is_paid is True

    def test_mark_income_received(self, authenticated_api_client, income_obj):
        payload = {
            "item_type": "income",
            "item_id": income_obj.id,
            "payment_date": "2026-03-05",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

        income_obj.refresh_from_db()
        assert income_obj.is_received is True

    def test_mark_already_paid_returns_already_paid_status(
        self, authenticated_api_client, installment
    ):
        installment.is_paid = True
        installment.paid_date = date(2026, 3, 15)
        installment.save(update_fields=["is_paid", "paid_date", "updated_at"])

        payload = {
            "item_type": "installment",
            "item_id": installment.id,
            "payment_date": "2026-03-15",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "already_paid"

    def test_mark_paid_invalid_item_type_returns_400(self, authenticated_api_client):
        payload = {
            "item_type": "unknown",
            "item_id": 1,
            "payment_date": "2026-03-15",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_nonexistent_id_returns_404(self, authenticated_api_client):
        payload = {
            "item_type": "installment",
            "item_id": 999999,
            "payment_date": "2026-03-15",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_paid_missing_fields_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_missing_payment_date_returns_400(
        self, authenticated_api_client, installment
    ):
        payload = {"item_type": "installment", "item_id": installment.id}
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
