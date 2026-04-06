"""Integration tests for soft delete behavior across Building, Apartment, Tenant."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import Apartment, Building, Tenant


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=8800,
        name="Edifício Soft Delete",
        address="Rua Soft Delete, 8800",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=301,
        rental_value=Decimal("1000.00"),
        cleaning_fee=Decimal("100.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Soft Delete Tenant",
        cpf_cnpj="29375235017",
        phone="11999998800",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
class TestBuildingSoftDelete:
    def test_soft_delete_building_excluded_from_list(
        self, authenticated_api_client, building
    ):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        response = authenticated_api_client.get("/api/buildings/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert building.id not in ids

    def test_soft_delete_building_excluded_from_retrieve(
        self, authenticated_api_client, building
    ):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        response = authenticated_api_client.get(f"/api/buildings/{building.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_delete_building_record_remains_in_db(
        self, authenticated_api_client, building
    ):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        # Record still exists with is_deleted=True
        assert Building.all_objects.filter(id=building.id, is_deleted=True).exists()

    def test_soft_delete_building_audit_fields_set(
        self, authenticated_api_client, building
    ):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        building.refresh_from_db()
        assert building.is_deleted is True
        assert building.deleted_at is not None


@pytest.mark.integration
class TestApartmentSoftDelete:
    def test_soft_delete_apartment_excluded_from_list(
        self, authenticated_api_client, apartment
    ):
        authenticated_api_client.delete(f"/api/apartments/{apartment.id}/")
        response = authenticated_api_client.get("/api/apartments/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert apartment.id not in ids

    def test_soft_delete_apartment_record_remains_in_db(
        self, authenticated_api_client, apartment
    ):
        authenticated_api_client.delete(f"/api/apartments/{apartment.id}/")
        assert Apartment.all_objects.filter(id=apartment.id, is_deleted=True).exists()

    def test_soft_delete_apartment_building_still_accessible(
        self, authenticated_api_client, building, apartment
    ):
        authenticated_api_client.delete(f"/api/apartments/{apartment.id}/")
        response = authenticated_api_client.get(f"/api/buildings/{building.id}/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestTenantSoftDelete:
    def test_soft_delete_tenant_excluded_from_list(
        self, authenticated_api_client, tenant
    ):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant.id not in ids

    def test_soft_delete_tenant_record_remains_in_db(
        self, authenticated_api_client, tenant
    ):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        assert Tenant.all_objects.filter(id=tenant.id, is_deleted=True).exists()

    def test_soft_delete_tenant_audit_fields_set(
        self, authenticated_api_client, tenant
    ):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        tenant.refresh_from_db()
        assert tenant.is_deleted is True
        assert tenant.deleted_at is not None

    def test_new_tenant_not_affected_by_deleted_records(
        self, authenticated_api_client, tenant
    ):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")

        # Create a new tenant — should not interfere with deleted one
        payload = {
            "name": "Novo Inquilino Pós Delete",
            "cpf_cnpj": "529.982.247-25",
            "is_company": False,
            "phone": "(11) 99999-0000",
            "marital_status": "Solteiro(a)",
            "profession": "Eng",
            "due_day": 5,
        }
        create_response = authenticated_api_client.post(
            "/api/tenants/", payload, format="json"
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        list_response = authenticated_api_client.get("/api/tenants/")
        ids = [item["id"] for item in list_response.data["results"]]
        assert create_response.data["id"] in ids
        assert tenant.id not in ids
