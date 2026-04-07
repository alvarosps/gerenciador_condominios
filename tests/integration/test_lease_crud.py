"""Integration tests for Lease CRUD — creation, updates, M2M relationships."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Lease
from tests.factories import (
    make_apartment,
    make_building,
    make_dependent,
    make_lease,
    make_tenant,
)


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=7100,
        user=admin_user,
        name="Edifício Lease CRUD",
        address="Rua Lease CRUD, 7100",
    )


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=101,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=3,
    )


@pytest.fixture
def apartment2(building, admin_user):
    return make_apartment(
        building=building,
        number=102,
        user=admin_user,
        rental_value=Decimal("1800.00"),
        rental_value_double=Decimal("1950.00"),
        cleaning_fee=Decimal("250.00"),
        max_tenants=2,
    )


@pytest.fixture
def tenant(admin_user):
    return make_tenant(
        cpf_cnpj="29375235017",
        user=admin_user,
        name="Carlos Lease CRUD",
        phone="11999990011",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
    )


@pytest.fixture
def tenant2(admin_user):
    return make_tenant(
        cpf_cnpj="52998224725",
        user=admin_user,
        name="Maria Lease CRUD",
        phone="11999990022",
        marital_status="Casado(a)",
        profession="Médica",
        due_day=10,
    )


@pytest.fixture
def tenant3(admin_user):
    return make_tenant(
        cpf_cnpj="11222333000181",
        user=admin_user,
        name="Pedro Lease CRUD",
        is_company=True,
        phone="11999990033",
        marital_status="Solteiro(a)",
        profession="TI",
        due_day=15,
    )


@pytest.fixture
def dependent(tenant, admin_user):
    return make_dependent(
        tenant=tenant,
        user=admin_user,
        name="Filho de Carlos",
        phone="11977776666",
    )


@pytest.fixture
def dependent2(tenant2, admin_user):
    return make_dependent(
        tenant=tenant2,
        user=admin_user,
        name="Filho de Maria",
        phone="11988887777",
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
    )


@pytest.mark.integration
class TestLeaseCreate:
    url = "/api/leases/"

    def test_create_lease_with_single_tenant(self, authenticated_api_client, apartment2, tenant2):
        payload = {
            "apartment_id": apartment2.id,
            "responsible_tenant_id": tenant2.id,
            "tenant_ids": [tenant2.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
            "number_of_tenants": 1,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["tag_fee"] == "50.00"
        assert len(response.data["tenants"]) == 1

    def test_create_lease_with_multiple_tenants(
        self, authenticated_api_client, apartment2, tenant2, tenant3, dependent2
    ):
        payload = {
            "apartment_id": apartment2.id,
            "responsible_tenant_id": tenant2.id,
            "tenant_ids": [tenant2.id, tenant3.id],
            "resident_dependent_id": dependent2.id,
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["tenants"]) == 2

    def test_create_lease_invalid_apartment_id(self, authenticated_api_client, tenant):
        payload = {
            "apartment_id": 999999,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_lease_invalid_tenant_id(self, authenticated_api_client, apartment2):
        payload = {
            "apartment_id": apartment2.id,
            "responsible_tenant_id": 999999,
            "tenant_ids": [999999],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_lease_missing_required_fields(self, authenticated_api_client):
        response = authenticated_api_client.post(self.url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestLeaseUpdate:
    def test_full_update_lease(
        self, authenticated_api_client, lease, apartment, tenant, tenant2, dependent
    ):
        payload = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id, tenant2.id],
            "resident_dependent_id": dependent.id,
            "start_date": "2026-02-01",
            "validity_months": 24,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = authenticated_api_client.put(f"/api/leases/{lease.id}/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["validity_months"] == 24
        assert len(response.data["tenants"]) == 2

    def test_partial_update_lease(self, authenticated_api_client, lease):
        response = authenticated_api_client.patch(
            f"/api/leases/{lease.id}/",
            {"tag_fee": "80.00", "contract_signed": True},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tag_fee"] == "80.00"
        assert response.data["contract_signed"] is True

    def test_update_lease_changes_tenants_m2m(
        self, authenticated_api_client, lease, tenant, tenant2, apartment
    ):
        # Start with one tenant, update to two
        lease.tenants.set([tenant])

        payload = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id, tenant2.id],
            "start_date": lease.start_date.isoformat(),
            "validity_months": lease.validity_months,
            "tag_fee": str(lease.tag_fee),
        }
        response = authenticated_api_client.put(f"/api/leases/{lease.id}/", payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        tenant_ids = [t["id"] for t in response.data["tenants"]]
        assert tenant.id in tenant_ids
        assert tenant2.id in tenant_ids


@pytest.mark.integration
class TestLeaseDelete:
    def test_delete_lease_sets_apartment_not_rented(
        self, authenticated_api_client, lease, apartment
    ):
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        response = authenticated_api_client.delete(f"/api/leases/{lease.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_deleted_lease_excluded_from_list(self, authenticated_api_client, lease):
        authenticated_api_client.delete(f"/api/leases/{lease.id}/")
        response = authenticated_api_client.get("/api/leases/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert lease.id not in ids

    def test_delete_lease_regular_user_forbidden(self, regular_authenticated_api_client, lease):
        response = regular_authenticated_api_client.delete(f"/api/leases/{lease.id}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        # Lease should still exist
        assert Lease.objects.filter(id=lease.id).exists()
