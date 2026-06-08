"""Unit tests for LeaseSerializer apartment-availability validation (onboarding G3).

The DB has a UniqueConstraint (unique_active_lease_per_apartment, condition is_deleted=False)
that turns a second active lease on the same apartment into an IntegrityError 500. These tests
assert that LeaseSerializer.validate() rejects an occupied apartment with a clean, namespaced
400 (`{"apartment": [...]}`, Portuguese) BEFORE the constraint is hit.
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import Lease
from core.serializers import LeaseSerializer
from tests.factories import (
    make_apartment,
    make_building,
    make_lease,
    make_tenant,
)


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=7201,
        user=admin_user,
        name="Availability Test Building",
        address="Rua Availability, 7201",
    )


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=101,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
    )


@pytest.fixture
def other_apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=102,
        user=admin_user,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
    )


@pytest.fixture
def tenant(admin_user):
    return make_tenant(
        cpf_cnpj="71286955084",
        user=admin_user,
        name="Availability Tenant",
        phone="11966660001",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
    )


@pytest.fixture
def other_tenant(admin_user):
    return make_tenant(
        cpf_cnpj="20000000027",
        user=admin_user,
        name="Other Availability Tenant",
        phone="11966660002",
        marital_status="Solteiro(a)",
        profession="Médico",
        due_day=10,
    )


def _lease_payload(apartment, tenant):
    return {
        "apartment_id": apartment.id,
        "responsible_tenant_id": tenant.id,
        "tenant_ids": [tenant.id],
        "number_of_tenants": 1,
        "start_date": date(2026, 1, 1),
        "validity_months": 12,
        "rental_value": Decimal("1500.00"),
    }


@pytest.mark.unit
@pytest.mark.django_db
class TestLeaseSerializerApartmentAvailability:
    def test_rejects_apartment_with_active_lease(self, apartment, tenant, other_tenant, admin_user):
        existing = make_lease(apartment=apartment, tenant=tenant, user=admin_user)
        existing.tenants.add(tenant)

        serializer = LeaseSerializer(data=_lease_payload(apartment, other_tenant))

        assert serializer.is_valid() is False
        assert "apartment" in serializer.errors
        assert serializer.errors["apartment"] == ["Este apartamento já possui um contrato ativo."]

    def test_allows_free_apartment(self, other_apartment, tenant):
        serializer = LeaseSerializer(data=_lease_payload(other_apartment, tenant))

        assert serializer.is_valid() is True, serializer.errors

    def test_editing_own_lease_does_not_flag_itself(self, apartment, tenant, admin_user):
        lease = make_lease(apartment=apartment, tenant=tenant, user=admin_user)
        lease.tenants.add(tenant)

        serializer = LeaseSerializer(
            instance=lease,
            data={"number_of_tenants": 1, "apartment_id": apartment.id},
            partial=True,
        )

        assert serializer.is_valid() is True, serializer.errors

    def test_soft_deleted_lease_does_not_block_apartment(
        self, apartment, tenant, other_tenant, admin_user
    ):
        old_lease = make_lease(apartment=apartment, tenant=tenant, user=admin_user)
        old_lease.tenants.add(tenant)
        old_lease.delete()  # soft delete

        assert Lease.objects.filter(apartment=apartment).exists() is False
        assert Lease.objects.with_deleted().filter(apartment=apartment).exists() is True

        serializer = LeaseSerializer(data=_lease_payload(apartment, other_tenant))

        assert serializer.is_valid() is True, serializer.errors
