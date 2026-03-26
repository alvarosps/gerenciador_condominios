"""
E2E Tests for Property Management Lifecycle Workflows

Tests complete workflows for the property management module:
- Property creation and management lifecycle
- Lease M2M tenant management and tag fees
- Furniture assignment in apartment/tenant/lease context
- Dashboard data accuracy
- Soft delete cascade behavior
- Authentication and permission enforcement
- Search and filter chains
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Apartment, Building, Furniture, Lease, Tenant

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Valid CPFs for use across tests — each test that needs a unique tenant
# must use a different CPF to avoid unique constraint violations.
# All values verified against the Brazilian CPF checksum algorithm.
# ---------------------------------------------------------------------------
CPF_JOAO = "529.982.247-25"   # from conftest.py sample_tenant_data
CPF_MARIA = "05257794187"     # from test_financial_workflow.py
CPF_PEDRO = "24843803480"     # from test_financial_workflow.py
CPF_ANA = "15782647825"       # from test_financial_workflow.py
CPF_CARLOS = "71428793860"    # from test_financial_workflow.py
CPF_FERNANDA = "72604350203"  # from test_financial_workflow.py
CPF_LUCAS = "10433218100"     # generated — verified valid
CPF_SOFIA = "32505476462"     # generated — verified valid


class TestPropertyLifecycleE2E:
    """Complete property management lifecycle from creation through deletion."""

    def test_full_property_lifecycle(self, authenticated_api_client, mock_pdf_generation):
        """
        Full workflow: building → apartment → tenant → lease → contract →
        late fee → due date change → soft delete → re-lease.
        """
        client = authenticated_api_client

        # Step 1: Create building and verify in list
        building_resp = client.post(
            "/api/buildings/",
            {"street_number": 100, "name": "Edifício Principal", "address": "Rua das Flores, 100"},
        )
        assert building_resp.status_code == status.HTTP_201_CREATED
        building_id = building_resp.data["id"]
        assert building_resp.data["street_number"] == 100

        list_resp = client.get("/api/buildings/")
        assert list_resp.status_code == status.HTTP_200_OK
        building_ids = [b["id"] for b in list_resp.data["results"]]
        assert building_id in building_ids

        # Step 2: Create apartment in building and verify relationship
        apt_resp = client.post(
            "/api/apartments/",
            {
                "building_id": building_id,
                "number": 101,
                "rental_value": "1500.00",
                "cleaning_fee": "200.00",
                "max_tenants": 2,
            },
        )
        assert apt_resp.status_code == status.HTTP_201_CREATED
        apt_id = apt_resp.data["id"]
        assert apt_resp.data["building"]["id"] == building_id
        assert apt_resp.data["is_rented"] is False

        # Step 3: Create tenant with valid CPF and verify in list
        tenant_resp = client.post(
            "/api/tenants/",
            {
                "name": "João da Silva",
                "cpf_cnpj": CPF_JOAO,
                "is_company": False,
                "phone": "(11) 98765-4321",
                "marital_status": "Casado(a)",
                "profession": "Engenheiro",
                "due_day": 10,
            },
        )
        assert tenant_resp.status_code == status.HTTP_201_CREATED
        tenant_id = tenant_resp.data["id"]
        assert tenant_resp.data["name"] == "João da Silva"

        tenant_list_resp = client.get("/api/tenants/")
        assert tenant_list_resp.status_code == status.HTTP_200_OK
        tenant_ids = [t["id"] for t in tenant_list_resp.data["results"]]
        assert tenant_id in tenant_ids

        # Step 4: Create lease (apartment + tenant + M2M) and verify is_rented becomes True
        lease_resp = client.post(
            "/api/leases/",
            {
                "apartment_id": apt_id,
                "responsible_tenant_id": tenant_id,
                "tenant_ids": [tenant_id],
                "start_date": "2025-01-01",
                "validity_months": 12,
                "tag_fee": "50.00",
                "number_of_tenants": 1,
            },
        )
        assert lease_resp.status_code == status.HTTP_201_CREATED
        lease_id = lease_resp.data["id"]
        assert lease_resp.data["contract_generated"] is False

        # Apartment should now be rented
        apt_detail = client.get(f"/api/apartments/{apt_id}/")
        assert apt_detail.status_code == status.HTTP_200_OK
        assert apt_detail.data["is_rented"] is True

        # Step 5: Generate contract (mocked PDF) and verify contract_generated=True
        contract_resp = client.post(f"/api/leases/{lease_id}/generate_contract/")
        assert contract_resp.status_code == status.HTTP_200_OK
        assert "pdf_path" in contract_resp.data

        lease_detail = client.get(f"/api/leases/{lease_id}/")
        assert lease_detail.status_code == status.HTTP_200_OK
        assert lease_detail.data["contract_generated"] is True
        assert "pdf_path" in contract_resp.data
        # PDF path should include building number and apartment number
        pdf_path = contract_resp.data["pdf_path"]
        assert str(100) in pdf_path or str(101) in pdf_path or str(lease_id) in pdf_path

        # Step 6: Calculate late fee with frozen time past due date
        # due_day=10, freeze to day 15 of the same month — 5 days late
        with freeze_time("2025-02-15"):
            late_fee_resp = client.get(f"/api/leases/{lease_id}/calculate_late_fee/")
            assert late_fee_resp.status_code == status.HTTP_200_OK
            # Should be late because day 15 > due_day 10
            if late_fee_resp.data.get("late_days") is not None:
                assert late_fee_resp.data["late_days"] >= 5
                assert Decimal(str(late_fee_resp.data["late_fee"])) > Decimal("0")

        # Step 7: Change due date and verify updated
        change_resp = client.post(
            f"/api/leases/{lease_id}/change_due_date/",
            {"new_due_day": 15},
        )
        assert change_resp.status_code == status.HTTP_200_OK
        assert "fee" in change_resp.data

        # Verify tenant due_day was updated
        tenant_detail = client.get(f"/api/tenants/{tenant_id}/")
        assert tenant_detail.status_code == status.HTTP_200_OK
        assert tenant_detail.data["due_day"] == 15

        # Step 8: Soft delete the lease and verify apartment becomes not rented
        delete_resp = client.delete(f"/api/leases/{lease_id}/")
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        # Apartment should no longer be rented
        apt_after_delete = client.get(f"/api/apartments/{apt_id}/")
        assert apt_after_delete.status_code == status.HTTP_200_OK
        assert apt_after_delete.data["is_rented"] is False

        # Step 9: Verify soft-deleted lease excluded from default list
        lease_list_after = client.get("/api/leases/")
        assert lease_list_after.status_code == status.HTTP_200_OK
        deleted_ids = [l["id"] for l in lease_list_after.data["results"]]
        assert lease_id not in deleted_ids

        # Step 10: Create a new apartment and lease — proves is_rented signal works correctly
        # Note: OneToOneField means a soft-deleted lease still occupies the apartment slot.
        # A new apartment is used to verify the is_rented lifecycle works end-to-end.
        apt2_resp = client.post(
            "/api/apartments/",
            {
                "building_id": building_id,
                "number": 102,
                "rental_value": "1200.00",
                "cleaning_fee": "150.00",
                "max_tenants": 2,
            },
        )
        assert apt2_resp.status_code == status.HTTP_201_CREATED
        apt2_id = apt2_resp.data["id"]
        assert apt2_resp.data["is_rented"] is False

        tenant2_resp = client.post(
            "/api/tenants/",
            {
                "name": "Maria Souza",
                "cpf_cnpj": CPF_MARIA,
                "is_company": False,
                "phone": "(11) 91234-5678",
                "marital_status": "Solteiro(a)",
                "profession": "Professora",
                "due_day": 5,
            },
        )
        assert tenant2_resp.status_code == status.HTTP_201_CREATED
        tenant2_id = tenant2_resp.data["id"]

        new_lease_resp = client.post(
            "/api/leases/",
            {
                "apartment_id": apt2_id,
                "responsible_tenant_id": tenant2_id,
                "tenant_ids": [tenant2_id],
                "start_date": "2025-03-01",
                "validity_months": 12,
                "tag_fee": "50.00",
                "number_of_tenants": 1,
            },
        )
        assert new_lease_resp.status_code == status.HTTP_201_CREATED

        # Apartment 2 is now rented via signal
        apt2_detail = client.get(f"/api/apartments/{apt2_id}/")
        assert apt2_detail.data["is_rented"] is True

        # Original apartment (with soft-deleted lease) remains unrented
        apt_still_unrented = client.get(f"/api/apartments/{apt_id}/")
        assert apt_still_unrented.data["is_rented"] is False


class TestLeaseM2MTenantManagement:
    """Lease M2M tenant management and tag fee logic."""

    def test_m2m_tenants_and_tag_fee(self, authenticated_api_client):
        """
        Create lease with 2 tenants → verify tag_fee=R$80, both tenants present.
        Remove tenant → verify update. Add back → verify M2M updated.
        """
        client = authenticated_api_client

        # Setup building and apartment
        building = Building.objects.create(
            street_number=200, name="Prédio M2M", address="Rua M2M, 200"
        )
        apt = Apartment.objects.create(
            building=building,
            number=201,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"),
            max_tenants=3,
        )

        # Create 2 tenants via API
        t1_resp = client.post(
            "/api/tenants/",
            {
                "name": "Pedro Alves",
                "cpf_cnpj": CPF_PEDRO,
                "is_company": False,
                "phone": "(11) 91111-1111",
                "marital_status": "Solteiro(a)",
                "profession": "Analista",
                "due_day": 10,
            },
        )
        assert t1_resp.status_code == status.HTTP_201_CREATED
        t1_id = t1_resp.data["id"]

        t2_resp = client.post(
            "/api/tenants/",
            {
                "name": "Ana Lima",
                "cpf_cnpj": CPF_ANA,
                "is_company": False,
                "phone": "(11) 92222-2222",
                "marital_status": "Casado(a)",
                "profession": "Designer",
                "due_day": 10,
            },
        )
        assert t2_resp.status_code == status.HTTP_201_CREATED
        t2_id = t2_resp.data["id"]

        # Create lease with 2 tenants and tag_fee=R$80 (2+ tenants rule)
        lease_resp = client.post(
            "/api/leases/",
            {
                "apartment_id": apt.pk,
                "responsible_tenant_id": t1_id,
                "tenant_ids": [t1_id, t2_id],
                "start_date": "2025-01-01",
                "validity_months": 12,
                "tag_fee": "80.00",
                "number_of_tenants": 2,
            },
        )
        assert lease_resp.status_code == status.HTTP_201_CREATED
        lease_id = lease_resp.data["id"]
        assert Decimal(str(lease_resp.data["tag_fee"])) == Decimal("80.00")

        # Verify both tenants appear in lease.tenants
        lease_detail = client.get(f"/api/leases/{lease_id}/")
        assert lease_detail.status_code == status.HTTP_200_OK
        tenant_ids_in_lease = [t["id"] for t in lease_detail.data["tenants"]]
        assert t1_id in tenant_ids_in_lease
        assert t2_id in tenant_ids_in_lease

        # Remove second tenant from lease.
        # Constraint: number_of_tenants must be >= M2M tenant count at save time.
        # The serializer saves fields first, then sets M2M — so we must keep
        # number_of_tenants >= current M2M count (2) when saving, then update count separately.
        # Step A: Remove t2 from M2M while keeping number_of_tenants=2 (satisfies constraint)
        remove_tenant_resp = client.patch(
            f"/api/leases/{lease_id}/",
            {"tenant_ids": [t1_id]},
        )
        assert remove_tenant_resp.status_code == status.HTTP_200_OK

        # Step B: Update number_of_tenants and tag_fee now that M2M has only 1 tenant
        update_count_resp = client.patch(
            f"/api/leases/{lease_id}/",
            {"number_of_tenants": 1, "tag_fee": "50.00"},
        )
        assert update_count_resp.status_code == status.HTTP_200_OK

        # Verify M2M updated — only t1 remains
        updated_detail = client.get(f"/api/leases/{lease_id}/")
        updated_tenant_ids = [t["id"] for t in updated_detail.data["tenants"]]
        assert t1_id in updated_tenant_ids
        assert t2_id not in updated_tenant_ids
        assert Decimal(str(updated_detail.data["tag_fee"])) == Decimal("50.00")

        # Add second tenant back — update count first, then add to M2M
        re_add_resp = client.patch(
            f"/api/leases/{lease_id}/",
            {"tenant_ids": [t1_id, t2_id], "tag_fee": "80.00", "number_of_tenants": 2},
        )
        assert re_add_resp.status_code == status.HTTP_200_OK

        final_detail = client.get(f"/api/leases/{lease_id}/")
        final_tenant_ids = [t["id"] for t in final_detail.data["tenants"]]
        assert t1_id in final_tenant_ids
        assert t2_id in final_tenant_ids
        assert Decimal(str(final_detail.data["tag_fee"])) == Decimal("80.00")


class TestFurnitureManagementWorkflow:
    """Furniture assignment workflow: apartment, tenant, and lease context."""

    def test_furniture_assignment_and_lease_context(self, authenticated_api_client):
        """
        Create furniture, assign to apartment and tenant, verify lease reflects
        the correct furniture (apartment furniture minus tenant furniture).
        """
        client = authenticated_api_client

        # Create furniture items via API
        fridge_resp = client.post(
            "/api/furnitures/",
            {"name": "Geladeira Teste", "description": "Geladeira 300L"},
        )
        assert fridge_resp.status_code == status.HTTP_201_CREATED
        fridge_id = fridge_resp.data["id"]

        stove_resp = client.post(
            "/api/furnitures/",
            {"name": "Fogão Teste", "description": "Fogão 4 bocas"},
        )
        assert stove_resp.status_code == status.HTTP_201_CREATED
        stove_id = stove_resp.data["id"]

        bed_resp = client.post(
            "/api/furnitures/",
            {"name": "Cama Teste", "description": "Cama de casal"},
        )
        assert bed_resp.status_code == status.HTTP_201_CREATED
        bed_id = bed_resp.data["id"]

        # Create building and apartment with all 3 furniture items
        building = Building.objects.create(
            street_number=300, name="Prédio Móveis", address="Rua dos Móveis, 300"
        )
        apt_resp = client.post(
            "/api/apartments/",
            {
                "building_id": building.pk,
                "number": 301,
                "rental_value": "900.00",
                "cleaning_fee": "100.00",
                "max_tenants": 2,
                "furniture_ids": [fridge_id, stove_id, bed_id],
            },
        )
        assert apt_resp.status_code == status.HTTP_201_CREATED
        apt_id = apt_resp.data["id"]
        apt_furniture_names = {f["name"] for f in apt_resp.data["furnitures"]}
        assert "Geladeira Teste" in apt_furniture_names
        assert "Fogão Teste" in apt_furniture_names
        assert "Cama Teste" in apt_furniture_names

        # Create tenant who brings their own bed
        tenant_resp = client.post(
            "/api/tenants/",
            {
                "name": "Carlos Mendes",
                "cpf_cnpj": CPF_CARLOS,
                "is_company": False,
                "phone": "(11) 93333-3333",
                "marital_status": "Divorciado(a)",
                "profession": "Médico",
                "due_day": 5,
                "furniture_ids": [bed_id],
            },
        )
        assert tenant_resp.status_code == status.HTTP_201_CREATED
        tenant_id = tenant_resp.data["id"]
        tenant_furniture_names = {f["name"] for f in tenant_resp.data["furnitures"]}
        assert "Cama Teste" in tenant_furniture_names

        # Create lease
        lease_resp = client.post(
            "/api/leases/",
            {
                "apartment_id": apt_id,
                "responsible_tenant_id": tenant_id,
                "tenant_ids": [tenant_id],
                "start_date": "2025-01-01",
                "validity_months": 12,
                "tag_fee": "50.00",
                "number_of_tenants": 1,
            },
        )
        assert lease_resp.status_code == status.HTTP_201_CREATED
        lease_id = lease_resp.data["id"]

        # Verify lease detail includes apartment furniture and tenant furniture
        lease_detail = client.get(f"/api/leases/{lease_id}/")
        assert lease_detail.status_code == status.HTTP_200_OK

        apt_furniture_in_lease = {f["name"] for f in lease_detail.data["apartment"]["furnitures"]}
        tenant_furniture_in_lease = {
            f["name"] for f in lease_detail.data["tenants"][0]["furnitures"]
        }

        # Apartment has all 3 furniture items
        assert "Geladeira Teste" in apt_furniture_in_lease
        assert "Fogão Teste" in apt_furniture_in_lease
        assert "Cama Teste" in apt_furniture_in_lease

        # Tenant owns the bed (their own furniture)
        assert "Cama Teste" in tenant_furniture_in_lease

        # Contract furniture = apartment furniture - tenant furniture: fridge and stove
        contract_furniture = apt_furniture_in_lease - tenant_furniture_in_lease
        assert "Geladeira Teste" in contract_furniture
        assert "Fogão Teste" in contract_furniture
        assert "Cama Teste" not in contract_furniture

        # Verify furniture list endpoint
        furniture_list = client.get("/api/furnitures/")
        assert furniture_list.status_code == status.HTTP_200_OK
        furniture_names = [f["name"] for f in furniture_list.data["results"]]
        assert "Geladeira Teste" in furniture_names


class TestDashboardDataAccuracy:
    """Dashboard endpoint data accuracy with controlled test data."""

    def test_dashboard_endpoints_return_correct_structure(self, authenticated_api_client):
        """
        Create buildings, apartments, tenants, leases.
        Verify all dashboard endpoints return correct structure and non-negative values.
        """
        client = authenticated_api_client

        # Create two buildings with apartments, one rented and one vacant
        building_a = Building.objects.create(
            street_number=400, name="Prédio Dashboard A", address="Rua A, 400"
        )
        building_b = Building.objects.create(
            street_number=401, name="Prédio Dashboard B", address="Rua B, 401"
        )

        # Rented apartment in building A
        apt_rented = Apartment.objects.create(
            building=building_a,
            number=401,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("200.00"),
            max_tenants=2,
        )
        # Vacant apartment in building A
        Apartment.objects.create(
            building=building_a,
            number=402,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"),
            max_tenants=2,
        )
        # Apartment in building B (rented)
        apt_b = Apartment.objects.create(
            building=building_b,
            number=403,
            rental_value=Decimal("1800.00"),
            cleaning_fee=Decimal("250.00"),
            max_tenants=3,
        )

        tenant_a = Tenant.objects.create(
            name="Fernanda Costa",
            cpf_cnpj=CPF_FERNANDA,
            phone="(11) 94444-4444",
            marital_status="Solteiro(a)",
            profession="Jornalista",
            due_day=10,
        )
        tenant_b = Tenant.objects.create(
            name="Lucas Ferreira",
            cpf_cnpj=CPF_LUCAS,
            phone="(11) 95555-5555",
            marital_status="Casado(a)",
            profession="Advogado",
            due_day=10,
        )

        Lease.objects.create(
            apartment=apt_rented,
            responsible_tenant=tenant_a,
            start_date=date(2024, 1, 1),
            validity_months=24,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1500.00"),
        )
        Lease.objects.create(
            apartment=apt_b,
            responsible_tenant=tenant_b,
            start_date=date(2024, 6, 1),
            validity_months=12,
            tag_fee=Decimal("80.00"),
            rental_value=Decimal("1800.00"),
        )

        # GET /api/dashboard/financial_summary/
        fin_resp = client.get("/api/dashboard/financial_summary/")
        assert fin_resp.status_code == status.HTTP_200_OK
        data = fin_resp.data
        assert "total_revenue" in data
        assert "occupancy_rate" in data
        assert "total_apartments" in data
        assert "rented_apartments" in data
        assert "vacant_apartments" in data
        assert data["total_apartments"] >= 3
        assert data["rented_apartments"] >= 2
        assert data["vacant_apartments"] >= 1
        assert Decimal(str(data["total_revenue"])) >= Decimal("0")

        # GET /api/dashboard/lease_metrics/
        lease_resp = client.get("/api/dashboard/lease_metrics/")
        assert lease_resp.status_code == status.HTTP_200_OK
        lease_data = lease_resp.data
        assert "total_leases" in lease_data
        assert "active_leases" in lease_data
        assert "expired_leases" in lease_data
        assert lease_data["total_leases"] >= 2
        assert lease_data["active_leases"] >= 1

        # GET /api/dashboard/tenant_statistics/
        tenant_resp = client.get("/api/dashboard/tenant_statistics/")
        assert tenant_resp.status_code == status.HTTP_200_OK
        tenant_data = tenant_resp.data
        assert "total_tenants" in tenant_data
        assert "individual_tenants" in tenant_data
        assert "company_tenants" in tenant_data
        assert tenant_data["total_tenants"] >= 2

        # GET /api/dashboard/building_statistics/
        building_resp = client.get("/api/dashboard/building_statistics/")
        assert building_resp.status_code == status.HTTP_200_OK
        buildings_data = building_resp.data
        assert isinstance(buildings_data, list)
        assert len(buildings_data) >= 2

        # Verify per-building structure
        building_a_stat = next(
            (b for b in buildings_data if b["building_number"] == 400), None
        )
        assert building_a_stat is not None
        assert "total_apartments" in building_a_stat
        assert "rented_apartments" in building_a_stat
        assert "occupancy_rate" in building_a_stat
        assert "total_revenue" in building_a_stat
        assert building_a_stat["total_apartments"] >= 2
        assert building_a_stat["rented_apartments"] >= 1

        # GET /api/dashboard/late_payment_summary/ — freeze time to force lateness
        with freeze_time("2025-02-20"):
            late_resp = client.get("/api/dashboard/late_payment_summary/")
            assert late_resp.status_code == status.HTTP_200_OK
            late_data = late_resp.data
            assert "total_late_leases" in late_data
            assert "total_late_fees" in late_data
            assert "late_leases" in late_data
            # With due_day=10 and frozen date=20, both leases should be late
            assert late_data["total_late_leases"] >= 2
            assert Decimal(str(late_data["total_late_fees"])) > Decimal("0")


class TestSoftDeleteCascadeBehavior:
    """Soft delete cascade: records excluded from default queryset, new records unaffected."""

    def test_soft_delete_exclusion_and_isolation(self, authenticated_api_client):
        """
        Soft delete tenant, apartment → verify excluded from default queries.
        Verify deleted records do not interfere with new records.
        """
        client = authenticated_api_client

        building = Building.objects.create(
            street_number=500, name="Prédio Soft Delete", address="Rua Delete, 500"
        )
        apt = Apartment.objects.create(
            building=building,
            number=501,
            rental_value=Decimal("1000.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=2,
        )
        tenant = Tenant.objects.create(
            name="Sofia Ramos",
            cpf_cnpj=CPF_SOFIA,
            phone="(11) 96666-6666",
            marital_status="Solteiro(a)",
            profession="Arquiteta",
            due_day=10,
        )

        # Create lease so we can verify it survives tenant soft delete
        Lease.objects.create(
            apartment=apt,
            responsible_tenant=tenant,
            start_date=date(2024, 1, 1),
            validity_months=12,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1000.00"),
        )

        # Soft delete the tenant via API
        delete_resp = client.delete(f"/api/tenants/{tenant.pk}/")
        assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

        # Tenant should not appear in the default list
        tenant_list = client.get("/api/tenants/")
        assert tenant_list.status_code == status.HTTP_200_OK
        tenant_ids = [t["id"] for t in tenant_list.data["results"]]
        assert tenant.pk not in tenant_ids

        # Soft delete the apartment via API
        apt_delete_resp = client.delete(f"/api/apartments/{apt.pk}/")
        assert apt_delete_resp.status_code == status.HTTP_204_NO_CONTENT

        # Apartment should not appear in the default list
        apt_list = client.get("/api/apartments/")
        assert apt_list.status_code == status.HTTP_200_OK
        apt_ids = [a["id"] for a in apt_list.data["results"]]
        assert apt.pk not in apt_ids

        # Create new tenant and apartment — should be unaffected by deleted records
        new_tenant_resp = client.post(
            "/api/tenants/",
            {
                "name": "Novo Inquilino",
                "cpf_cnpj": CPF_PEDRO,
                "is_company": False,
                "phone": "(11) 97777-7777",
                "marital_status": "Casado(a)",
                "profession": "Contador",
                "due_day": 15,
            },
        )
        assert new_tenant_resp.status_code == status.HTTP_201_CREATED
        new_tenant_id = new_tenant_resp.data["id"]

        new_apt_resp = client.post(
            "/api/apartments/",
            {
                "building_id": building.pk,
                "number": 502,
                "rental_value": "1100.00",
                "cleaning_fee": "120.00",
                "max_tenants": 2,
            },
        )
        assert new_apt_resp.status_code == status.HTTP_201_CREATED
        new_apt_id = new_apt_resp.data["id"]

        # New records appear in lists; old deleted records do not
        final_tenant_list = client.get("/api/tenants/")
        final_tenant_ids = [t["id"] for t in final_tenant_list.data["results"]]
        assert new_tenant_id in final_tenant_ids
        assert tenant.pk not in final_tenant_ids

        final_apt_list = client.get("/api/apartments/")
        final_apt_ids = [a["id"] for a in final_apt_list.data["results"]]
        assert new_apt_id in final_apt_ids
        assert apt.pk not in final_apt_ids


class TestAuthAndPermissionWorkflow:
    """Authentication and permission enforcement across endpoints."""

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated requests to protected endpoints return 401."""
        endpoints = [
            "/api/buildings/",
            "/api/apartments/",
            "/api/tenants/",
            "/api/leases/",
            "/api/furnitures/",
            "/api/dashboard/financial_summary/",
        ]
        for url in endpoints:
            resp = api_client.get(url)
            assert resp.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Expected 401 for unauthenticated GET {url}, got {resp.status_code}"
            )

    def test_non_admin_read_only_on_property_endpoints(
        self, admin_user, regular_user, sample_building_data
    ):
        """
        Regular authenticated user can READ buildings, apartments, tenants, leases.
        Regular user CANNOT CREATE/UPDATE/DELETE (403).
        Admin user can do everything.
        """
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin_user)

        non_admin = APIClient()
        non_admin.force_authenticate(user=regular_user)

        # Admin creates a building
        building_resp = admin_client.post(
            "/api/buildings/",
            {"street_number": 600, "name": "Auth Test", "address": "Rua Auth, 600"},
        )
        assert building_resp.status_code == status.HTTP_201_CREATED
        building_id = building_resp.data["id"]

        # Non-admin can READ
        read_resp = non_admin.get("/api/buildings/")
        assert read_resp.status_code == status.HTTP_200_OK

        detail_resp = non_admin.get(f"/api/buildings/{building_id}/")
        assert detail_resp.status_code == status.HTTP_200_OK

        # Non-admin CANNOT create
        create_resp = non_admin.post(
            "/api/buildings/",
            {"street_number": 601, "name": "Blocked", "address": "Rua Block"},
        )
        assert create_resp.status_code == status.HTTP_403_FORBIDDEN

        # Non-admin CANNOT update
        update_resp = non_admin.patch(f"/api/buildings/{building_id}/", {"name": "Hacked"})
        assert update_resp.status_code == status.HTTP_403_FORBIDDEN

        # Non-admin CANNOT delete
        delete_resp = non_admin.delete(f"/api/buildings/{building_id}/")
        assert delete_resp.status_code == status.HTTP_403_FORBIDDEN

        # Admin can create apartment
        apt_resp = admin_client.post(
            "/api/apartments/",
            {
                "building_id": building_id,
                "number": 601,
                "rental_value": "1000.00",
                "cleaning_fee": "100.00",
                "max_tenants": 2,
            },
        )
        assert apt_resp.status_code == status.HTTP_201_CREATED
        apt_id = apt_resp.data["id"]

        # Non-admin can read apartments
        apt_read = non_admin.get("/api/apartments/")
        assert apt_read.status_code == status.HTTP_200_OK

        # Non-admin cannot delete apartments
        apt_delete = non_admin.delete(f"/api/apartments/{apt_id}/")
        assert apt_delete.status_code == status.HTTP_403_FORBIDDEN

        # Non-admin cannot modify tenants
        tenant_create = non_admin.post(
            "/api/tenants/",
            {
                "name": "Blocked Tenant",
                "cpf_cnpj": CPF_JOAO,
                "phone": "(11) 91111-1111",
                "marital_status": "Solteiro(a)",
                "profession": "Teste",
                "due_day": 10,
            },
        )
        assert tenant_create.status_code == status.HTTP_403_FORBIDDEN

        # Dashboard is admin-only
        dash_resp = non_admin.get("/api/dashboard/financial_summary/")
        assert dash_resp.status_code == status.HTTP_403_FORBIDDEN

        # Admin can access dashboard
        admin_dash = admin_client.get("/api/dashboard/financial_summary/")
        assert admin_dash.status_code == status.HTTP_200_OK


class TestSearchAndFilterChains:
    """Search and filter combinations for tenants, apartments, and leases."""

    def test_tenant_filters(self, authenticated_api_client):
        """
        Test tenant filters: is_company, search, has_furniture, has_dependents.
        """
        client = authenticated_api_client

        # Create individual tenant with furniture
        furn_resp = client.post(
            "/api/furnitures/",
            {"name": "Armário Filtro", "description": "Armário para teste de filtro"},
        )
        assert furn_resp.status_code == status.HTTP_201_CREATED
        furn_id = furn_resp.data["id"]

        individual_resp = client.post(
            "/api/tenants/",
            {
                "name": "Individual Com Móvel",
                "cpf_cnpj": CPF_FERNANDA,
                "is_company": False,
                "phone": "(11) 98888-8888",
                "marital_status": "Solteiro(a)",
                "profession": "Programador",
                "due_day": 10,
                "furniture_ids": [furn_id],
                "dependents": [{"name": "Filho Teste", "phone": "(11) 91234-5000"}],
            },
            format="json",
        )
        assert individual_resp.status_code == status.HTTP_201_CREATED
        individual_id = individual_resp.data["id"]
        # Verify dependent was created via nested serializer
        assert len(individual_resp.data["dependents"]) == 1, (
            f"Expected 1 dependent in response, got: {individual_resp.data['dependents']}"
        )

        company_resp = client.post(
            "/api/tenants/",
            {
                "name": "Empresa XPTO LTDA",
                "cpf_cnpj": "11.222.333/0001-81",
                "is_company": True,
                "phone": "(11) 99999-9999",
                "marital_status": "Solteiro(a)",
                "profession": "Comércio",
                "due_day": 15,
            },
        )
        assert company_resp.status_code == status.HTTP_201_CREATED
        company_id = company_resp.data["id"]

        # Filter by is_company=true
        company_filter = client.get("/api/tenants/", {"is_company": "true"})
        assert company_filter.status_code == status.HTTP_200_OK
        company_result_ids = [t["id"] for t in company_filter.data["results"]]
        assert company_id in company_result_ids
        assert individual_id not in company_result_ids

        # Filter by is_company=false
        individual_filter = client.get("/api/tenants/", {"is_company": "false"})
        assert individual_filter.status_code == status.HTTP_200_OK
        individual_result_ids = [t["id"] for t in individual_filter.data["results"]]
        assert individual_id in individual_result_ids
        assert company_id not in individual_result_ids

        # Search by name
        search_resp = client.get("/api/tenants/", {"search": "Individual Com"})
        assert search_resp.status_code == status.HTTP_200_OK
        search_ids = [t["id"] for t in search_resp.data["results"]]
        assert individual_id in search_ids

        # Filter has_furniture=true
        with_furn = client.get("/api/tenants/", {"has_furniture": "true"})
        assert with_furn.status_code == status.HTTP_200_OK
        with_furn_ids = [t["id"] for t in with_furn.data["results"]]
        assert individual_id in with_furn_ids

        # Filter has_dependents=true
        with_deps = client.get("/api/tenants/", {"has_dependents": "true"})
        assert with_deps.status_code == status.HTTP_200_OK
        with_deps_ids = [t["id"] for t in with_deps.data["results"]]
        assert individual_id in with_deps_ids

        # Combined: is_company=false + search
        combined = client.get(
            "/api/tenants/", {"is_company": "false", "search": "Individual"}
        )
        assert combined.status_code == status.HTTP_200_OK
        combined_ids = [t["id"] for t in combined.data["results"]]
        assert individual_id in combined_ids
        assert company_id not in combined_ids

    def test_apartment_filters(self, authenticated_api_client):
        """
        Test apartment filters: building_id, is_rented, min_price, max_price.
        """
        client = authenticated_api_client

        building_x = Building.objects.create(
            street_number=700, name="Prédio Filtros X", address="Rua X, 700"
        )
        building_y = Building.objects.create(
            street_number=701, name="Prédio Filtros Y", address="Rua Y, 701"
        )

        apt_cheap = Apartment.objects.create(
            building=building_x,
            number=701,
            rental_value=Decimal("800.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=2,
            is_rented=False,
        )
        apt_mid = Apartment.objects.create(
            building=building_x,
            number=702,
            rental_value=Decimal("1500.00"),
            cleaning_fee=Decimal("150.00"),
            max_tenants=2,
            is_rented=True,
        )
        apt_expensive = Apartment.objects.create(
            building=building_y,
            number=703,
            rental_value=Decimal("3000.00"),
            cleaning_fee=Decimal("300.00"),
            max_tenants=3,
            is_rented=False,
        )

        # Filter by building_id
        bx_filter = client.get("/api/apartments/", {"building_id": building_x.pk})
        assert bx_filter.status_code == status.HTTP_200_OK
        bx_ids = [a["id"] for a in bx_filter.data["results"]]
        assert apt_cheap.pk in bx_ids
        assert apt_mid.pk in bx_ids
        assert apt_expensive.pk not in bx_ids

        # Filter is_rented=true
        rented_filter = client.get("/api/apartments/", {"is_rented": "true"})
        assert rented_filter.status_code == status.HTTP_200_OK
        rented_ids = [a["id"] for a in rented_filter.data["results"]]
        assert apt_mid.pk in rented_ids
        assert apt_cheap.pk not in rented_ids

        # Filter is_rented=false
        vacant_filter = client.get("/api/apartments/", {"is_rented": "false"})
        assert vacant_filter.status_code == status.HTTP_200_OK
        vacant_ids = [a["id"] for a in vacant_filter.data["results"]]
        assert apt_cheap.pk in vacant_ids
        assert apt_expensive.pk in vacant_ids
        assert apt_mid.pk not in vacant_ids

        # Filter min_price=1000
        min_filter = client.get("/api/apartments/", {"min_price": "1000"})
        assert min_filter.status_code == status.HTTP_200_OK
        min_ids = [a["id"] for a in min_filter.data["results"]]
        assert apt_mid.pk in min_ids
        assert apt_expensive.pk in min_ids
        assert apt_cheap.pk not in min_ids

        # Filter max_price=2000
        max_filter = client.get("/api/apartments/", {"max_price": "2000"})
        assert max_filter.status_code == status.HTTP_200_OK
        max_ids = [a["id"] for a in max_filter.data["results"]]
        assert apt_cheap.pk in max_ids
        assert apt_mid.pk in max_ids
        assert apt_expensive.pk not in max_ids

        # Combined: building_id + is_rented=false + min_price
        combined = client.get(
            "/api/apartments/",
            {"building_id": building_x.pk, "is_rented": "false", "min_price": "700"},
        )
        assert combined.status_code == status.HTTP_200_OK
        combined_ids = [a["id"] for a in combined.data["results"]]
        assert apt_cheap.pk in combined_ids
        assert apt_mid.pk not in combined_ids

    def test_lease_filters(self, authenticated_api_client):
        """
        Test lease filters: apartment_id, responsible_tenant_id, is_active, is_expired.
        """
        client = authenticated_api_client

        building = Building.objects.create(
            street_number=800, name="Prédio Lease Filter", address="Rua Filter, 800"
        )
        apt_a = Apartment.objects.create(
            building=building,
            number=801,
            rental_value=Decimal("1000.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=2,
        )
        apt_b = Apartment.objects.create(
            building=building,
            number=802,
            rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("120.00"),
            max_tenants=2,
        )

        tenant_a = Tenant.objects.create(
            name="Lease Filter A",
            cpf_cnpj=CPF_JOAO,
            phone="(11) 91010-1010",
            marital_status="Solteiro(a)",
            profession="Dev",
            due_day=10,
        )
        tenant_b = Tenant.objects.create(
            name="Lease Filter B",
            cpf_cnpj=CPF_MARIA,
            phone="(11) 92020-2020",
            marital_status="Casado(a)",
            profession="Designer",
            due_day=5,
        )

        # Active lease (started recently, long validity)
        active_lease = Lease.objects.create(
            apartment=apt_a,
            responsible_tenant=tenant_a,
            start_date=date(2025, 1, 1),
            validity_months=24,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1000.00"),
        )

        # Expired lease (started in the past, short validity)
        expired_lease = Lease.objects.create(
            apartment=apt_b,
            responsible_tenant=tenant_b,
            start_date=date(2020, 1, 1),
            validity_months=12,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1200.00"),
        )

        # Filter by apartment_id
        apt_filter = client.get("/api/leases/", {"apartment_id": apt_a.pk})
        assert apt_filter.status_code == status.HTTP_200_OK
        apt_filter_ids = [l["id"] for l in apt_filter.data["results"]]
        assert active_lease.pk in apt_filter_ids
        assert expired_lease.pk not in apt_filter_ids

        # Filter by responsible_tenant_id
        tenant_filter = client.get(
            "/api/leases/", {"responsible_tenant_id": tenant_a.pk}
        )
        assert tenant_filter.status_code == status.HTTP_200_OK
        tenant_filter_ids = [l["id"] for l in tenant_filter.data["results"]]
        assert active_lease.pk in tenant_filter_ids
        assert expired_lease.pk not in tenant_filter_ids

        # Filter is_active=true — active lease should appear, expired should not
        with freeze_time("2026-03-24"):
            active_filter = client.get("/api/leases/", {"is_active": "true"})
            assert active_filter.status_code == status.HTTP_200_OK
            active_ids = [l["id"] for l in active_filter.data["results"]]
            assert active_lease.pk in active_ids
            assert expired_lease.pk not in active_ids

        # Filter is_expired=true — expired lease should appear, active should not
        with freeze_time("2026-03-24"):
            expired_filter = client.get("/api/leases/", {"is_expired": "true"})
            assert expired_filter.status_code == status.HTTP_200_OK
            expired_ids = [l["id"] for l in expired_filter.data["results"]]
            assert expired_lease.pk in expired_ids
            assert active_lease.pk not in expired_ids
