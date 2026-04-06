"""Integration tests for AdminProofViewSet — list, approve, reject."""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from core.models import Apartment, Building, Lease, PaymentProof, Tenant

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=7701,
        name="Prédio Provas",
        address="Rua Provas, 7701",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Inquilino Prova",
        cpf_cnpj="52998224725",
        is_company=False,
        phone="11999990001",
        marital_status="Solteiro(a)",
        profession="Programador",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


def _make_proof_file():
    return SimpleUploadedFile("proof.jpg", BytesIO(b"fake-image-data").read(), content_type="image/jpeg")


@pytest.fixture
def pending_proof(lease, admin_user):
    return PaymentProof.objects.create(
        lease=lease,
        reference_month=date(2026, 3, 1),
        file=_make_proof_file(),
        status="pending",
        created_by=admin_user,
        updated_by=admin_user,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAdminProofsAPI:
    list_url = "/api/admin/proofs/"

    def test_list_pending_proofs(self, authenticated_api_client, pending_proof):
        response = authenticated_api_client.get(self.list_url, {"status": "pending"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1
        ids = [item["id"] for item in response.data["results"]]
        assert pending_proof.pk in ids

    def test_approve_proof(self, authenticated_api_client, pending_proof):
        url = f"{self.list_url}{pending_proof.pk}/review/"
        response = authenticated_api_client.post(url, {"action": "approve"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "approved"

        pending_proof.refresh_from_db()
        assert pending_proof.status == "approved"
        assert pending_proof.reviewed_at is not None

    def test_reject_proof_with_reason(self, authenticated_api_client, pending_proof):
        url = f"{self.list_url}{pending_proof.pk}/review/"
        response = authenticated_api_client.post(
            url,
            {"action": "reject", "reason": "Comprovante ilegível"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "rejected"

        pending_proof.refresh_from_db()
        assert pending_proof.status == "rejected"
        assert pending_proof.rejection_reason == "Comprovante ilegível"

    def test_review_invalid_action_returns_400(self, authenticated_api_client, pending_proof):
        url = f"{self.list_url}{pending_proof.pk}/review/"
        response = authenticated_api_client.post(url, {"action": "invalid"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_review_nonexistent_proof_returns_404(self, authenticated_api_client):
        url = f"{self.list_url}99999/review/"
        response = authenticated_api_client.post(url, {"action": "approve"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_requires_authentication(self, api_client):
        response = api_client.get(self.list_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
