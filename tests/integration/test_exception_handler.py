"""Integration tests for the global exception handler (HF-1).

Reproduces the production incident: a row holding legacy-invalid data turns a
minimal partial update into an unhandled django ValidationError. With the
handler registered, the API must answer 400 naming the offending field — never 500.

Invalid rows are seeded via queryset.update(), which bypasses save()/full_clean()
exactly like the legacy data entered the database.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Apartment, Building, Lease, Tenant


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Inquilino Handler",
        cpf_cnpj="29375235017",
        phone="(51) 99999-0011",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=910,
        name="Edifício Handler",
        address="Rua Handler, 910",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=301,
        rental_value=Decimal("1200.00"),
        cleaning_fee=Decimal("150.00"),
        max_tenants=2,
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
        tag_fee=Decimal("20.00"),
        rental_value=Decimal("1200.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
class TestStoredInvalidDataPartialUpdate:
    def test_patch_due_day_with_stored_invalid_marital_status_returns_400(
        self, authenticated_api_client, tenant
    ):
        """Repro do incidente de prod (tenant 7): PATCH {'due_day': 10} numa linha
        com marital_status='Solteira' deve dar 400 apontando o campo — não 500."""
        Tenant.all_objects.filter(pk=tenant.pk).update(marital_status="Solteira")

        response = authenticated_api_client.patch(
            f"/api/tenants/{tenant.pk}/", {"due_day": 10}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "marital_status" in response.json()

    def test_patch_due_day_with_stored_invalid_phone_returns_400(
        self, authenticated_api_client, tenant
    ):
        """Classe dos tenants 44/45/46: telefone armazenado sem DDD."""
        Tenant.all_objects.filter(pk=tenant.pk).update(phone="993102731")

        response = authenticated_api_client.patch(
            f"/api/tenants/{tenant.pk}/", {"due_day": 10}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in response.json()

    def test_patch_on_valid_tenant_still_returns_200(self, authenticated_api_client, tenant):
        response = authenticated_api_client.patch(
            f"/api/tenants/{tenant.pk}/", {"due_day": 15}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["due_day"] == 15
        tenant.refresh_from_db()
        assert tenant.due_day == 15

    def test_patch_lease_with_stored_invalid_validity_months_returns_400(
        self, authenticated_api_client, lease
    ):
        """Mesma classe no Lease: linha armazenada inválida + PATCH mínimo → 400, não 500."""
        Lease.all_objects.filter(pk=lease.pk).update(validity_months=120)

        response = authenticated_api_client.patch(
            f"/api/leases/{lease.pk}/", {"tag_fee": "40.00"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "validity_months" in response.json()
