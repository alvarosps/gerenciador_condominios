"""Integration tests for tenant portal API endpoints (/api/tenant/*)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    Notification,
    PaymentProof,
    Person,
    RentAdjustment,
    Tenant,
)
from tests.factories import (
    make_apartment,
    make_building,
    make_lease,
    make_rent_payment,
)


@pytest.fixture
def tenant_user(admin_user):
    """Create a tenant with a linked Django user and active lease."""
    building = make_building(
        street_number=500,
        user=admin_user,
        name="Test Building Tenant",
        address="Rua Teste 500",
    )
    apartment = make_apartment(
        building=building,
        number=501,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("150.00"),
        max_tenants=2,
    )
    user = User.objects.create_user(username="tenant_portal_test", is_staff=False)
    tenant = Tenant.objects.create(
        name="Maria Portal",
        cpf_cnpj="98765432100",
        phone="(11) 88888-7777",
        marital_status="Solteiro(a)",
        profession="Engenheira",
        due_day=15,
        user=user,
        created_by=admin_user,
        updated_by=admin_user,
    )
    lease = make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date=timezone.now().date(),
        validity_months=12,
        rental_value=Decimal("1500.00"),
        number_of_tenants=1,
    )
    lease.tenants.add(tenant)
    return tenant, user, lease


@pytest.fixture
def tenant_client(tenant_user):
    _, user, _ = tenant_user
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantMe:
    def test_get_own_data(self, tenant_client, tenant_user):
        _tenant, _, _ = tenant_user
        response = tenant_client.get("/api/tenant/me/")
        assert response.status_code == 200
        assert response.data["name"] == "Maria Portal"
        assert response.data["cpf_cnpj"] == "98765432100"
        assert "lease" in response.data
        assert "apartment" in response.data

    def test_admin_cannot_access(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/tenant/me/")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantPayments:
    def test_list_own_payments(self, tenant_client, tenant_user, admin_user):
        _, _, lease = tenant_user
        make_rent_payment(
            lease=lease,
            user=admin_user,
            reference_month=timezone.now().date().replace(day=1),
            amount_paid=Decimal("1500.00"),
            payment_date=timezone.now().date(),
        )
        response = tenant_client.get("/api/tenant/payments/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantNotifications:
    def test_list_own_notifications(self, tenant_client, tenant_user):
        _, user, _ = tenant_user
        Notification.objects.create(
            recipient=user,
            type="due_reminder",
            title="Vencimento próximo",
            body="Seu aluguel vence em 3 dias",
            sent_at=timezone.now(),
        )
        response = tenant_client.get("/api/tenant/notifications/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_mark_as_read(self, tenant_client, tenant_user):
        _, user, _ = tenant_user
        notif = Notification.objects.create(
            recipient=user,
            type="due_reminder",
            title="Test",
            body="Test",
            sent_at=timezone.now(),
        )
        response = tenant_client.patch(f"/api/tenant/notifications/{notif.pk}/read/")
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_all_read(self, tenant_client, tenant_user):
        _, user, _ = tenant_user
        for i in range(3):
            Notification.objects.create(
                recipient=user,
                type="due_reminder",
                title=f"Test {i}",
                body="Test",
                sent_at=timezone.now(),
            )
        response = tenant_client.post("/api/tenant/notifications/read-all/")
        assert response.status_code == 200
        assert response.data["marked_read"] == 3


@pytest.fixture
def tenant_user_no_lease(admin_user):
    """A tenant linked to a Django user but WITHOUT any lease."""
    user = User.objects.create_user(username="tenant_no_lease", is_staff=False)
    tenant = Tenant.objects.create(
        name="Sem Locação",
        cpf_cnpj="11144477735",
        phone="(11) 90000-0000",
        marital_status="Solteiro(a)",
        profession="Autônomo",
        due_day=10,
        user=user,
        created_by=admin_user,
        updated_by=admin_user,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return tenant, user, client


@pytest.fixture
def contract_pdf_on_disk(tenant_user):
    """Write the on-disk contract PDF the tenant download endpoint serves, and GUARANTEE it (and the
    building dir, if this fixture created it) is removed afterwards — even if the test fails.

    The endpoint reads a hardcoded ``BASE_DIR/contracts/<building>/contract_apto_<apt>_<lease>.pdf``
    path, so the file cannot live in a tmp dir; the teardown is what keeps the working tree clean.
    """
    _, _, lease = tenant_user
    lease.contract_generated = True
    lease.save(update_fields=["contract_generated"])
    apt = lease.apartment
    building_dir = Path(settings.BASE_DIR) / "contracts" / str(apt.building.street_number)
    created_dir = not building_dir.exists()
    building_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = building_dir / f"contract_apto_{apt.number}_{lease.pk}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\ntest contract\n")
    try:
        yield lease, pdf_path
    finally:
        pdf_path.unlink(missing_ok=True)
        if created_dir and building_dir.is_dir() and not any(building_dir.iterdir()):
            building_dir.rmdir()


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantContract:
    def test_not_generated_returns_404(self, tenant_client, tenant_user):
        _, _, lease = tenant_user
        lease.contract_generated = False
        lease.save(update_fields=["contract_generated"])
        response = tenant_client.get("/api/tenant/contract/")
        assert response.status_code == 404
        assert "ainda não foi gerado" in response.data["detail"]

    def test_generated_but_file_missing_returns_404(self, tenant_client, tenant_user):
        _, _, lease = tenant_user
        lease.contract_generated = True
        lease.save(update_fields=["contract_generated"])
        response = tenant_client.get("/api/tenant/contract/")
        assert response.status_code == 404
        assert "não encontrado" in response.data["detail"]

    def test_success_streams_pdf(self, tenant_client, contract_pdf_on_disk):
        response = tenant_client.get("/api/tenant/contract/")
        try:
            assert response.status_code == 200
            assert response["Content-Type"] == "application/pdf"
        finally:
            # Release the FileResponse handle so the fixture teardown can unlink on Windows.
            response.close()

    def test_no_lease_returns_404(self, tenant_user_no_lease):
        _, _, client = tenant_user_no_lease
        response = client.get("/api/tenant/contract/")
        assert response.status_code == 404
        assert "Nenhuma locação ativa" in response.data["detail"]


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantRentAdjustments:
    def test_lists_adjustments(self, tenant_client, tenant_user, admin_user):
        _, _, lease = tenant_user
        RentAdjustment.objects.create(
            lease=lease,
            adjustment_date=date(2026, 1, 1),
            previous_value=Decimal("1400.00"),
            new_value=Decimal("1500.00"),
            percentage=Decimal("7.14"),
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = tenant_client.get("/api/tenant/rent-adjustments/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert Decimal(response.data[0]["new_value"]) == Decimal("1500.00")

    def test_no_lease_returns_404(self, tenant_user_no_lease):
        _, _, client = tenant_user_no_lease
        response = client.get("/api/tenant/rent-adjustments/")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantPix:
    def test_owner_pix_key_used(self, tenant_client, tenant_user, admin_user):
        _, _, lease = tenant_user
        owner = Person.objects.create(
            name="Dona do Apto",
            relationship="Proprietário",
            phone="11955554444",
            pix_key="dona@apto.com",
            pix_key_type="email",
            is_owner=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        apt = lease.apartment
        apt.owner = owner
        apt.save(update_fields=["owner"])

        response = tenant_client.post("/api/tenant/payments/pix/")
        assert response.status_code == 200
        assert "pix_copy_paste" in response.data

    def test_missing_pix_key_returns_400(self, tenant_client):
        # No apartment owner pix key and no FinancialSettings default → ValueError → 400.
        response = tenant_client.post("/api/tenant/payments/pix/")
        assert response.status_code == 400
        assert "Chave PIX" in response.data["detail"]

    def test_no_lease_returns_404(self, tenant_user_no_lease):
        _, _, client = tenant_user_no_lease
        response = client.post("/api/tenant/payments/pix/")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantProof:
    def test_upload_proof_succeeds(self, tenant_client):
        proof_file = SimpleUploadedFile(
            "comprovante.png", b"\x89PNG\r\n\x1a\nfake", content_type="image/png"
        )
        response = tenant_client.post(
            "/api/tenant/payments/proof/",
            data={"reference_month": "2026-03-01", "file": proof_file, "pix_code": "ABC123"},
            format="multipart",
        )
        assert response.status_code == 201
        assert response.data["status"] == "pending"
        assert PaymentProof.objects.filter(pk=response.data["id"]).exists()

    def test_upload_rejects_disallowed_file_type(self, tenant_client):
        bad_file = SimpleUploadedFile(
            "malware.exe", b"MZ binary", content_type="application/octet-stream"
        )
        response = tenant_client.post(
            "/api/tenant/payments/proof/",
            data={"reference_month": "2026-03-01", "file": bad_file},
            format="multipart",
        )
        assert response.status_code == 400

    def test_proof_status_returns_proof(self, tenant_client, tenant_user):
        _, _, lease = tenant_user
        proof = PaymentProof.objects.create(
            lease=lease,
            reference_month=date(2026, 3, 1),
            file=SimpleUploadedFile("p.png", b"img", content_type="image/png"),
        )
        response = tenant_client.get(f"/api/tenant/payments/proof/{proof.pk}/")
        assert response.status_code == 200
        assert response.data["id"] == proof.pk

    def test_proof_status_not_found_returns_404(self, tenant_client):
        response = tenant_client.get("/api/tenant/payments/proof/999999/")
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantDueDateSimulate:
    def test_simulate_success(self, tenant_client):
        response = tenant_client.post(
            "/api/tenant/due-date/simulate/", data={"new_due_day": 20}, format="json"
        )
        assert response.status_code == 200
        assert response.data["new_due_day"] == 20
        assert "fee" in response.data
        assert "days_difference" in response.data

    def test_missing_param_returns_400(self, tenant_client):
        response = tenant_client.post("/api/tenant/due-date/simulate/", data={}, format="json")
        assert response.status_code == 400
        assert "obrigatório" in response.data["detail"]

    def test_non_integer_returns_400(self, tenant_client):
        response = tenant_client.post(
            "/api/tenant/due-date/simulate/", data={"new_due_day": "abc"}, format="json"
        )
        assert response.status_code == 400
        assert "inteiro" in response.data["detail"]

    def test_out_of_range_returns_400(self, tenant_client):
        response = tenant_client.post(
            "/api/tenant/due-date/simulate/", data={"new_due_day": 40}, format="json"
        )
        assert response.status_code == 400
        assert "entre" in response.data["detail"]
