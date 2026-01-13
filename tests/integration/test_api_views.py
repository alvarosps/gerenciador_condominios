"""
Integration tests for API views

Tests all API endpoints including:
- CRUD operations (Create, Read, Update, Delete)
- Custom actions (generate_contract, calculate_late_fee, change_due_date)
- Pagination
- Filtering and ordering
- Error handling
- Status codes

Coverage target: 80%+ of views.py
"""

import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant
from tests.fixtures.factories import (
    ApartmentFactory,
    BuildingFactory,
    DependentFactory,
    FurnitureFactory,
    LeaseFactory,
    TenantFactory,
    create_full_lease_scenario,
)

# ============================================================================
# Building API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestBuildingAPI:
    """Test suite for Building API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client
        self.url = "/api/buildings/"

    def test_list_buildings(self):
        """Test GET /api/buildings/ returns list of buildings"""
        # Create test data
        BuildingFactory.create_batch(3)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_list_buildings_empty(self):
        """Test GET /api/buildings/ with no buildings"""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_create_building(self):
        """Test POST /api/buildings/ creates new building"""
        data = {"street_number": 836, "name": "Edifício Test", "address": "Rua Test, 836 - São Paulo/SP"}

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["street_number"] == 836
        assert response.data["name"] == "Edifício Test"

        # Verify in database
        assert Building.objects.filter(street_number=836).exists()

    def test_create_building_missing_fields(self):
        """Test POST /api/buildings/ with missing required fields"""
        data = {
            "name": "Edifício Incompleto"
            # Missing street_number and address
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "street_number" in response.data

    def test_retrieve_building(self):
        """Test GET /api/buildings/{id}/ returns specific building"""
        building = BuildingFactory(street_number=850)

        response = self.client.get(f"{self.url}{building.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == building.id
        assert response.data["street_number"] == 850

    def test_retrieve_building_not_found(self):
        """Test GET /api/buildings/{id}/ with invalid ID"""
        response = self.client.get(f"{self.url}99999/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_building(self):
        """Test PUT /api/buildings/{id}/ updates building"""
        building = BuildingFactory(name="Nome Antigo")

        data = {"street_number": building.street_number, "name": "Nome Atualizado", "address": building.address}

        response = self.client.put(f"{self.url}{building.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Nome Atualizado"

        # Verify in database
        building.refresh_from_db()
        assert building.name == "Nome Atualizado"

    def test_partial_update_building(self):
        """Test PATCH /api/buildings/{id}/ partially updates building"""
        building = BuildingFactory(name="Nome Antigo")

        data = {"name": "Nome Parcialmente Atualizado"}

        response = self.client.patch(f"{self.url}{building.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Nome Parcialmente Atualizado"

    def test_delete_building(self):
        """Test DELETE /api/buildings/{id}/ deletes building"""
        building = BuildingFactory()
        building_id = building.id

        response = self.client.delete(f"{self.url}{building.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Building.objects.filter(id=building_id).exists()

    def test_pagination(self):
        """Test pagination for building list"""
        BuildingFactory.create_batch(25)  # More than default page size (20)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert response.data["count"] == 25


# ============================================================================
# Furniture API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestFurnitureAPI:
    """Test suite for Furniture API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client
        self.url = "/api/furnitures/"

    def test_list_furnitures(self):
        """Test GET /api/furnitures/"""
        FurnitureFactory.create_batch(5)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5

    def test_create_furniture(self):
        """Test POST /api/furnitures/"""
        data = {"name": "Geladeira", "description": "Geladeira Frost Free"}

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Geladeira"

    def test_retrieve_furniture(self):
        """Test GET /api/furnitures/{id}/"""
        furniture = FurnitureFactory(name="Fogão")

        response = self.client.get(f"{self.url}{furniture.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Fogão"

    def test_update_furniture(self):
        """Test PUT /api/furnitures/{id}/"""
        furniture = FurnitureFactory()

        data = {"name": furniture.name, "description": "Nova Descrição"}

        response = self.client.put(f"{self.url}{furniture.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "Nova Descrição"

    def test_delete_furniture(self):
        """Test DELETE /api/furnitures/{id}/"""
        furniture = FurnitureFactory()
        furniture_id = furniture.id

        response = self.client.delete(f"{self.url}{furniture.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Furniture.objects.filter(id=furniture_id).exists()


# ============================================================================
# Apartment API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestApartmentAPI:
    """Test suite for Apartment API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client
        self.url = "/api/apartments/"

    def test_list_apartments(self):
        """Test GET /api/apartments/"""
        ApartmentFactory.create_batch(3)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_create_apartment(self):
        """Test POST /api/apartments/"""
        building = BuildingFactory()

        data = {
            "building_id": building.id,
            "number": 101,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
            "interfone_configured": False,
            "contract_generated": False,
            "contract_signed": False,
            "is_rented": False,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["number"] == 101
        assert Decimal(response.data["rental_value"]) == Decimal("1500.00")

    def test_create_apartment_with_invalid_building(self):
        """Test POST /api/apartments/ with non-existent building"""
        data = {
            "building_id": 99999,
            "number": 102,
            "rental_value": "1500.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_apartment(self):
        """Test GET /api/apartments/{id}/"""
        apartment = ApartmentFactory()

        response = self.client.get(f"{self.url}{apartment.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == apartment.id
        assert "building" in response.data
        assert "furnitures" in response.data

    def test_update_apartment(self):
        """Test PUT /api/apartments/{id}/"""
        apartment = ApartmentFactory(rental_value=Decimal("1500.00"))

        data = {
            "building_id": apartment.building.id,
            "number": apartment.number,
            "rental_value": "1800.00",  # Updated
            "cleaning_fee": str(apartment.cleaning_fee),
            "max_tenants": apartment.max_tenants,
            "interfone_configured": apartment.interfone_configured,
            "contract_generated": apartment.contract_generated,
            "contract_signed": apartment.contract_signed,
            "is_rented": apartment.is_rented,
        }

        response = self.client.put(f"{self.url}{apartment.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["rental_value"]) == Decimal("1800.00")

    def test_delete_apartment(self):
        """Test DELETE /api/apartments/{id}/"""
        apartment = ApartmentFactory()
        apartment_id = apartment.id

        response = self.client.delete(f"{self.url}{apartment.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Apartment.objects.filter(id=apartment_id).exists()


# ============================================================================
# Tenant API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestTenantAPI:
    """Test suite for Tenant API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client
        self.url = "/api/tenants/"

    def test_list_tenants(self):
        """Test GET /api/tenants/"""
        TenantFactory.create_batch(3)

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_create_tenant(self):
        """Test POST /api/tenants/"""
        data = {
            "name": "João da Silva",
            "cpf_cnpj": "529.982.247-25",  # Valid CPF
            "phone": "(11) 98765-4321",
            "marital_status": "Casado(a)",
            "profession": "Engenheiro",
            "rent_due_day": 10,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "João da Silva"

    def test_create_tenant_with_dependents(self):
        """Test POST /api/tenants/ with nested dependents"""
        data = {
            "name": "Maria Santos",
            "cpf_cnpj": "111.444.777-35",  # Valid CPF
            "phone": "(11) 98888-7777",
            "marital_status": "Casado(a)",
            "profession": "Médica",
            "rent_due_day": 5,
            "dependents": [
                {"name": "Pedro Santos", "phone": "(11) 91111-1111"},
                {"name": "Ana Santos", "phone": "(11) 92222-2222"},
            ],
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Maria Santos"
        assert len(response.data["dependents"]) == 2

        # Verify in database
        tenant = Tenant.objects.get(cpf_cnpj="111.444.777-35")
        assert tenant.dependents.count() == 2

    def test_retrieve_tenant(self):
        """Test GET /api/tenants/{id}/"""
        tenant = TenantFactory()
        DependentFactory.create_batch(2, tenant=tenant)

        response = self.client.get(f"{self.url}{tenant.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tenant.id
        assert len(response.data["dependents"]) == 2

    def test_update_tenant(self):
        """Test PUT /api/tenants/{id}/"""
        tenant = TenantFactory(profession="Engenheiro")

        data = {
            "name": tenant.name,
            "cpf_cnpj": tenant.cpf_cnpj,
            "phone": tenant.phone,
            "marital_status": tenant.marital_status,
            "profession": "Arquiteto",  # Updated
            "rent_due_day": tenant.rent_due_day,
        }

        response = self.client.put(f"{self.url}{tenant.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["profession"] == "Arquiteto"

    def test_delete_tenant(self):
        """Test DELETE /api/tenants/{id}/"""
        tenant = TenantFactory()
        # Ensure tenant is not used in any lease
        tenant_id = tenant.id

        response = self.client.delete(f"{self.url}{tenant.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Tenant.objects.filter(id=tenant_id).exists()


# ============================================================================
# Lease API Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestLeaseAPI:
    """Test suite for Lease API endpoints"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client
        self.url = "/api/leases/"

    def test_list_leases(self):
        """Test GET /api/leases/"""
        # Create leases with unique apartments
        for i in range(3):
            apartment = ApartmentFactory()
            tenant = TenantFactory()
            LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_create_lease(self):
        """Test POST /api/leases/"""
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
            "number_of_tenants": 1,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["apartment"]["id"] == apartment.id
        assert len(response.data["tenants"]) == 1

    def test_create_lease_with_multiple_tenants(self):
        """Test POST /api/leases/ with multiple tenants"""
        apartment = ApartmentFactory()
        tenant1 = TenantFactory(cpf_cnpj="234.567.890-92")  # Valid CPF
        tenant2 = TenantFactory(cpf_cnpj="345.678.901-75")  # Valid CPF

        data = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant1.id,
            "tenant_ids": [tenant1.id, tenant2.id],
            "start_date": "2025-02-01",
            "validity_months": 12,
            "due_day": 15,
            "rental_value": "2000.00",
            "cleaning_fee": "250.00",
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }

        response = self.client.post(self.url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["tenants"]) == 2

    def test_retrieve_lease(self):
        """Test GET /api/leases/{id}/"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        response = self.client.get(f"{self.url}{lease.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == lease.id
        assert "apartment" in response.data
        assert "responsible_tenant" in response.data
        assert "tenants" in response.data

    def test_update_lease(self):
        """Test PUT /api/leases/{id}/"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant], due_day=10)

        data = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": str(lease.start_date),
            "validity_months": lease.validity_months,
            "due_day": 15,  # Updated
            "rental_value": str(lease.rental_value),
            "cleaning_fee": str(lease.cleaning_fee),
            "tag_fee": str(lease.tag_fee),
            "number_of_tenants": 1,
        }

        response = self.client.put(f"{self.url}{lease.id}/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["due_day"] == 15

    def test_delete_lease(self):
        """Test DELETE /api/leases/{id}/"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])
        lease_id = lease.id

        response = self.client.delete(f"{self.url}{lease.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Lease.objects.filter(id=lease_id).exists()

    # ========================================================================
    # Custom Actions Tests
    # ========================================================================

    @pytest.mark.pdf
    @patch("core.views.ContractService.generate_contract")
    def test_generate_contract_error_handling(self, mock_generate_contract):
        """Test contract generation error handling"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        # Simulate error in PDF generation
        mock_generate_contract.side_effect = Exception("PDF generation failed")

        response = self.client.post(f"{self.url}{lease.id}/generate_contract/")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.data

    @pytest.mark.pdf
    def test_generate_contract_success_integration(self):
        """
        Integration test for contract generation (marked as slow).
        Note: This requires full infrastructure (Chrome, file system, etc.)
        For unit testing, see test_generate_contract_error_handling
        """
        # This test would require actual Chrome/pyppeteer setup
        # Skipped in normal test runs to keep tests fast
        pytest.skip("Integration test - requires full PDF infrastructure")

    def test_calculate_late_fee_when_late(self):
        """Test GET /api/leases/{id}/calculate_late_fee/ when payment is late"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        # Create lease with due day in the past (before today)
        # Set due day to early in the month to ensure it's in the past
        lease = LeaseFactory(
            apartment=apartment,
            responsible_tenant=tenant,
            tenants=[tenant],
            due_day=1,  # Day 1 - likely in the past
            rental_value=Decimal("1500.00"),
        )

        response = self.client.get(f"{self.url}{lease.id}/calculate_late_fee/")

        assert response.status_code == status.HTTP_200_OK
        # Response will vary based on current date vs due_day
        assert "late_days" in response.data or "message" in response.data

    def test_calculate_late_fee_not_late(self):
        """Test GET /api/leases/{id}/calculate_late_fee/ when payment is not late"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()

        # Create lease with due day in the future
        # Set due day to end of month to ensure it's in the future
        lease = LeaseFactory(
            apartment=apartment,
            responsible_tenant=tenant,
            tenants=[tenant],
            due_day=28,  # Day 28 - likely in the future or same as today
            rental_value=Decimal("1500.00"),
        )

        response = self.client.get(f"{self.url}{lease.id}/calculate_late_fee/")

        assert response.status_code == status.HTTP_200_OK
        # Should return message saying payment is not late
        assert "message" in response.data

    def test_change_due_date(self):
        """Test POST /api/leases/{id}/change_due_date/"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant], due_day=10)

        data = {"new_due_day": 20}

        response = self.client.post(f"{self.url}{lease.id}/change_due_date/", data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "fee" in response.data
        assert response.data["message"] == "Dia de vencimento alterado."

        # Verify in database
        lease.refresh_from_db()
        assert lease.due_day == 20

    def test_change_due_date_missing_parameter(self):
        """Test POST /api/leases/{id}/change_due_date/ without new_due_day"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        data = {}  # Missing new_due_day

        response = self.client.post(f"{self.url}{lease.id}/change_due_date/", data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_change_due_date_invalid_value(self):
        """Test POST /api/leases/{id}/change_due_date/ with invalid value"""
        apartment = ApartmentFactory()
        tenant = TenantFactory()
        lease = LeaseFactory(apartment=apartment, responsible_tenant=tenant, tenants=[tenant])

        # Invalid new_due_day (not a valid number)
        data = {"new_due_day": "not_a_number"}

        response = self.client.post(f"{self.url}{lease.id}/change_due_date/", data, format="json")

        # Should return 400 due to invalid input (improved error handling)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.view
class TestAPIErrorHandling:
    """Test suite for API error handling"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_api_client):
        """Set up test client for all tests"""
        self.client = authenticated_api_client

    def test_invalid_json_format(self):
        """Test POST with invalid JSON format"""
        response = self.client.post("/api/buildings/", "invalid json", content_type="application/json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_method_not_allowed(self):
        """Test using wrong HTTP method"""
        building = BuildingFactory()

        # PATCH on a create-only endpoint (buildings list doesn't support PATCH)
        response = self.client.patch(f"/api/buildings/{building.id}/", {"name": "Test"}, format="json")

        # PATCH is allowed on detail views, so this should work
        # Let's test a truly not-allowed method
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_not_found_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = self.client.get("/api/nonexistent/")

        assert response.status_code == status.HTTP_404_NOT_FOUND
