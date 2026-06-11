"""Integration tests for the authenticated lease contract download endpoint.

GET /api/leases/{id}/contract/ — serves the contract PDF only to admins or the
responsible tenant (owner). Anonymous → 401, other tenant → 404 (IDOR regression:
the lease is outside the requesting tenant's scoped queryset), not generated /
missing file → 404.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Tenant
from tests.factories import make_apartment, make_building, make_lease, make_tenant


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=4836,
        user=admin_user,
        name="Edifício Download",
        address="Rua Download, 4836",
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
    return User.objects.create_user(username="contract_owner", is_staff=False, is_active=True)


@pytest.fixture
def tenant(admin_user, owner_user):
    created = make_tenant(
        cpf_cnpj="52998224725",
        user=admin_user,
        name="Dono do Contrato",
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
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
    )
    created.tenants.add(tenant)
    return created


@pytest.fixture
def other_tenant_client(admin_user):
    """An authenticated tenant who is NOT party to the lease (IDOR victim)."""
    user = User.objects.create_user(username="other_tenant", is_staff=False, is_active=True)
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


@pytest.fixture
def contract_pdf_on_disk(lease):
    """Write the on-disk contract PDF the endpoint serves; remove it (and the building dir, if
    created here) afterwards even on failure. The path is the SSOT relative path under
    BASE_DIR/PDF_OUTPUT_DIR, so it cannot live in a tmp dir."""
    lease.contract_generated = True
    lease.save(update_fields=["contract_generated"])
    apt = lease.apartment
    building_dir = (
        Path(settings.BASE_DIR) / settings.PDF_OUTPUT_DIR / str(apt.building.street_number)
    )
    created_dir = not building_dir.exists()
    building_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = building_dir / f"contract_apto_{apt.number}_{lease.pk}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest contract bytes\n")
    try:
        yield lease, pdf_path
    finally:
        pdf_path.unlink(missing_ok=True)
        if created_dir and building_dir.is_dir() and not any(building_dir.iterdir()):
            building_dir.rmdir()


def _url(lease_pk: int) -> str:
    return f"/api/leases/{lease_pk}/contract/"


@pytest.mark.integration
@pytest.mark.django_db
class TestLeaseContractDownload:
    def test_admin_baixa_contrato_existente_retorna_pdf(
        self, authenticated_api_client, contract_pdf_on_disk
    ):
        lease, pdf_path = contract_pdf_on_disk
        response = authenticated_api_client.get(_url(lease.pk))
        try:
            assert response.status_code == 200
            assert response["Content-Type"] == "application/pdf"
            assert b"".join(response.streaming_content) == pdf_path.read_bytes()
        finally:
            response.close()

    def test_dono_baixa_proprio_contrato(self, contract_pdf_on_disk, owner_user):
        lease, _ = contract_pdf_on_disk
        client = APIClient()
        client.force_authenticate(user=owner_user)
        response = client.get(_url(lease.pk))
        try:
            assert response.status_code == 200
            assert response["Content-Type"] == "application/pdf"
        finally:
            response.close()

    def test_inquilino_de_outro_lease_recebe_404(self, contract_pdf_on_disk, other_tenant_client):
        # After P1.2 the LeaseViewSet queryset is scoped to the requesting tenant, so another
        # tenant's lease is invisible: get_object() 404s before CanGenerateContract runs.
        lease, _ = contract_pdf_on_disk
        response = other_tenant_client.get(_url(lease.pk))
        assert response.status_code == 404

    def test_anonimo_recebe_401(self, api_client, contract_pdf_on_disk):
        lease, _ = contract_pdf_on_disk
        response = api_client.get(_url(lease.pk))
        assert response.status_code == 401

    def test_contrato_nao_gerado_retorna_404(self, authenticated_api_client, lease):
        lease.contract_generated = False
        lease.save(update_fields=["contract_generated"])
        response = authenticated_api_client.get(_url(lease.pk))
        assert response.status_code == 404
        assert "detail" in response.data

    def test_arquivo_ausente_no_disco_retorna_404(self, authenticated_api_client, lease):
        lease.contract_generated = True
        lease.save(update_fields=["contract_generated"])
        response = authenticated_api_client.get(_url(lease.pk))
        assert response.status_code == 404
        assert "detail" in response.data
