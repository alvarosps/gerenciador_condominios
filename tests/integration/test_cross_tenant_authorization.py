"""Integration tests for cross-tenant authorization and portal isolation."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Apartment, Building, Lease, RentPayment, Tenant

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _make_tenant_setup(
    admin_user,
    django_user_model,
    street_number: int,
    apt_number: int,
    cpf_cnpj: str,
    tenant_username: str,
) -> dict:
    """Create building, apartment, tenant, lease, and linked user for portal tests."""
    building = Building.objects.create(
        street_number=street_number,
        name=f"Edifício Tenant {street_number}",
        address=f"Rua Tenant, {street_number}",
        created_by=admin_user,
        updated_by=admin_user,
    )
    apartment = Apartment.objects.create(
        building=building,
        number=apt_number,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )
    tenant = Tenant.objects.create(
        name=f"Inquilino {street_number}",
        cpf_cnpj=cpf_cnpj,
        phone=f"119{street_number:07d}",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        rental_value=Decimal("1500.00"),
        number_of_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )
    user = django_user_model.objects.create_user(
        username=tenant_username,
        password="tenantpass123",
        is_staff=False,
        is_active=True,
    )
    tenant.user = user
    tenant.save(update_fields=["user"])

    return {
        "building": building,
        "apartment": apartment,
        "tenant": tenant,
        "lease": lease,
        "user": user,
    }


@pytest.fixture
def tenant_a_setup(admin_user, django_user_model):
    return _make_tenant_setup(
        admin_user,
        django_user_model,
        street_number=6601,
        apt_number=101,
        cpf_cnpj="52998224725",
        tenant_username="tenant_a_portal",
    )


@pytest.fixture
def tenant_b_setup(admin_user, django_user_model):
    return _make_tenant_setup(
        admin_user,
        django_user_model,
        street_number=6602,
        apt_number=201,
        cpf_cnpj="29375235017",
        tenant_username="tenant_b_portal",
    )


class TestTenantPortalIsolation:
    def test_tenant_sees_own_profile(self, api_client, tenant_a_setup):
        """GET /api/tenant/me/ returns the authenticated tenant's own profile."""
        api_client.force_authenticate(user=tenant_a_setup["user"])
        response = api_client.get("/api/tenant/me/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tenant_a_setup["tenant"].pk
        assert response.data["name"] == tenant_a_setup["tenant"].name

    def test_admin_cannot_access_tenant_portal(self, authenticated_api_client):
        """Admin users (is_staff=True) are blocked by IsTenantUser — returns 403."""
        response = authenticated_api_client.get("/api/tenant/me/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_returns_401(self):
        """Unauthenticated requests to tenant portal return 401."""
        client = APIClient()
        response = client.get("/api/tenant/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tenant_payments_scoped_to_own_lease(
        self, api_client, admin_user, tenant_a_setup, tenant_b_setup
    ):
        """Tenant A's payment list only contains payments for tenant A's lease."""
        # Create a payment for tenant A's lease
        payment_a = RentPayment.objects.create(
            lease=tenant_a_setup["lease"],
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 3, 10),
            created_by=admin_user,
            updated_by=admin_user,
        )
        # Create a payment for tenant B's lease
        RentPayment.objects.create(
            lease=tenant_b_setup["lease"],
            reference_month=date(2026, 3, 1),
            amount_paid=Decimal("1500.00"),
            payment_date=date(2026, 3, 10),
            created_by=admin_user,
            updated_by=admin_user,
        )

        api_client.force_authenticate(user=tenant_a_setup["user"])
        response = api_client.get("/api/tenant/payments/")

        assert response.status_code == status.HTTP_200_OK
        result_ids = [item["id"] for item in response.data["results"]]
        assert payment_a.pk in result_ids
        # Tenant A must not see tenant B's payments
        lease_ids = {item["lease"]["id"] for item in response.data["results"]}
        assert tenant_b_setup["lease"].pk not in lease_ids


class TestAdminCanAccessAllData:
    def test_admin_can_list_all_tenants(
        self, authenticated_api_client, tenant_a_setup, tenant_b_setup
    ):
        """Admin can list tenants from both setups via GET /api/tenants/."""
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK

        ids = [item["id"] for item in response.data["results"]]
        assert tenant_a_setup["tenant"].pk in ids
        assert tenant_b_setup["tenant"].pk in ids

    def test_admin_can_access_any_lease(
        self, authenticated_api_client, tenant_a_setup, tenant_b_setup
    ):
        """Admin can retrieve detail for leases belonging to different tenants."""
        response_a = authenticated_api_client.get(f"/api/leases/{tenant_a_setup['lease'].pk}/")
        response_b = authenticated_api_client.get(f"/api/leases/{tenant_b_setup['lease'].pk}/")

        assert response_a.status_code == status.HTTP_200_OK
        assert response_b.status_code == status.HTTP_200_OK
        assert response_a.data["id"] == tenant_a_setup["lease"].pk
        assert response_b.data["id"] == tenant_b_setup["lease"].pk
