"""Tests for the sync_apartment_is_rented signal — race-condition-free atomic update."""

from datetime import date
from decimal import Decimal

import pytest

from core.models import Apartment, Building, Lease, Tenant


@pytest.fixture
def building() -> Building:
    return Building.objects.create(
        street_number=702, name="Signal Race Building", address="Rua Race, 702"
    )


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return Apartment.objects.create(
        building=building, number=301, rental_value="1500.00", max_tenants=2
    )


@pytest.fixture
def tenant() -> Tenant:
    return Tenant.objects.create(
        name="Race Tenant",
        cpf_cnpj="52998224725",
        phone="11987650001",
        marital_status="Solteiro(a)",
        profession="Tester",
    )


@pytest.fixture
def second_tenant() -> Tenant:
    return Tenant.objects.create(
        name="Race Tenant Two",
        cpf_cnpj="46959416000",
        phone="11987650002",
        marital_status="Solteiro(a)",
        profession="Dev",
    )


@pytest.mark.unit
class TestSyncApartmentIsRentedSignal:
    def test_apartment_marked_rented_when_lease_created(
        self, apartment: Apartment, tenant: Tenant
    ) -> None:
        assert apartment.is_rented is False
        Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

    def test_apartment_marked_not_rented_when_last_lease_soft_deleted(
        self, apartment: Apartment, tenant: Tenant
    ) -> None:
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        lease.delete()

        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_apartment_stays_rented_when_one_of_two_leases_deleted(
        self, apartment: Apartment, tenant: Tenant, second_tenant: Tenant
    ) -> None:
        first_lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        # Soft-delete first lease so unique constraint allows second
        first_lease.delete()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

        second_lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=second_tenant,
            start_date=date(2025, 7, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        # Re-save first (soft-deleted) lease — apartment must stay rented
        first_from_db = Lease.all_objects.get(pk=first_lease.pk)
        first_from_db.save()

        apartment.refresh_from_db()
        assert apartment.is_rented is True

        second_lease.delete(hard_delete=True)
