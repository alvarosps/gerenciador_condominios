"""
Unit tests for Core serializers

Tests all serializer functionality including:
- Serialization (model to JSON)
- Deserialization (JSON to model)
- Nested relationships
- Validation rules
- Custom create/update methods
- Read/write field handling (_id fields)

Coverage target: 80%+ of serializers.py
"""

from datetime import date
from decimal import Decimal

from rest_framework.exceptions import ValidationError

import pytest

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant
from core.serializers import (
    ApartmentSerializer,
    BuildingSerializer,
    DependentSerializer,
    FurnitureSerializer,
    LeaseSerializer,
    TenantSerializer,
)
from tests.fixtures.factories import (
    ApartmentFactory,
    BuildingFactory,
    DependentFactory,
    FurnitureFactory,
    LeaseFactory,
    TenantFactory,
)

# ============================================================================
# BuildingSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestBuildingSerializer:
    """Test suite for BuildingSerializer"""

    def test_serialize_building(self):
        """Test serializing a building model to JSON"""
        building = BuildingFactory(street_number=836, name="Edifício Test", address="Rua Test, 836")

        serializer = BuildingSerializer(building)
        data = serializer.data

        assert data["id"] == building.id
        assert data["street_number"] == 836
        assert data["name"] == "Edifício Test"
        assert data["address"] == "Rua Test, 836"

    def test_deserialize_building(self):
        """Test deserializing JSON to building model"""
        data = {"street_number": 850, "name": "Edifício Novo", "address": "Rua Nova, 850 - São Paulo/SP"}

        serializer = BuildingSerializer(data=data)
        assert serializer.is_valid()

        building = serializer.save()
        assert building.street_number == 850
        assert building.name == "Edifício Novo"
        assert building.address == "Rua Nova, 850 - São Paulo/SP"

    def test_building_validation_errors(self):
        """Test validation errors for invalid building data"""
        # Missing required field
        data = {
            "name": "Edifício Sem Número"
            # Missing street_number
        }

        serializer = BuildingSerializer(data=data)
        assert not serializer.is_valid()
        assert "street_number" in serializer.errors

    def test_building_update(self):
        """Test updating an existing building"""
        building = BuildingFactory(name="Nome Antigo")

        data = {"street_number": building.street_number, "name": "Nome Atualizado", "address": building.address}

        serializer = BuildingSerializer(building, data=data)
        assert serializer.is_valid()

        updated_building = serializer.save()
        assert updated_building.name == "Nome Atualizado"
        assert updated_building.id == building.id

    def test_serialize_multiple_buildings(self):
        """Test serializing multiple buildings"""
        buildings = BuildingFactory.create_batch(3)

        serializer = BuildingSerializer(buildings, many=True)
        data = serializer.data

        assert len(data) == 3
        assert all("street_number" in item for item in data)


# ============================================================================
# FurnitureSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestFurnitureSerializer:
    """Test suite for FurnitureSerializer"""

    def test_serialize_furniture(self):
        """Test serializing furniture model to JSON"""
        furniture = FurnitureFactory(name="Geladeira", description="Geladeira Frost Free 300L")

        serializer = FurnitureSerializer(furniture)
        data = serializer.data

        assert data["id"] == furniture.id
        assert data["name"] == "Geladeira"
        assert data["description"] == "Geladeira Frost Free 300L"

    def test_deserialize_furniture(self):
        """Test deserializing JSON to furniture model"""
        data = {"name": "Fogão", "description": "Fogão 4 bocas"}

        serializer = FurnitureSerializer(data=data)
        assert serializer.is_valid()

        furniture = serializer.save()
        assert furniture.name == "Fogão"
        assert furniture.description == "Fogão 4 bocas"

    def test_furniture_optional_description(self):
        """Test that description is optional in serializer"""
        data = {
            "name": "Mesa"
            # No description
        }

        serializer = FurnitureSerializer(data=data)
        assert serializer.is_valid()

        furniture = serializer.save()
        assert furniture.name == "Mesa"
        assert furniture.description in [None, ""]


# ============================================================================
# ApartmentSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestApartmentSerializer:
    """Test suite for ApartmentSerializer"""

    def test_serialize_apartment(self):
        """Test serializing apartment with nested building and furniture"""
        building = BuildingFactory()
        furniture1 = FurnitureFactory(name="Geladeira")
        furniture2 = FurnitureFactory(name="Fogão")

        apartment = ApartmentFactory(building=building, number=101, furnitures=[furniture1, furniture2])

        serializer = ApartmentSerializer(apartment)
        data = serializer.data

        assert data["id"] == apartment.id
        assert data["number"] == 101
        assert data["building"]["id"] == building.id
        assert len(data["furnitures"]) == 2
        assert any(f["name"] == "Geladeira" for f in data["furnitures"])

    def test_deserialize_apartment(self):
        """Test deserializing apartment with building_id"""
        building = BuildingFactory()

        data = {
            "building_id": building.id,
            "number": 102,
            "interfone_configured": False,
            "contract_generated": False,
            "contract_signed": False,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
            "is_rented": False,
        }

        serializer = ApartmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        apartment = serializer.save()
        assert apartment.building == building
        assert apartment.number == 102
        assert apartment.rental_value == Decimal("1500.00")

    def test_apartment_with_furnitures(self):
        """Test that furniture relationship is read-only"""
        building = BuildingFactory()

        data = {
            "building_id": building.id,
            "number": 103,
            "rental_value": "1800.00",
            "cleaning_fee": "250.00",
            "max_tenants": 3,
            "furnitures": [],  # This should be ignored (read-only)
        }

        serializer = ApartmentSerializer(data=data)
        assert serializer.is_valid()

        apartment = serializer.save()
        # Furniture is set separately via many-to-many
        assert apartment.number == 103

    def test_apartment_validation(self):
        """Test validation for apartment data"""
        # Missing required fields
        data = {
            "number": 104
            # Missing building_id, rental_value, etc.
        }

        serializer = ApartmentSerializer(data=data)
        assert not serializer.is_valid()
        assert "building_id" in serializer.errors or "building" in serializer.errors

    def test_apartment_update(self):
        """Test updating an existing apartment"""
        apartment = ApartmentFactory(rental_value=Decimal("1500.00"))

        data = {
            "building_id": apartment.building.id,
            "number": apartment.number,
            "rental_value": "1800.00",  # Updated value
            "cleaning_fee": str(apartment.cleaning_fee),
            "max_tenants": apartment.max_tenants,
            "interfone_configured": apartment.interfone_configured,
            "contract_generated": apartment.contract_generated,
            "contract_signed": apartment.contract_signed,
            "is_rented": apartment.is_rented,
        }

        serializer = ApartmentSerializer(apartment, data=data)
        assert serializer.is_valid()

        updated = serializer.save()
        assert updated.rental_value == Decimal("1800.00")


# ============================================================================
# DependentSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestDependentSerializer:
    """Test suite for DependentSerializer"""

    def test_serialize_dependent(self):
        """Test serializing dependent model"""
        tenant = TenantFactory()
        dependent = DependentFactory(tenant=tenant, name="Maria Silva", phone="(11) 91234-5678")

        serializer = DependentSerializer(dependent)
        data = serializer.data

        assert data["id"] == dependent.id
        assert data["tenant"] == tenant.id
        assert data["name"] == "Maria Silva"
        assert data["phone"] == "(11) 91234-5678"

    def test_deserialize_dependent(self):
        """Test deserializing dependent data (tenant field is read-only, set by parent)"""
        # Note: In practice, dependents are created via nested serialization in TenantSerializer
        # The tenant field is read-only and will be set manually
        data = {"name": "João Filho", "phone": "(11) 99999-8888"}

        serializer = DependentSerializer(data=data)
        assert serializer.is_valid()

        # Tenant must be set manually when not using nested creation
        tenant = TenantFactory()
        dependent = serializer.save(tenant=tenant)
        assert dependent.tenant == tenant
        assert dependent.name == "João Filho"


# ============================================================================
# TenantSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestTenantSerializer:
    """Test suite for TenantSerializer"""

    def test_serialize_tenant_with_dependents(self):
        """Test serializing tenant with nested dependents"""
        tenant = TenantFactory()
        _dep1 = DependentFactory(tenant=tenant, name="Filho 1")  # noqa: F841
        _dep2 = DependentFactory(tenant=tenant, name="Filho 2")  # noqa: F841

        serializer = TenantSerializer(tenant)
        data = serializer.data

        assert data["id"] == tenant.id
        assert data["name"] == tenant.name
        assert len(data["dependents"]) == 2
        assert any(d["name"] == "Filho 1" for d in data["dependents"])
        assert any(d["name"] == "Filho 2" for d in data["dependents"])

    def test_create_tenant_with_dependents(self):
        """Test creating tenant with nested dependents in single request"""
        data = {
            "name": "João da Silva",
            "cpf_cnpj": "529.982.247-25",  # Valid CPF
            "phone": "(11) 98765-4321",
            "marital_status": "Casado(a)",
            "profession": "Engenheiro",
            "rent_due_day": 10,
            "dependents": [
                {"name": "Maria Silva", "phone": "(11) 91111-1111"},
                {"name": "Pedro Silva", "phone": "(11) 92222-2222"},
            ],
        }

        serializer = TenantSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        tenant = serializer.save()
        assert tenant.name == "João da Silva"
        assert tenant.dependents.count() == 2
        assert tenant.dependents.filter(name="Maria Silva").exists()
        assert tenant.dependents.filter(name="Pedro Silva").exists()

    def test_update_tenant_dependents(self):
        """Test updating tenant's dependents"""
        tenant = TenantFactory()
        _old_dep = DependentFactory(tenant=tenant, name="Filho Antigo")  # noqa: F841

        data = {
            "name": tenant.name,
            "cpf_cnpj": tenant.cpf_cnpj,
            "phone": tenant.phone,
            "marital_status": tenant.marital_status,
            "profession": tenant.profession,
            "rent_due_day": tenant.rent_due_day,
            "dependents": [{"name": "Novo Filho", "phone": "(11) 93333-3333"}],
        }

        serializer = TenantSerializer(tenant, data=data)
        assert serializer.is_valid()

        updated_tenant = serializer.save()
        # Old dependent should be deleted, new one created
        assert not updated_tenant.dependents.filter(name="Filho Antigo").exists()
        assert updated_tenant.dependents.filter(name="Novo Filho").exists()

    def test_tenant_with_furnitures(self):
        """Test serializing tenant with furniture"""
        furniture1 = FurnitureFactory(name="Sofá Próprio")
        furniture2 = FurnitureFactory(name="Mesa Própria")

        tenant = TenantFactory(furnitures=[furniture1, furniture2])

        serializer = TenantSerializer(tenant)
        data = serializer.data

        assert len(data["furnitures"]) == 2
        assert any(f["name"] == "Sofá Próprio" for f in data["furnitures"])

    def test_tenant_create_with_furniture_ids(self):
        """Test creating tenant with furniture_ids"""
        furniture1 = FurnitureFactory(name="Sofá")
        furniture2 = FurnitureFactory(name="Mesa")

        data = {
            "name": "Maria Santos",
            "cpf_cnpj": "987.654.321-00",
            "phone": "(11) 98888-7777",
            "marital_status": "Solteiro(a)",
            "profession": "Médica",
            "rent_due_day": 5,
            "furniture_ids": [furniture1.id, furniture2.id],
        }

        serializer = TenantSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        tenant = serializer.save()
        assert tenant.furnitures.count() == 2
        assert furniture1 in tenant.furnitures.all()
        assert furniture2 in tenant.furnitures.all()

    def test_tenant_validation(self):
        """Test validation for required fields"""
        data = {
            "name": "Teste"
            # Missing many required fields
        }

        serializer = TenantSerializer(data=data)
        assert not serializer.is_valid()
        assert "cpf_cnpj" in serializer.errors

    def test_serialize_tenant_without_dependents(self):
        """Test serializing tenant without dependents"""
        tenant = TenantFactory()

        serializer = TenantSerializer(tenant)
        data = serializer.data

        assert "dependents" in data
        assert len(data["dependents"]) == 0


# ============================================================================
# LeaseSerializer Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.serializer
class TestLeaseSerializer:
    """Test suite for LeaseSerializer"""

    def test_serialize_lease(self):
        """Test serializing lease with nested objects"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        serializer = LeaseSerializer(lease)
        data = serializer.data

        assert data["id"] == lease.id
        assert data["apartment"]["id"] == apartment.id
        assert data["responsible_tenant"]["id"] == tenant.id
        assert len(data["tenants"]) == 1
        assert data["tenants"][0]["id"] == tenant.id

    def test_create_lease(self):
        """Test creating lease via serializer"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        data = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2025-01-15",
            "validity_months": 12,
            "due_day": 10,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "tag_fee": "50.00",
        }

        serializer = LeaseSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        lease = serializer.save()
        assert lease.apartment == apartment
        assert lease.responsible_tenant == tenant
        assert lease.tenants.count() == 1
        assert lease.rental_value == Decimal("1500.00")

    def test_lease_with_multiple_tenants(self):
        """Test creating lease with multiple tenants"""
        apartment = ApartmentFactory()
        tenant1 = TenantFactory(cpf_cnpj="276.685.415-00")  # Valid CPF
        tenant2 = TenantFactory(cpf_cnpj="567.890.123-03")  # Valid CPF

        data = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant1.id,
            "tenant_ids": [tenant1.id, tenant2.id],
            "start_date": "2025-02-01",
            "validity_months": 12,
            "due_day": 15,
            "rental_value": "2000.00",
            "cleaning_fee": "250.00",
            "tag_fee": "80.00",  # Multiple tenants
            "number_of_tenants": 2,
        }

        serializer = LeaseSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

        lease = serializer.save()
        assert lease.tenants.count() == 2
        assert tenant1 in lease.tenants.all()
        assert tenant2 in lease.tenants.all()

    def test_lease_validation_apartment_required(self):
        """Test that apartment_id is required"""
        tenant = TenantFactory()

        data = {
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2025-01-15",
            "validity_months": 12,
            "due_day": 10,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "tag_fee": "50.00",
            # Missing apartment_id
        }

        serializer = LeaseSerializer(data=data)
        assert not serializer.is_valid()
        assert "apartment_id" in serializer.errors or "apartment" in serializer.errors

    def test_lease_tag_fee_calculation(self):
        """Test that tag_fee is properly set based on number of tenants"""
        # This is tested in model tests and view tests
        # Serializer just passes the value through
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        # Single tenant - should be 50.00
        data_single = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2025-01-15",
            "validity_months": 12,
            "due_day": 10,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "tag_fee": "50.00",
            "number_of_tenants": 1,
        }

        serializer = LeaseSerializer(data=data_single)
        assert serializer.is_valid()
        lease = serializer.save()
        assert lease.tag_fee == Decimal("50.00")

    def test_lease_update(self):
        """Test updating an existing lease"""
        lease = LeaseFactory(due_day=10)

        data = {
            "apartment_id": lease.apartment.id,
            "responsible_tenant_id": lease.responsible_tenant.id,
            "tenant_ids": [t.id for t in lease.tenants.all()],
            "start_date": str(lease.start_date),
            "validity_months": lease.validity_months,
            "due_day": 15,  # Updated
            "rental_value": str(lease.rental_value),
            "cleaning_fee": str(lease.cleaning_fee),
            "tag_fee": str(lease.tag_fee),
            "number_of_tenants": lease.number_of_tenants,
        }

        serializer = LeaseSerializer(lease, data=data)
        assert serializer.is_valid(), serializer.errors

        updated_lease = serializer.save()
        assert updated_lease.due_day == 15

    def test_serialize_lease_complete_data(self):
        """Test serializing lease returns all expected fields"""
        lease = LeaseFactory()

        serializer = LeaseSerializer(lease)
        data = serializer.data

        expected_fields = [
            "id",
            "apartment",
            "responsible_tenant",
            "tenants",
            "start_date",
            "validity_months",
            "due_day",
            "rental_value",
            "cleaning_fee",
            "tag_fee",
            "contract_generated",
            "contract_signed",
            "interfone_configured",
            "warning_count",
        ]

        for field in expected_fields:
            assert field in data, f"Field '{field}' missing from serialized data"
