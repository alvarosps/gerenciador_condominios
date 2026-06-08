"""Integration tests for previously-untested financial dashboard + person-payment-schedule endpoints.

Real admin API calls (no internal mocks) exercising the view layer and the underlying services
(FinancialDashboardService.get_dashboard_summary / get_monthly_purchases / get_expense_detail and
PersonPaymentScheduleService.bulk_configure / get_person_month_total).
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import Expense, ExpenseInstallment, Person, PersonPayment


@pytest.fixture
def person(admin_user):
    return Person.objects.create(
        name="Pessoa Extended",
        relationship="Proprietário",
        phone="11900001111",
        is_owner=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def expense(person, admin_user):
    return Expense.objects.create(
        description="Compra mensal",
        expense_type="one_time_expense",
        total_amount=Decimal("300.00"),
        expense_date=date(2026, 3, 10),
        person=person,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestFinancialDashboardSummaryEndpoints:
    def test_dashboard_summary_returns_200(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/dashboard_summary/", {"year": 2026, "month": 3}
        )
        assert response.status_code == 200

    def test_dashboard_summary_invalid_params_400(self, authenticated_api_client):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/dashboard_summary/", {"year": "abc", "month": 3}
        )
        assert response.status_code == 400

    def test_monthly_purchases_returns_200(self, authenticated_api_client, expense):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/monthly_purchases/", {"year": 2026, "month": 3}
        )
        assert response.status_code == 200

    def test_monthly_purchases_invalid_params_400(self, authenticated_api_client):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/monthly_purchases/", {"year": "x", "month": "y"}
        )
        assert response.status_code == 400

    def test_expense_detail_missing_type_400(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/financial-dashboard/expense_detail/")
        assert response.status_code == 400

    def test_expense_detail_invalid_id_400(self, authenticated_api_client):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/expense_detail/", {"type": "person", "id": "notint"}
        )
        assert response.status_code == 400

    def test_expense_detail_person_returns_200(self, authenticated_api_client, person, expense):
        response = authenticated_api_client.get(
            "/api/financial-dashboard/expense_detail/",
            {"type": "person", "id": person.pk, "year": 2026, "month": 3},
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestPersonPaymentScheduleEndpoints:
    def test_bulk_configure_missing_fields_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/person-payment-schedules/bulk_configure/", {}, format="json"
        )
        assert response.status_code == 400

    def test_bulk_configure_month_not_first_day_400(self, authenticated_api_client, person):
        response = authenticated_api_client.post(
            "/api/person-payment-schedules/bulk_configure/",
            {"person_id": person.pk, "reference_month": "2026-03-15", "entries": []},
            format="json",
        )
        assert response.status_code == 400

    def test_bulk_configure_person_not_found_404(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/person-payment-schedules/bulk_configure/",
            {"person_id": 999999, "reference_month": "2026-03-01", "entries": []},
            format="json",
        )
        assert response.status_code == 404

    def test_bulk_configure_success_200(self, authenticated_api_client, person):
        response = authenticated_api_client.post(
            "/api/person-payment-schedules/bulk_configure/",
            {
                "person_id": person.pk,
                "reference_month": "2026-03-01",
                "entries": [{"due_day": 10, "amount": "500.00"}],
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["total_configured"] == 1

    def test_person_month_total_missing_params_400(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/person-payment-schedules/person_month_total/")
        assert response.status_code == 400

    def test_person_month_total_person_not_found_404(self, authenticated_api_client):
        response = authenticated_api_client.get(
            "/api/person-payment-schedules/person_month_total/",
            {"person_id": 999999, "reference_month": "2026-03-01"},
        )
        assert response.status_code == 404

    def test_person_month_total_success_200(self, authenticated_api_client, person):
        response = authenticated_api_client.get(
            "/api/person-payment-schedules/person_month_total/",
            {"person_id": person.pk, "reference_month": "2026-03-01"},
        )
        assert response.status_code == 200
        assert "net_total" in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestDailyControlMarkPaid:
    def test_mark_person_schedule_success(self, authenticated_api_client, person):
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "person_schedule",
                "payment_date": "2026-03-10",
                "person_id": person.pk,
                "amount": "500.00",
                "year": 2026,
                "month": 3,
            },
            format="json",
        )
        assert response.status_code == 200
        assert PersonPayment.objects.filter(person=person, amount=Decimal("500.00")).exists()

    def test_mark_person_schedule_missing_fields_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {"item_type": "person_schedule", "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == 400

    def test_mark_person_schedule_person_not_found_404(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {
                "item_type": "person_schedule",
                "payment_date": "2026-03-10",
                "person_id": 999999,
                "amount": "500.00",
                "year": 2026,
                "month": 3,
            },
            format="json",
        )
        assert response.status_code == 404

    def test_mark_standard_missing_item_id_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {"item_type": "installment", "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == 400

    def test_mark_standard_invalid_item_id_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {"item_type": "installment", "item_id": "notint", "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == 400

    def test_mark_standard_installment_success(self, authenticated_api_client, person, admin_user):
        expense = Expense.objects.create(
            description="Parcelado",
            expense_type="card_purchase",
            total_amount=Decimal("600.00"),
            expense_date=date(2026, 3, 5),
            person=person,
            is_installment=True,
            total_installments=2,
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=1,
            total_installments=2,
            amount=Decimal("300.00"),
            due_date=date(2026, 3, 20),
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = authenticated_api_client.post(
            "/api/daily-control/mark_paid/",
            {"item_type": "installment", "item_id": inst.pk, "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == 200
        inst.refresh_from_db()
        assert inst.is_paid is True
