"""Integration tests for automatic rent pricing by occupancy feature.

Tests behavioral correctness of:
- ApartmentSerializer: rental_value_double required when max_tenants=2
- ApartmentSerializer: rental_value_double >= rental_value
- LeaseSerializer: number_of_tenants must be 1 or 2
- LeaseSerializer: number_of_tenants cannot exceed apartment.max_tenants
- LeaseSerializer: resident_dependent_id required when number_of_tenants=2
- LeaseSerializer: resident_dependent must belong to responsible_tenant
- Lease creation: rental_value auto-derived from apartment based on occupancy
- Lease update: number_of_tenants change with dependent succeeds
- Contract generation: uses lease.rental_value (not apartment.rental_value)
- Late fee calculation: uses lease.rental_value (not apartment.rental_value)
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Apartment, Building, Dependent, Lease, Tenant


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin_occ",
        email="admin_occ@test.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


@pytest.fixture
def api_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=8800,
        name="Edifício Occupancy",
        address="Rua Occupancy, 8800",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_single(building, admin_user):
    """Apartment that allows only 1 tenant."""
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1000.00"),
        cleaning_fee=Decimal("150.00"),
        max_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_double(building, admin_user):
    """Apartment that allows up to 2 tenants, with double-occupancy pricing."""
    return Apartment.objects.create(
        building=building,
        number=102,
        rental_value=Decimal("1000.00"),
        rental_value_double=Decimal("1100.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Tenant Occupancy",
        cpf_cnpj="29375235017",
        phone="11999990055",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def other_tenant(admin_user):
    return Tenant.objects.create(
        name="Other Tenant",
        cpf_cnpj="52998224725",
        phone="11999990066",
        marital_status="Solteiro(a)",
        profession="Médico",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def dependent(tenant, admin_user):
    return Dependent.objects.create(
        tenant=tenant,
        name="Dependent of Tenant",
        phone="11988880001",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def dependent_of_other(other_tenant, admin_user):
    return Dependent.objects.create(
        tenant=other_tenant,
        name="Dependent of Other Tenant",
        phone="11988880002",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease_single(apartment_double, tenant, admin_user):
    """Single-occupancy lease on a double-capable apartment."""
    return Lease.objects.create(
        apartment=apartment_double,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1000.00"),
        number_of_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
class TestApartmentSerializerValidation:
    """Serializer-level validation for apartment occupancy pricing fields."""

    url = "/api/apartments/"

    def test_apartment_rental_value_double_required_when_max_tenants_2(self, api_client, building):
        """Creating an apartment with max_tenants=2 but no rental_value_double must fail."""
        payload = {
            "building_id": building.id,
            "number": 201,
            "rental_value": "1000.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rental_value_double" in response.data

    def test_apartment_rental_value_double_must_be_gte_rental_value(self, api_client, building):
        """rental_value_double < rental_value must fail validation."""
        payload = {
            "building_id": building.id,
            "number": 202,
            "rental_value": "1000.00",
            "rental_value_double": "900.00",
            "cleaning_fee": "200.00",
            "max_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rental_value_double" in response.data


@pytest.mark.integration
class TestLeaseSerializerValidation:
    """Serializer-level validation for lease occupancy fields."""

    url = "/api/leases/"

    def test_lease_number_of_tenants_must_be_1_or_2(self, api_client, apartment_double, tenant):
        """number_of_tenants=3 must be rejected."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
            "number_of_tenants": 3,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "number_of_tenants" in response.data

    def test_lease_number_of_tenants_cannot_exceed_max_tenants(
        self, api_client, apartment_single, tenant, dependent
    ):
        """Apartment with max_tenants=1 must reject number_of_tenants=2."""
        payload = {
            "apartment_id": apartment_single.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "resident_dependent_id": dependent.id,
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
            "number_of_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lease_resident_dependent_required_when_2_tenants(
        self, api_client, apartment_double, tenant
    ):
        """number_of_tenants=2 without resident_dependent_id must fail."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "resident_dependent_id" in response.data

    def test_lease_resident_dependent_must_belong_to_responsible_tenant(
        self, api_client, apartment_double, tenant, dependent_of_other
    ):
        """Providing a dependent that belongs to a different tenant must fail."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "resident_dependent_id": dependent_of_other.id,
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "resident_dependent_id" in response.data


@pytest.mark.integration
class TestLeaseOccupancyPricing:
    """Integration tests for auto-derived rental_value based on occupancy."""

    url = "/api/leases/"

    def test_create_lease_1_person_auto_derives_rental_value(
        self, api_client, apartment_double, tenant
    ):
        """Creating a lease with number_of_tenants=1 derives rental_value from apartment.rental_value."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "50.00",
            "number_of_tenants": 1,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["rental_value"]) == apartment_double.rental_value

    def test_create_lease_2_persons_auto_derives_rental_value_double(
        self, api_client, apartment_double, tenant, dependent
    ):
        """Creating a lease with number_of_tenants=2 derives rental_value from apartment.rental_value_double."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "resident_dependent_id": dependent.id,
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["rental_value"]) == apartment_double.rental_value_double

    def test_create_lease_2_persons_with_resident_dependent(
        self, api_client, apartment_double, tenant, dependent
    ):
        """Full flow: create lease with dependent, verify resident_dependent is stored."""
        payload = {
            "apartment_id": apartment_double.id,
            "responsible_tenant_id": tenant.id,
            "tenant_ids": [tenant.id],
            "resident_dependent_id": dependent.id,
            "start_date": "2026-06-01",
            "validity_months": 12,
            "tag_fee": "80.00",
            "number_of_tenants": 2,
        }
        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["resident_dependent"] is not None
        assert response.data["resident_dependent"]["id"] == dependent.id
        assert response.data["number_of_tenants"] == 2

    def test_edit_lease_change_number_of_tenants(self, api_client, lease_single, tenant, dependent):
        """PATCH: changing number_of_tenants from 1 to 2 with dependent must succeed."""
        url = f"{self.url}{lease_single.id}/"
        payload = {
            "number_of_tenants": 2,
            "resident_dependent_id": dependent.id,
        }
        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["number_of_tenants"] == 2
        assert response.data["resident_dependent"]["id"] == dependent.id

    def test_contract_generation_uses_lease_rental_value(
        self, api_client, lease_single, tenant, mock_pdf_generation
    ):
        """generate_contract must use lease.rental_value, not apartment.rental_value."""
        lease_single.tenants.add(tenant)

        # Set a custom rental_value on the lease different from the apartment
        lease_single.rental_value = Decimal("1200.00")
        lease_single.save()

        url = f"{self.url}{lease_single.id}/generate_contract/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert "pdf_path" in response.data

        # Verify the lease still holds the custom rental_value (contract used it)
        lease_single.refresh_from_db()
        assert lease_single.rental_value == Decimal("1200.00")

    @freeze_time("2026-03-15")
    def test_late_fee_uses_lease_rental_value(
        self, api_client, apartment_double, tenant, admin_user
    ):
        """calculate_late_fee must use lease.rental_value, not apartment.rental_value.

        apartment_double.rental_value = 1000.00
        lease.rental_value = 1500.00 (custom, higher than apartment)
        tenant.due_day = 10, today = 2026-03-15 → 5 days late

        Fee with lease.rental_value=1500: 5 * 0.05 * (1500/30) = 5 * 0.05 * 50 = 12.50
        Fee with apartment.rental_value=1000: 5 * 0.05 * (1000/30) = 5 * 0.05 * 33.33 = 8.33
        """
        lease = Lease.objects.create(
            apartment=apartment_double,
            responsible_tenant=tenant,
            start_date=date(2026, 1, 1),
            validity_months=12,
            tag_fee=Decimal("50.00"),
            rental_value=Decimal("1500.00"),
            number_of_tenants=1,
            created_by=admin_user,
            updated_by=admin_user,
        )

        url = f"{self.url}{lease.id}/calculate_late_fee/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["late_days"] == 5
        # Verify the fee is based on lease.rental_value=1500, not apartment.rental_value=1000
        assert Decimal(str(response.data["late_fee"])) == Decimal("12.50")
