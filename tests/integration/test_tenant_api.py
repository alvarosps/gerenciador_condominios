"""Integration tests for tenant portal API endpoints (/api/tenant/*)."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Notification, Tenant
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
        tenant, _, _ = tenant_user
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
