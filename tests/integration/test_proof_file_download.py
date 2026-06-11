"""Integration tests for authenticated payment-proof file download endpoints.

Admin:  GET /api/admin/proofs/{id}/file/   (IsAdminUser)
Owner:  GET /api/tenant/payments/proof/{id}/file/  (filtered by the tenant's lease)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import PaymentProof, Tenant
from tests.factories import make_apartment, make_building, make_lease, make_tenant


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=5901,
        user=admin_user,
        name="Edifício Provas Download",
        address="Rua Provas, 5901",
    )


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=101,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
    )


@pytest.fixture
def owner_user():
    return User.objects.create_user(username="proof_owner", is_staff=False, is_active=True)


@pytest.fixture
def tenant(admin_user, owner_user):
    created = make_tenant(
        cpf_cnpj="52998224725",
        user=admin_user,
        name="Dono do Comprovante",
        phone="11999990001",
        due_day=10,
    )
    created.user = owner_user
    created.save(update_fields=["user"])
    return created


@pytest.fixture
def lease(apartment, tenant, admin_user):
    created = make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date=date(2026, 1, 1),
        validity_months=12,
        rental_value=Decimal("1500.00"),
    )
    created.tenants.add(tenant)
    return created


@pytest.fixture
def proof(lease, admin_user):
    return PaymentProof.objects.create(
        lease=lease,
        reference_month=date(2026, 3, 1),
        file=SimpleUploadedFile("p.png", b"\x89PNG\r\n\x1a\nproofbytes", content_type="image/png"),
        status="pending",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def owner_client(owner_user):
    client = APIClient()
    client.force_authenticate(user=owner_user)
    return client


@pytest.fixture
def other_tenant_client(admin_user):
    user = User.objects.create_user(username="proof_other", is_staff=False, is_active=True)
    Tenant.objects.create(
        name="Outro Inquilino",
        cpf_cnpj="11144477735",
        phone="11999990002",
        marital_status="Solteiro(a)",
        profession="Autônomo",
        due_day=5,
        user=user,
        created_by=admin_user,
        updated_by=admin_user,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminProofFileDownload:
    def test_admin_baixa_arquivo_comprovante(self, authenticated_api_client, proof):
        response = authenticated_api_client.get(f"/api/admin/proofs/{proof.pk}/file/")
        try:
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"\x89PNG\r\n\x1a\nproofbytes"
        finally:
            response.close()

    def test_admin_proof_file_served_as_attachment_with_nosniff(
        self, authenticated_api_client, proof
    ):
        response = authenticated_api_client.get(f"/api/admin/proofs/{proof.pk}/file/")
        try:
            assert response.status_code == 200
            assert response["X-Content-Type-Options"] == "nosniff"
            assert response["Content-Disposition"].startswith("attachment")
        finally:
            response.close()

    def test_nao_admin_recebe_403_no_admin_proof_file(self, owner_client, proof):
        response = owner_client.get(f"/api/admin/proofs/{proof.pk}/file/")
        assert response.status_code == 403

    def test_comprovante_inexistente_retorna_404(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/admin/proofs/999999/file/")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantProofFileDownload:
    def test_dono_baixa_proprio_comprovante(self, owner_client, proof):
        response = owner_client.get(f"/api/tenant/payments/proof/{proof.pk}/file/")
        try:
            assert response.status_code == 200
            assert b"".join(response.streaming_content) == b"\x89PNG\r\n\x1a\nproofbytes"
        finally:
            response.close()

    def test_inquilino_nao_baixa_comprovante_de_outro_lease(self, other_tenant_client, proof):
        response = other_tenant_client.get(f"/api/tenant/payments/proof/{proof.pk}/file/")
        assert response.status_code == 404

    def test_comprovante_sem_arquivo_retorna_404(self, owner_client, lease, admin_user):
        proof_no_file = PaymentProof.objects.create(
            lease=lease,
            reference_month=date(2026, 4, 1),
            file="",
            status="pending",
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = owner_client.get(f"/api/tenant/payments/proof/{proof_no_file.pk}/file/")
        assert response.status_code == 404
