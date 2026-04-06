"""Integration tests for core CRUD viewsets.

Covers BuildingViewSet, FurnitureViewSet, ApartmentViewSet, TenantViewSet,
LeaseViewSet (filters + list) and DashboardViewSet endpoints.

Note: All list endpoints return paginated responses with {"count", "next",
"previous", "results"} structure per CustomPageNumberPagination.
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import Apartment, Building, Dependent, Furniture, Lease, Tenant


def get_ids(response):
    """Extract IDs from a paginated list response."""
    return [item["id"] for item in response.data["results"]]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=900,
        name="Edifício Core Views",
        address="Rua Core, 900",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def building2(admin_user):
    return Building.objects.create(
        street_number=901,
        name="Edifício Core Views 2",
        address="Rua Core, 901",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=201,
        rental_value=Decimal("1200.00"),
        cleaning_fee=Decimal("150.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_expensive(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=202,
        rental_value=Decimal("3000.00"),
        cleaning_fee=Decimal("300.00"),
        max_tenants=3,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def furniture(admin_user):
    return Furniture.objects.create(
        name="Fogão Views Test",
        description="Fogão 4 bocas",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Ana Tenant Views",
        cpf_cnpj="29375235017",
        phone="11999990011",
        marital_status="Solteiro(a)",
        profession="Médica",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant2(admin_user):
    return Tenant.objects.create(
        name="Bruno Views Empresa",
        cpf_cnpj="11222333000181",
        is_company=True,
        phone="11888880022",
        marital_status="Solteiro(a)",
        profession="TI",
        due_day=15,
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
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1200.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


# ---------------------------------------------------------------------------
# BuildingViewSet
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestBuildingViewSet:
    def test_list_buildings_admin(self, authenticated_api_client, building):
        response = authenticated_api_client.get("/api/buildings/")
        assert response.status_code == status.HTTP_200_OK
        assert building.id in get_ids(response)

    def test_list_buildings_regular_user(self, regular_authenticated_api_client, building):
        response = regular_authenticated_api_client.get("/api/buildings/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_buildings_unauthenticated(self, api_client):
        response = api_client.get("/api/buildings/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_building(self, authenticated_api_client, building):
        response = authenticated_api_client.get(f"/api/buildings/{building.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["street_number"] == building.street_number

    def test_create_building_admin(self, authenticated_api_client):
        payload = {
            "street_number": 999,
            "name": "Novo Edifício",
            "address": "Rua Nova, 999",
        }
        response = authenticated_api_client.post("/api/buildings/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["street_number"] == 999

    def test_create_building_regular_user_forbidden(self, regular_authenticated_api_client):
        payload = {
            "street_number": 998,
            "name": "Não Permitido",
            "address": "Rua Bloqueada, 1",
        }
        response = regular_authenticated_api_client.post(
            "/api/buildings/", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_building_admin(self, authenticated_api_client, building):
        payload = {
            "street_number": building.street_number,
            "name": "Nome Atualizado",
            "address": building.address,
        }
        response = authenticated_api_client.put(
            f"/api/buildings/{building.id}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Nome Atualizado"

    def test_delete_building_admin(self, authenticated_api_client, admin_user):
        b = Building.objects.create(
            street_number=997,
            name="Para Deletar",
            address="Rua Delete, 1",
            created_by=admin_user,
        )
        response = authenticated_api_client.delete(f"/api/buildings/{b.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ---------------------------------------------------------------------------
# FurnitureViewSet
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFurnitureViewSet:
    def test_list_furniture_authenticated(self, authenticated_api_client, furniture):
        response = authenticated_api_client.get("/api/furnitures/")
        assert response.status_code == status.HTTP_200_OK
        assert furniture.id in get_ids(response)

    def test_create_furniture_admin(self, authenticated_api_client):
        payload = {"name": "Geladeira Test Create", "description": "Geladeira 300L"}
        response = authenticated_api_client.post("/api/furnitures/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_furniture_regular_user_forbidden(self, regular_authenticated_api_client):
        payload = {"name": "Sofá Bloqueado", "description": "Não deve criar"}
        response = regular_authenticated_api_client.post(
            "/api/furnitures/", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_furniture(self, authenticated_api_client, furniture):
        response = authenticated_api_client.get(f"/api/furnitures/{furniture.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == furniture.name

    def test_list_furniture_unauthenticated(self, api_client):
        response = api_client.get("/api/furnitures/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# ApartmentViewSet — filters
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestApartmentViewSet:
    def test_list_apartments(self, authenticated_api_client, apartment):
        response = authenticated_api_client.get("/api/apartments/")
        assert response.status_code == status.HTTP_200_OK
        assert apartment.id in get_ids(response)

    def test_filter_by_building_id(
        self, authenticated_api_client, building, building2, apartment, admin_user
    ):
        apt2 = Apartment.objects.create(
            building=building2,
            number=301,
            rental_value=Decimal("1000.00"),
            cleaning_fee=Decimal("100.00"),
            max_tenants=1,
            created_by=admin_user,
        )
        response = authenticated_api_client.get(
            f"/api/apartments/?building_id={building.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert apartment.id in ids
        assert apt2.id not in ids

    def test_filter_by_is_rented_false(self, authenticated_api_client, apartment):
        # apartment is not rented (no lease yet)
        response = authenticated_api_client.get("/api/apartments/?is_rented=false")
        assert response.status_code == status.HTTP_200_OK
        assert apartment.id in get_ids(response)

    def test_filter_by_is_rented_true(
        self, authenticated_api_client, apartment, tenant, admin_user, lease
    ):
        # lease fixture creates lease which sets apartment.is_rented=True via signal
        response = authenticated_api_client.get("/api/apartments/?is_rented=true")
        assert response.status_code == status.HTTP_200_OK
        assert apartment.id in get_ids(response)

    def test_filter_by_min_price(
        self, authenticated_api_client, apartment, apartment_expensive
    ):
        response = authenticated_api_client.get("/api/apartments/?min_price=2000")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert apartment_expensive.id in ids
        assert apartment.id not in ids

    def test_filter_by_max_price(
        self, authenticated_api_client, apartment, apartment_expensive
    ):
        response = authenticated_api_client.get("/api/apartments/?max_price=2000")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert apartment.id in ids
        assert apartment_expensive.id not in ids

    def test_create_apartment_admin(self, authenticated_api_client, building):
        payload = {
            "building_id": building.id,
            "number": 505,
            "rental_value": "800.00",
            "cleaning_fee": "100.00",
            "max_tenants": 1,
            "is_rented": False,
        }
        response = authenticated_api_client.post("/api/apartments/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_apartment_regular_user_forbidden(
        self, regular_authenticated_api_client, building
    ):
        payload = {
            "building_id": building.id,
            "number": 506,
            "rental_value": "800.00",
            "cleaning_fee": "100.00",
            "max_tenants": 1,
        }
        response = regular_authenticated_api_client.post(
            "/api/apartments/", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_apartment(self, authenticated_api_client, apartment):
        response = authenticated_api_client.get(f"/api/apartments/{apartment.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["number"] == apartment.number


# ---------------------------------------------------------------------------
# TenantViewSet — filters
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestTenantViewSet:
    def test_list_tenants_admin(self, authenticated_api_client, tenant):
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        assert tenant.id in get_ids(response)

    def test_list_tenants_unauthenticated(self, api_client):
        response = api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_is_company_true(
        self, authenticated_api_client, tenant, tenant2
    ):
        response = authenticated_api_client.get("/api/tenants/?is_company=true")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert tenant2.id in ids
        assert tenant.id not in ids

    def test_filter_by_is_company_false(
        self, authenticated_api_client, tenant, tenant2
    ):
        response = authenticated_api_client.get("/api/tenants/?is_company=false")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert tenant.id in ids
        assert tenant2.id not in ids

    def test_filter_by_has_dependents_true(
        self, authenticated_api_client, tenant, admin_user
    ):
        Dependent.objects.create(
            tenant=tenant,
            name="Filho Teste",
            phone="11911112222",
            created_by=admin_user,
        )
        response = authenticated_api_client.get("/api/tenants/?has_dependents=true")
        assert response.status_code == status.HTTP_200_OK
        assert tenant.id in get_ids(response)

    def test_filter_by_has_dependents_false(
        self, authenticated_api_client, tenant2
    ):
        # tenant2 has no dependents
        response = authenticated_api_client.get("/api/tenants/?has_dependents=false")
        assert response.status_code == status.HTTP_200_OK
        assert tenant2.id in get_ids(response)

    def test_filter_by_has_furniture_true(
        self, authenticated_api_client, tenant, furniture
    ):
        tenant.furnitures.add(furniture)
        response = authenticated_api_client.get("/api/tenants/?has_furniture=true")
        assert response.status_code == status.HTTP_200_OK
        assert tenant.id in get_ids(response)

    def test_filter_by_has_furniture_false(
        self, authenticated_api_client, tenant2
    ):
        response = authenticated_api_client.get("/api/tenants/?has_furniture=false")
        assert response.status_code == status.HTTP_200_OK
        assert tenant2.id in get_ids(response)

    def test_search_by_name(self, authenticated_api_client, tenant, tenant2):
        response = authenticated_api_client.get("/api/tenants/?search=Ana Tenant")
        assert response.status_code == status.HTTP_200_OK
        ids = get_ids(response)
        assert tenant.id in ids
        assert tenant2.id not in ids

    def test_search_by_cpf(self, authenticated_api_client, tenant):
        response = authenticated_api_client.get(
            f"/api/tenants/?search={tenant.cpf_cnpj[:6]}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert tenant.id in get_ids(response)

    def test_create_tenant_admin(self, authenticated_api_client):
        payload = {
            "name": "Novo Inquilino",
            "cpf_cnpj": "529.982.247-25",
            "is_company": False,
            "phone": "(11) 98765-4321",
            "marital_status": "Casado(a)",
            "profession": "Arquiteto",
            "due_day": 10,
        }
        response = authenticated_api_client.post("/api/tenants/", payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_tenant_regular_user_forbidden(self, regular_authenticated_api_client):
        payload = {
            "name": "Bloqueado",
            "cpf_cnpj": "529.982.247-25",
            "phone": "(11) 98765-4321",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
            "due_day": 5,
        }
        response = regular_authenticated_api_client.post(
            "/api/tenants/", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# LeaseViewSet — list filters
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLeaseViewSetFilters:
    def test_list_leases_admin(self, authenticated_api_client, lease):
        response = authenticated_api_client.get("/api/leases/")
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    def test_list_leases_unauthenticated_returns_401(self, api_client, lease):
        response = api_client.get("/api/leases/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_leases_regular_user_can_read(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.get("/api/leases/")
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_apartment_id(
        self, authenticated_api_client, lease, apartment
    ):
        response = authenticated_api_client.get(
            f"/api/leases/?apartment_id={apartment.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    def test_filter_by_responsible_tenant_id(
        self, authenticated_api_client, lease, tenant
    ):
        response = authenticated_api_client.get(
            f"/api/leases/?responsible_tenant_id={tenant.id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    @freeze_time("2026-06-01")
    def test_filter_is_active_true(self, authenticated_api_client, lease):
        # lease starts 2026-01-01 with 12 months validity — active on 2026-06-01
        response = authenticated_api_client.get("/api/leases/?is_active=true")
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    @freeze_time("2028-01-01")
    def test_filter_is_expired_true(self, authenticated_api_client, lease):
        # lease starts 2026-01-01 with 12 months — expired by 2028-01-01
        response = authenticated_api_client.get("/api/leases/?is_expired=true")
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    @freeze_time("2026-12-20")
    def test_filter_expiring_soon(self, authenticated_api_client, lease):
        # lease ends around 2027-01-01 (12 months from 2026-01-01)
        # On 2026-12-20, expiry is within 30 days
        response = authenticated_api_client.get("/api/leases/?expiring_soon=true")
        assert response.status_code == status.HTTP_200_OK
        assert lease.id in get_ids(response)

    def test_create_lease_regular_user_forbidden(
        self, regular_authenticated_api_client, apartment, tenant
    ):
        payload = {
            "apartment_id": apartment.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
        }
        response = regular_authenticated_api_client.post(
            "/api/leases/", payload, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# DashboardViewSet
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestDashboardViewSet:
    def test_financial_summary_admin(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/dashboard/financial_summary/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_revenue" in data
        assert "occupancy_rate" in data
        assert "total_apartments" in data
        assert "rented_apartments" in data
        assert "vacant_apartments" in data

    def test_financial_summary_regular_user_forbidden(self, regular_authenticated_api_client):
        response = regular_authenticated_api_client.get("/api/dashboard/financial_summary/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_financial_summary_unauthenticated(self, api_client):
        response = api_client.get("/api/dashboard/financial_summary/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lease_metrics_admin(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/dashboard/lease_metrics/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_leases" in data
        assert "active_leases" in data
        assert "expired_leases" in data
        assert "expiring_soon" in data

    def test_building_statistics_admin(self, authenticated_api_client, building):
        response = authenticated_api_client.get("/api/dashboard/building_statistics/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        building_ids = [b["building_id"] for b in response.data]
        assert building.id in building_ids

    def test_late_payment_summary_admin(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/dashboard/late_payment_summary/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_late_leases" in data
        assert "total_late_fees" in data
        assert "average_late_days" in data
        assert "late_leases" in data

    def test_tenant_statistics_admin(self, authenticated_api_client, tenant, tenant2):
        response = authenticated_api_client.get("/api/dashboard/tenant_statistics/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "total_tenants" in data
        assert "individual_tenants" in data
        assert "company_tenants" in data
        assert "tenants_with_dependents" in data
        assert data["total_tenants"] >= 2

    def test_dashboard_endpoints_forbidden_for_regular_users(
        self, regular_authenticated_api_client
    ):
        endpoints = [
            "/api/dashboard/financial_summary/",
            "/api/dashboard/lease_metrics/",
            "/api/dashboard/building_statistics/",
            "/api/dashboard/late_payment_summary/",
            "/api/dashboard/tenant_statistics/",
        ]
        for url in endpoints:
            response = regular_authenticated_api_client.get(url)
            assert response.status_code == status.HTTP_403_FORBIDDEN, (
                f"{url} should be 403 for non-admin"
            )
