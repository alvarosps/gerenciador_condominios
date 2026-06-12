"""Integration tests for soft delete behavior across Building, Apartment, Tenant."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from rest_framework import status

from core.models import Apartment, Building, Condominium, Furniture, Tenant
from tests.factories import make_apartment, make_building, make_furniture, make_tenant


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
    def test_soft_delete_building_excluded_from_list(self, authenticated_api_client, building):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        response = authenticated_api_client.get("/api/buildings/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert building.id not in ids

    def test_soft_delete_building_excluded_from_retrieve(self, authenticated_api_client, building):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        response = authenticated_api_client.get(f"/api/buildings/{building.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_soft_delete_building_record_remains_in_db(self, authenticated_api_client, building):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        # Record still exists with is_deleted=True
        assert Building.all_objects.filter(id=building.id, is_deleted=True).exists()

    def test_soft_delete_building_audit_fields_set(self, authenticated_api_client, building):
        authenticated_api_client.delete(f"/api/buildings/{building.id}/")
        building.refresh_from_db()
        assert building.is_deleted is True
        assert building.deleted_at is not None


@pytest.mark.integration
class TestApartmentSoftDelete:
    def test_soft_delete_apartment_excluded_from_list(self, authenticated_api_client, apartment):
        authenticated_api_client.delete(f"/api/apartments/{apartment.id}/")
        response = authenticated_api_client.get("/api/apartments/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert apartment.id not in ids

    def test_soft_delete_apartment_record_remains_in_db(self, authenticated_api_client, apartment):
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
    def test_soft_delete_tenant_excluded_from_list(self, authenticated_api_client, tenant):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant.id not in ids

    def test_soft_delete_tenant_record_remains_in_db(self, authenticated_api_client, tenant):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        assert Tenant.all_objects.filter(id=tenant.id, is_deleted=True).exists()

    def test_soft_delete_tenant_audit_fields_set(self, authenticated_api_client, tenant):
        authenticated_api_client.delete(f"/api/tenants/{tenant.id}/")
        tenant.refresh_from_db()
        assert tenant.is_deleted is True
        assert tenant.deleted_at is not None

    def test_new_tenant_not_affected_by_deleted_records(self, authenticated_api_client, tenant):
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
        create_response = authenticated_api_client.post("/api/tenants/", payload, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED

        list_response = authenticated_api_client.get("/api/tenants/")
        ids = [item["id"] for item in list_response.data["results"]]
        assert create_response.data["id"] in ids
        assert tenant.id not in ids


@pytest.mark.integration
class TestSoftDeleteAwareUniqueness:
    """Recreating a record with the same key after a soft delete must succeed (the partial
    UniqueConstraint only covers active rows), while two ACTIVE duplicates are still rejected."""

    def test_recreate_building_after_soft_delete(self, admin_user):
        first = make_building(street_number=836, user=admin_user)
        first.delete()
        # Same street_number must be allowed now that the deleted one no longer blocks it.
        second = make_building(street_number=836, user=admin_user)
        assert second.pk != first.pk
        assert Building.objects.filter(street_number=836).count() == 1

    def test_two_active_buildings_same_street_number_rejected(self, admin_user):
        make_building(street_number=840, user=admin_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            make_building(street_number=840, user=admin_user)

    def test_recreate_furniture_name_after_soft_delete(self, admin_user):
        first = make_furniture(name="Geladeira", user=admin_user)
        first.delete()
        second = make_furniture(name="Geladeira", user=admin_user)
        assert second.pk != first.pk
        assert Furniture.objects.filter(name="Geladeira").count() == 1

    def test_two_active_furniture_same_name_rejected(self, admin_user):
        make_furniture(name="Fogão", user=admin_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            make_furniture(name="Fogão", user=admin_user)

    def test_recreate_tenant_cpf_after_soft_delete(self, admin_user):
        first = make_tenant(cpf_cnpj="52998224725", user=admin_user)
        first.delete()
        second = make_tenant(cpf_cnpj="52998224725", user=admin_user)
        assert second.pk != first.pk
        assert Tenant.objects.filter(cpf_cnpj="52998224725").count() == 1

    def test_recreate_apartment_number_after_soft_delete(self, admin_user):
        building = make_building(street_number=900, user=admin_user)
        first = make_apartment(building=building, number=101, user=admin_user)
        first.delete()
        second = make_apartment(building=building, number=101, user=admin_user)
        assert second.pk != first.pk
        assert Apartment.objects.filter(building=building, number=101).count() == 1

    def test_two_active_apartments_same_number_rejected(self, admin_user):
        building = make_building(street_number=901, user=admin_user)
        make_apartment(building=building, number=102, user=admin_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            make_apartment(building=building, number=102, user=admin_user)

    def test_two_active_condominiums_same_name_rejected(self, admin_user):
        Condominium.objects.create(name="Condomínio Único", created_by=admin_user)
        with pytest.raises(IntegrityError), transaction.atomic():
            Condominium.objects.create(name="Condomínio Único", created_by=admin_user)

    def test_recreate_condominium_name_after_soft_delete(self, admin_user):
        first = Condominium.objects.create(name="Condomínio Reuso", created_by=admin_user)
        first.delete()
        second = Condominium.objects.create(name="Condomínio Reuso", created_by=admin_user)
        assert second.pk != first.pk


@pytest.mark.integration
class TestSerializerFriendlyDuplicateErrors:
    """A duplicate active record must surface a 400 with a PT field message, never a 500."""

    def test_duplicate_active_building_returns_400(self, authenticated_api_client, admin_user):
        make_building(street_number=850, user=admin_user)
        payload = {
            "street_number": 850,
            "name": "Prédio Duplicado",
            "address": "Rua Duplicada, 850",
        }
        response = authenticated_api_client.post("/api/buildings/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "street_number" in response.data

    def test_duplicate_active_furniture_returns_400(self, authenticated_api_client, admin_user):
        make_furniture(name="Microondas", user=admin_user)
        response = authenticated_api_client.post(
            "/api/furnitures/", {"name": "Microondas"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_duplicate_active_tenant_cpf_returns_400(self, authenticated_api_client, admin_user):
        make_tenant(cpf_cnpj="52998224725", user=admin_user)
        payload = {
            "name": "Inquilino Duplicado",
            "cpf_cnpj": "529.982.247-25",  # same identity, formatted
            "is_company": False,
            "phone": "(11) 99999-1111",
            "marital_status": "Solteiro(a)",
            "profession": "Eng",
            "due_day": 5,
        }
        response = authenticated_api_client.post("/api/tenants/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cpf_cnpj" in response.data

    def test_duplicate_active_apartment_returns_400(self, authenticated_api_client, admin_user):
        building = make_building(street_number=860, user=admin_user)
        make_apartment(building=building, number=201, user=admin_user)
        payload = {
            "building_id": building.id,
            "number": 201,
            "rental_value": "1000.00",
            "rental_value_double": "1500.00",
            "cleaning_fee": "100.00",
            "max_tenants": 2,
        }
        response = authenticated_api_client.post("/api/apartments/", payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # DRF's UniqueTogetherValidator surfaces this on non_field_errors (clean 400, not 500).
        assert "non_field_errors" in response.data
