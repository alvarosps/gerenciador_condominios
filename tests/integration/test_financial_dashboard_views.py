"""Integration tests for CashFlow, DailyControl, and extended FinancialDashboard views."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import (
    Apartment,
    Building,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    Income,
    Lease,
    Person,
    RentPayment,
    Tenant,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def building(admin_user) -> Building:
    return Building.objects.create(
        street_number=801, name="Dashboard Views", address="Rua DV, 801",
        created_by=admin_user, updated_by=admin_user
    )


@pytest.fixture
def apartment(building: Building, admin_user) -> Apartment:
    return Apartment.objects.create(
        building=building, number=101, rental_value=Decimal("1500.00"), max_tenants=2,
        created_by=admin_user, updated_by=admin_user
    )


@pytest.fixture
def tenant(admin_user) -> Tenant:
    return Tenant.objects.create(
        name="DV Tenant",
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
    )


@pytest.fixture
def person(admin_user) -> Person:
    return Person.objects.create(
        name="DV Person", relationship="Filho",
        created_by=admin_user, updated_by=admin_user
    )


# =============================================================================
# CashFlowViewSet — /api/cash-flow/
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestCashFlowMonthlyView:
    base_url = "/api/cash-flow"

    def test_monthly_requires_year_and_month(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/monthly/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "year" in response.data["error"].lower() or "month" in response.data["error"].lower()

    def test_monthly_invalid_params_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/monthly/?year=abc&month=3")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_monthly_invalid_month_range_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/monthly/?year=2026&month=13")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_monthly_valid_returns_200(self, authenticated_api_client, lease: Lease) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/monthly/?year=2026&month=3")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "income" in data
        assert "expenses" in data
        assert "balance" in data

    def test_monthly_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.get(f"{self.base_url}/monthly/?year=2026&month=3")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestCashFlowProjectionView:
    base_url = "/api/cash-flow"

    @freeze_time("2026-03-15")
    def test_projection_returns_200(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/projection/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    @freeze_time("2026-03-15")
    def test_projection_custom_months(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/projection/?months=6")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 6

    def test_projection_invalid_months_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/projection/?months=abc")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_projection_zero_months_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/projection/?months=0")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_projection_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.get(f"{self.base_url}/projection/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestCashFlowPersonSummaryView:
    base_url = "/api/cash-flow"

    def test_person_summary_missing_person_id_returns_400(
        self, authenticated_api_client
    ) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/person_summary/?year=2026&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_person_summary_missing_year_returns_400(
        self, authenticated_api_client, person: Person
    ) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/person_summary/?person_id={person.pk}&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_person_summary_invalid_types_returns_400(
        self, authenticated_api_client
    ) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/person_summary/?person_id=abc&year=2026&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_person_summary_not_found_returns_404(
        self, authenticated_api_client
    ) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/person_summary/?person_id=999999&year=2026&month=3"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_person_summary_valid_returns_200(
        self, authenticated_api_client, person: Person
    ) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/person_summary/?person_id={person.pk}&year=2026&month=3"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "person_name" in data
        assert "net_amount" in data

    def test_person_summary_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.get(f"{self.base_url}/person_summary/?person_id=1&year=2026&month=3")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestCashFlowSimulateView:
    base_url = "/api/cash-flow"

    @freeze_time("2026-03-15")
    def test_simulate_requires_scenarios(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(f"{self.base_url}/simulate/", {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-15")
    def test_simulate_empty_scenarios_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/simulate/", {"scenarios": []}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-15")
    def test_simulate_invalid_type_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/simulate/",
            {"scenarios": [{"type": "invalid_type"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @freeze_time("2026-03-15")
    def test_simulate_valid_scenario_returns_200(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/simulate/",
            {
                "scenarios": [
                    {
                        "type": "add_fixed_expense",
                        "amount": "200.00",
                        "description": "New Streaming",
                    }
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "base" in response.data
        assert "simulated" in response.data
        assert "comparison" in response.data

    def test_simulate_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.post(f"{self.base_url}/simulate/", {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# DailyControlViewSet — /api/daily-control/
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestDailyControlBreakdownView:
    base_url = "/api/daily-control"

    def test_breakdown_returns_200(self, authenticated_api_client, lease: Lease) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/breakdown/?year=2026&month=3")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 31  # March has 31 days

    def test_breakdown_invalid_params_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/breakdown/?year=abc&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_breakdown_invalid_month_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/breakdown/?year=2026&month=13"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_breakdown_defaults_to_current_month(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/breakdown/")
        assert response.status_code == status.HTTP_200_OK

    def test_breakdown_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.get(f"{self.base_url}/breakdown/?year=2026&month=3")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_breakdown_entry_has_expected_keys(
        self, authenticated_api_client, lease: Lease
    ) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/breakdown/?year=2026&month=3")
        assert response.status_code == status.HTTP_200_OK
        day = response.data[0]
        assert "date" in day
        assert "day_of_week" in day
        assert "entries" in day
        assert "exits" in day
        assert "cumulative_balance" in day


@pytest.mark.integration
@pytest.mark.django_db
class TestDailyControlSummaryView:
    base_url = "/api/daily-control"

    @freeze_time("2026-03-15")
    def test_summary_returns_200(self, authenticated_api_client, lease: Lease) -> None:
        response = authenticated_api_client.get(f"{self.base_url}/summary/?year=2026&month=3")
        assert response.status_code == status.HTTP_200_OK

    def test_summary_invalid_month_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/summary/?year=2026&month=0"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_summary_invalid_params_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/summary/?year=notanint&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_summary_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.get(f"{self.base_url}/summary/?year=2026&month=3")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.integration
@pytest.mark.django_db
class TestDailyControlMarkPaidView:
    base_url = "/api/daily-control"

    def test_mark_paid_missing_fields_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/", {}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_missing_payment_date_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "expense", "item_id": 1},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_invalid_item_id_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "expense", "item_id": "notanint", "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_invalid_date_format_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "expense", "item_id": 1, "payment_date": "not-a-date"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_nonexistent_item_returns_404(self, authenticated_api_client) -> None:
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "expense", "item_id": 999999, "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_paid_invalid_type_returns_400(self, authenticated_api_client) -> None:
        expense = Expense.objects.create(
            description="Mark Test",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 3, 1),
        )
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "invalid", "item_id": expense.pk, "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_mark_paid_expense_returns_200(self, authenticated_api_client) -> None:
        expense = Expense.objects.create(
            description="Mark Expense DV",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 3, 1),
        )
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "expense", "item_id": expense.pk, "payment_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        expense.refresh_from_db()
        assert expense.is_paid is True

    def test_mark_paid_income_returns_200(self, authenticated_api_client) -> None:
        income = Income.objects.create(
            description="Mark Income DV",
            amount=Decimal("1000.00"),
            income_date=date(2026, 3, 5),
        )
        response = authenticated_api_client.post(
            f"{self.base_url}/mark_paid/",
            {"item_type": "income", "item_id": income.pk, "payment_date": "2026-03-05"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        income.refresh_from_db()
        assert income.is_received is True

    def test_mark_paid_unauthenticated_returns_401(self, api_client) -> None:
        response = api_client.post(f"{self.base_url}/mark_paid/", {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# FinancialDashboardViewSet — extended coverage
# =============================================================================


@pytest.mark.integration
@pytest.mark.django_db
class TestFinancialDashboardSummary:
    base_url = "/api/financial-dashboard"

    def test_dashboard_summary_valid_returns_200(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/dashboard_summary/?year=2026&month=3"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_summary_invalid_params_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/dashboard_summary/?year=abc&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expense_detail_missing_type_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/expense_detail/?year=2026&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expense_detail_invalid_params_returns_400(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/expense_detail/?type=card&year=abc&month=3"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_expense_detail_valid_type_returns_200(self, authenticated_api_client) -> None:
        response = authenticated_api_client.get(
            f"{self.base_url}/expense_detail/?type=card&year=2026&month=3"
        )
        assert response.status_code == status.HTTP_200_OK
