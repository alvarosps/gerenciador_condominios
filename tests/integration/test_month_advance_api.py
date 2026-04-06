"""Integration tests for MonthAdvanceViewSet API endpoints.

Tests all endpoints: advance, rollback, get_status, snapshots, snapshot_detail, preview.
Uses real database and DRF APIClient — no internal code is mocked.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import (
    Apartment,
    Building,
    FinancialSettings,
    Lease,
    MonthSnapshot,
    Tenant,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=9901,
        name="Edifício API Test",
        address="Rua API, 9901",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=201,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Inquilino API Test",
        cpf_cnpj="11144477735",
        is_company=False,
        phone="11977770088",
        marital_status="Solteiro(a)",
        profession="Desenvolvedor",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def active_lease(apartment, tenant, admin_user):
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=24,
        tag_fee=Decimal("80.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def financial_settings(admin_user):
    return FinancialSettings.objects.create(
        initial_balance=Decimal("500.00"),
        initial_balance_date=date(2026, 1, 1),
        updated_by=admin_user,
    )


@pytest.fixture
def finalized_jan_snapshot(active_lease, financial_settings, authenticated_api_client):
    """Creates a finalized snapshot for 2026-01 via the API (force=True)."""
    response = authenticated_api_client.post(
        "/api/month-advance/advance/",
        {"year": 2026, "month": 1, "force": True, "notes": "Test Jan"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    return MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))


# ---------------------------------------------------------------------------
# TestMonthAdvanceAPI
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMonthAdvanceAPI:
    advance_url = "/api/month-advance/advance/"
    rollback_url = "/api/month-advance/rollback/"
    status_url = "/api/month-advance/get_status/"
    snapshots_url = "/api/month-advance/snapshots/"
    preview_url = "/api/month-advance/preview/"

    # --- advance ---

    def test_advance_endpoint_creates_snapshot(
        self, authenticated_api_client, active_lease, financial_settings
    ):
        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["success"] is True
        assert "snapshot_id" in data
        assert "summary" in data
        assert MonthSnapshot.objects.filter(reference_month=date(2026, 1, 1)).exists()

    def test_advance_endpoint_returns_warnings_without_force(
        self, authenticated_api_client, active_lease
    ):
        # Has active lease with unpaid rent → should return 400 without force
        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "force" in response.data["error"].lower()

    def test_advance_endpoint_missing_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_advance_endpoint_second_call_returns_400(
        self, authenticated_api_client, active_lease, financial_settings
    ):
        authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True},
            format="json",
        )

        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "já foi finalizado" in response.data["error"]

    # --- rollback ---

    def test_rollback_endpoint(self, authenticated_api_client, finalized_jan_snapshot):
        response = authenticated_api_client.post(
            self.rollback_url,
            {"year": 2026, "month": 1, "confirm": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["success"] is True
        assert data["details"]["snapshot_deleted"] is True
        assert not MonthSnapshot.objects.filter(reference_month=date(2026, 1, 1)).exists()

    def test_rollback_without_confirm_returns_400(
        self, authenticated_api_client, finalized_jan_snapshot
    ):
        response = authenticated_api_client.post(
            self.rollback_url,
            {"year": 2026, "month": 1, "confirm": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirm=True" in response.data["error"]

    def test_rollback_missing_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.post(
            self.rollback_url,
            {"confirm": True},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- get_status ---

    def test_status_endpoint(self, authenticated_api_client, active_lease):
        response = authenticated_api_client.get(self.status_url, {"year": 2026, "month": 1})

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["year"] == 2026
        assert data["month"] == 1
        assert data["is_finalized"] is False
        assert "validation" in data

    def test_status_endpoint_finalized(self, authenticated_api_client, finalized_jan_snapshot):
        response = authenticated_api_client.get(self.status_url, {"year": 2026, "month": 1})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_finalized"] is True
        assert response.data["snapshot_id"] == finalized_jan_snapshot.pk

    def test_status_endpoint_missing_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(self.status_url, {"year": 2026})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # --- snapshots list ---

    def test_snapshots_list_endpoint(self, authenticated_api_client, finalized_jan_snapshot):
        response = authenticated_api_client.get(self.snapshots_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1
        first = response.data[0]
        assert "id" in first
        assert "reference_month" in first
        assert "total_income" in first
        assert "total_expenses" in first
        assert "net_balance" in first
        assert "is_finalized" in first

    def test_snapshots_list_filtered_by_year(
        self, authenticated_api_client, finalized_jan_snapshot
    ):
        response = authenticated_api_client.get(self.snapshots_url, {"year": 2026})

        assert response.status_code == status.HTTP_200_OK
        assert all(item["reference_month"].startswith("2026") for item in response.data)

    def test_snapshots_list_empty_when_none_exist(self, authenticated_api_client):
        response = authenticated_api_client.get(self.snapshots_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    # --- snapshot detail ---

    def test_snapshot_detail_endpoint(self, authenticated_api_client, finalized_jan_snapshot):
        response = authenticated_api_client.get("/api/month-advance/snapshots/2026/1/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["id"] == finalized_jan_snapshot.pk
        assert "detailed_breakdown" in data
        assert "cumulative_ending_balance" in data

    def test_snapshot_detail_not_found_returns_404(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/month-advance/snapshots/2020/1/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data

    # --- preview ---

    def test_preview_endpoint(self, authenticated_api_client):
        response = authenticated_api_client.get(self.preview_url, {"year": 2026, "month": 1})

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["year"] == 2026
        assert data["month"] == 2
        assert "upcoming_installments_count" in data
        assert "expected_rent_count" in data
        assert "reminders" in data

    def test_preview_endpoint_missing_params_returns_400(self, authenticated_api_client):
        response = authenticated_api_client.get(self.preview_url, {"year": 2026})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_december_returns_january_next_year(self, authenticated_api_client):
        response = authenticated_api_client.get(self.preview_url, {"year": 2026, "month": 12})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["year"] == 2027
        assert response.data["month"] == 1

    # --- permissions ---

    def test_non_admin_cannot_advance(self, regular_authenticated_api_client, active_lease):
        response = regular_authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_rollback(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.post(
            self.rollback_url,
            {"year": 2026, "month": 1, "confirm": True},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_get_status(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.get(self.status_url, {"year": 2026, "month": 1})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self, api_client):
        response = api_client.get(self.status_url, {"year": 2026, "month": 1})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_advance_attaches_notes_to_snapshot(
        self, authenticated_api_client, active_lease, financial_settings
    ):
        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True, "notes": "Mês de teste"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 1, 1))
        assert snapshot.notes == "Mês de teste"

    def test_advance_summary_contains_financial_totals(
        self, authenticated_api_client, active_lease, financial_settings
    ):
        response = authenticated_api_client.post(
            self.advance_url,
            {"year": 2026, "month": 1, "force": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        summary = response.data["summary"]
        assert "total_income" in summary
        assert "total_expenses" in summary
        assert "net_balance" in summary
        assert "cumulative_ending_balance" in summary
