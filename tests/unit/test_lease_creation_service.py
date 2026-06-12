"""Tests for LeaseCreationService — rental-value derivation, defaults, apartment sync."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from core.models import Apartment, Tenant
from core.services.lease_creation_service import LeaseCreationService
from tests.factories import make_apartment, make_tenant


@pytest.mark.unit
@pytest.mark.django_db
class TestResolveRentalValue:
    def test_single_tenant_uses_rental_value(self) -> None:
        apt = make_apartment(
            rental_value=Decimal("1300.00"), rental_value_double=Decimal("1400.00")
        )
        assert LeaseCreationService.resolve_rental_value(apt, 1) == Decimal("1300.00")

    def test_two_tenants_uses_double_when_present(self) -> None:
        apt = make_apartment(
            rental_value=Decimal("1300.00"), rental_value_double=Decimal("1400.00")
        )
        assert LeaseCreationService.resolve_rental_value(apt, 2) == Decimal("1400.00")

    def test_two_tenants_falls_back_when_double_none(self) -> None:
        apt = make_apartment(rental_value=Decimal("1300.00"), rental_value_double=None)
        assert LeaseCreationService.resolve_rental_value(apt, 2) == Decimal("1300.00")


@pytest.mark.unit
@pytest.mark.django_db
class TestCreate:
    def _data(self, apartment: Apartment, tenant: Tenant, **overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "apartment": apartment,
            "responsible_tenant": tenant,
            "start_date": date(2026, 3, 1),
            "validity_months": 12,
            "number_of_tenants": 1,
        }
        data.update(overrides)
        return data

    def test_two_tenants_derives_double_rental_value(self) -> None:
        apt = make_apartment(
            rental_value=Decimal("1300.00"), rental_value_double=Decimal("1400.00"), max_tenants=2
        )
        tenant = make_tenant()
        lease = LeaseCreationService.create(
            validated_data=self._data(apt, tenant, number_of_tenants=2), tenants=[tenant]
        )
        assert lease.rental_value == Decimal("1400.00")

    def test_respects_explicit_rental_value(self) -> None:
        apt = make_apartment(rental_value=Decimal("1300.00"))
        tenant = make_tenant()
        lease = LeaseCreationService.create(
            validated_data=self._data(apt, tenant, rental_value=Decimal("999.00")),
            tenants=[tenant],
        )
        assert lease.rental_value == Decimal("999.00")

    def test_defaults_last_rent_increase_date_to_start_date(self) -> None:
        apt = make_apartment()
        tenant = make_tenant()
        lease = LeaseCreationService.create(
            validated_data=self._data(apt, tenant), tenants=[tenant]
        )
        assert lease.last_rent_increase_date == date(2026, 3, 1)

    def test_sets_tenants_m2m(self) -> None:
        apt = make_apartment()
        t1 = make_tenant()
        t2 = make_tenant()
        lease = LeaseCreationService.create(validated_data=self._data(apt, t1), tenants=[t1, t2])
        assert set(lease.tenants.all()) == {t1, t2}

    def test_syncs_apartment_last_rent_increase_date(self) -> None:
        apt = make_apartment()
        tenant = make_tenant()
        assert apt.last_rent_increase_date is None
        LeaseCreationService.create(
            validated_data=self._data(apt, tenant, last_rent_increase_date=date(2026, 5, 10)),
            tenants=[tenant],
        )
        apt.refresh_from_db()
        assert apt.last_rent_increase_date == date(2026, 5, 10)


@pytest.mark.unit
@pytest.mark.django_db
class TestSyncApartmentLastRentIncreaseDate:
    def test_noop_when_lease_date_is_none(self) -> None:
        apt = make_apartment()
        tenant = make_tenant()
        lease = LeaseCreationService.create(
            validated_data={
                "apartment": apt,
                "responsible_tenant": tenant,
                "start_date": date(2026, 1, 1),
                "validity_months": 12,
                "number_of_tenants": 1,
                "last_rent_increase_date": date(2026, 1, 1),
            },
            tenants=[tenant],
        )
        apt.refresh_from_db()
        assert apt.last_rent_increase_date == date(2026, 1, 1)

        lease.last_rent_increase_date = None
        LeaseCreationService.sync_apartment_last_rent_increase_date(lease)
        apt.refresh_from_db()
        # Apartment keeps its date; a date-less lease never clears it.
        assert apt.last_rent_increase_date == date(2026, 1, 1)
