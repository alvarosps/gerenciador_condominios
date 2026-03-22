"""Integration tests for CashFlowViewSet endpoints."""

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
    Lease,
    Person,
    Tenant,
)


@pytest.fixture
def person_cf(admin_user):
    return Person.objects.create(
        name="Carlos Fluxo",
        relationship="Proprietário",
        phone="11999997777",
        email="carlos_cf@test.com",
        is_owner=True,
        is_employee=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def building_cf(admin_user):
    return Building.objects.create(
        street_number=7700,
        name="Edifício Cash Flow",
        address="Rua Fluxo, 7700",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant_cf(admin_user):
    return Tenant.objects.create(
        name="Inquilino Fluxo",
        cpf_cnpj="71428793860",
        phone="11988886666",
        marital_status="Solteiro(a)",
        profession="Analista",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_cf(building_cf, admin_user):
    return Apartment.objects.create(
        building=building_cf,
        number=701,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
        is_rented=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease_cf(apartment_cf, tenant_cf, admin_user):
    return Lease.objects.create(
        apartment=apartment_cf,
        responsible_tenant=tenant_cf,
        rental_value=Decimal("1500.00"),
        due_day=10,
        start_date=date(2026, 1, 1),
        validity_months=12,
        cleaning_fee=Decimal("200.00"),
        tag_fee=Decimal("50.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def installment_expense_cf(person_cf, admin_user):
    expense = Expense.objects.create(
        description="Empréstimo Fluxo",
        expense_type="bank_loan",
        total_amount=Decimal("6000.00"),
        expense_date=date(2026, 1, 1),
        person=person_cf,
        bank_name="Banco Fluxo",
        interest_rate=Decimal("1.00"),
        is_installment=True,
        total_installments=6,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )
    for i in range(1, 7):
        month = 3 + i
        year = 2026
        if month > 12:
            month -= 12
            year = 2027
        ExpenseInstallment.objects.create(
            expense=expense,
            installment_number=i,
            total_installments=6,
            amount=Decimal("1000.00"),
            due_date=date(year, month, 10),
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
    return expense


@pytest.mark.integration
@pytest.mark.django_db
class TestCashFlowAPI:
    monthly_url = "/api/cash-flow/monthly/"
    projection_url = "/api/cash-flow/projection/"
    person_summary_url = "/api/cash-flow/person_summary/"
    simulate_url = "/api/cash-flow/simulate/"

    @freeze_time("2026-03-22")
    def test_monthly_endpoint(self, authenticated_api_client, lease_cf):
        response = authenticated_api_client.get(self.monthly_url, {"year": "2026", "month": "3"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["year"] == 2026
        assert response.data["month"] == 3
        assert "income" in response.data
        assert "expenses" in response.data
        assert "balance" in response.data

    @freeze_time("2026-03-22")
    def test_projection_endpoint(self, authenticated_api_client):
        response = authenticated_api_client.get(self.projection_url, {"months": "6"})
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 6

    @freeze_time("2026-03-22")
    def test_person_summary_endpoint(self, authenticated_api_client, person_cf):
        response = authenticated_api_client.get(
            self.person_summary_url,
            {"person_id": person_cf.pk, "year": "2026", "month": "3"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "person_name" in response.data
        assert response.data["person_name"] == "Carlos Fluxo"

    @freeze_time("2026-03-22")
    def test_simulate_endpoint(self, authenticated_api_client, installment_expense_cf):
        body = {"scenarios": [{"type": "pay_off_early", "expense_id": installment_expense_cf.pk}]}
        response = authenticated_api_client.post(self.simulate_url, body, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "base" in response.data
        assert "simulated" in response.data
        assert "comparison" in response.data

    @freeze_time("2026-03-22")
    def test_simulate_pay_off_early(self, authenticated_api_client, installment_expense_cf):
        body = {"scenarios": [{"type": "pay_off_early", "expense_id": installment_expense_cf.pk}]}
        response = authenticated_api_client.post(self.simulate_url, body, format="json")
        assert response.status_code == status.HTTP_200_OK

        base = response.data["base"]
        simulated = response.data["simulated"]
        comparison = response.data["comparison"]

        assert len(base) == len(simulated)
        assert "month_by_month" in comparison
        assert "total_impact_12m" in comparison
        assert "break_even_month" in comparison

        # Simulated expenses should be lower or equal in all months (paying off removes installments)
        for base_month, sim_month in zip(base, simulated, strict=True):
            assert sim_month["expenses_total"] <= base_month["expenses_total"]

    @freeze_time("2026-03-22")
    def test_simulate_multiple_scenarios(self, authenticated_api_client, installment_expense_cf):
        body = {
            "scenarios": [
                {"type": "pay_off_early", "expense_id": installment_expense_cf.pk},
                {"type": "add_fixed_expense", "amount": "500.00"},
            ]
        }
        response = authenticated_api_client.post(self.simulate_url, body, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "base" in response.data
        assert "simulated" in response.data

    def test_simulate_invalid_scenario(self, authenticated_api_client):
        body = {"scenarios": [{"type": "invalid_type"}]}
        response = authenticated_api_client.post(self.simulate_url, body, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "errors" in response.data

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(self.monthly_url, {"year": "2026", "month": "3"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_monthly_missing_params(self, authenticated_api_client):
        response = authenticated_api_client.get(self.monthly_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_monthly_missing_month(self, authenticated_api_client):
        response = authenticated_api_client.get(self.monthly_url, {"year": "2026"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_person_summary_missing_person(self, authenticated_api_client):
        response = authenticated_api_client.get(
            self.person_summary_url, {"year": "2026", "month": "3"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
