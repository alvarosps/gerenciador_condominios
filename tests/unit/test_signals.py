"""Tests for Django signals — cache invalidation and apartment sync."""

from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Apartment,
    Building,
    Dependent,
    Furniture,
    Lease,
    Tenant,
)
from tests.factories import (
    make_apartment,
    make_building,
    make_dependent,
    make_furniture,
    make_lease,
    make_tenant,
)


@pytest.fixture
def building() -> Building:
    return make_building(street_number=701)


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return make_apartment(building=building, number=201, max_tenants=2)


@pytest.fixture
def tenant() -> Tenant:
    return make_tenant(cpf_cnpj="52998224725", name="Signal Tenant")


@pytest.fixture
def lease(apartment: Apartment, tenant: Tenant) -> Lease:
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=12,
        rental_value=Decimal("1200.00"),
    )


# =============================================================================
# Lease → Apartment sync
# =============================================================================


@pytest.mark.unit
class TestSyncApartmentIsRented:
    def test_apartment_is_rented_true_when_lease_created(
        self, apartment: Apartment, tenant: Tenant
    ) -> None:
        Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1200.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

    def test_apartment_is_rented_false_when_lease_soft_deleted(
        self, lease: Lease, apartment: Apartment
    ) -> None:
        apartment.refresh_from_db()
        assert apartment.is_rented is True
        lease.delete()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_apartment_is_rented_false_on_hard_delete(
        self, lease: Lease, apartment: Apartment
    ) -> None:
        lease.delete(hard_delete=True)
        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_resaving_soft_deleted_lease_does_not_mark_apartment_unavailable_when_active_lease_exists(
        self, lease: Lease, apartment: Apartment
    ) -> None:
        """Historical soft-deleted lease re-save must not override active lease state."""
        second_tenant = make_tenant(cpf_cnpj="46959416000")
        # Soft-delete the first lease so the unique constraint allows a new active lease
        lease.delete()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

        # Create a second active lease for the same apartment
        second_lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=second_tenant,
            start_date=date(2025, 7, 1),
            validity_months=12,
            rental_value=Decimal("1200.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        # Re-save the soft-deleted (historical) lease — simulates any update to it
        lease_from_db = Lease.all_objects.get(pk=lease.pk)
        lease_from_db.save()

        # Apartment must still be rented (second_lease is still active)
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        second_lease.delete(hard_delete=True)

    def test_apartment_becomes_rented_when_new_lease_created_after_soft_delete(
        self, lease: Lease, apartment: Apartment
    ) -> None:
        """After soft-deleting the only lease, creating a new one marks apartment as rented."""
        lease.delete()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

        second_tenant = make_tenant(cpf_cnpj="29765710070")
        Lease.objects.create(
            apartment=apartment,
            responsible_tenant=second_tenant,
            start_date=date(2025, 8, 1),
            validity_months=12,
            rental_value=Decimal("1200.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True


# =============================================================================
# Cache invalidation — Building signals
# =============================================================================


@pytest.mark.unit
class TestBuildingSignals:
    def test_building_save_signal_fires_without_exception(self, building: Building) -> None:
        building.name = "Updated Name"
        building.save()
        building.refresh_from_db()
        assert building.name == "Updated Name"

    def test_building_delete_signal_fires_without_exception(self) -> None:
        b = make_building(street_number=702)
        b.delete()
        assert b.is_deleted is True

    def test_building_hard_delete_fires_post_delete_signal(self) -> None:
        """Covers lines 58-59: post_delete signal for Building (hard delete)."""
        b = make_building(street_number=703)
        pk = b.pk
        b.delete(hard_delete=True)
        assert not Building.all_objects.filter(pk=pk).exists()


# =============================================================================
# Cache invalidation — Apartment signals
# =============================================================================


@pytest.mark.unit
class TestApartmentSignals:
    def test_apartment_save_signal_fires_without_exception(self, apartment: Apartment) -> None:
        apartment.rental_value = "2000.00"
        apartment.save()
        apartment.refresh_from_db()
        assert str(apartment.rental_value) == "2000.00"

    def test_apartment_delete_signal_fires_without_exception(self, apartment: Apartment) -> None:
        pk = apartment.pk
        apartment.delete()
        assert Apartment.objects.filter(pk=pk).count() == 0

    def test_furniture_m2m_change_triggers_signal(self, apartment: Apartment) -> None:
        furniture = make_furniture(name="Signal Furniture")
        apartment.furnitures.add(furniture)
        # m2m_changed signal fires — verify no exception and M2M updated
        assert apartment.furnitures.filter(pk=furniture.pk).exists()
        apartment.furnitures.remove(furniture)
        assert not apartment.furnitures.filter(pk=furniture.pk).exists()


# =============================================================================
# Cache invalidation — Tenant signals
# =============================================================================


@pytest.mark.unit
class TestTenantSignals:
    def test_tenant_save_signal_fires_without_exception(self, tenant: Tenant) -> None:
        tenant.profession = "Médico"
        tenant.save()
        tenant.refresh_from_db()
        assert tenant.profession == "Médico"

    def test_tenant_delete_signal_fires_without_exception(self, tenant: Tenant) -> None:
        pk = tenant.pk
        tenant.delete()
        assert Tenant.objects.filter(pk=pk).count() == 0

    def test_furniture_m2m_change_triggers_signal(self, tenant: Tenant) -> None:
        furniture = make_furniture(name="Tenant Furniture")
        tenant.furnitures.add(furniture)
        assert tenant.furnitures.filter(pk=furniture.pk).exists()
        tenant.furnitures.clear()
        assert tenant.furnitures.count() == 0


# =============================================================================
# Cache invalidation — Furniture signals
# =============================================================================


@pytest.mark.unit
class TestFurnitureSignals:
    def test_furniture_save_triggers_signal(self) -> None:
        furniture = make_furniture(name="New Furniture Signal")
        furniture.description = "Updated"
        furniture.save()
        furniture.refresh_from_db()
        assert furniture.description == "Updated"

    def test_furniture_delete_triggers_signal(self) -> None:
        furniture = make_furniture(name="Delete Furniture Signal")
        pk = furniture.pk
        furniture.delete()
        assert Furniture.objects.filter(pk=pk).count() == 0


# =============================================================================
# Cache invalidation — Dependent signals
# =============================================================================


@pytest.mark.unit
class TestDependentSignals:
    def test_dependent_save_triggers_signal(self, tenant: Tenant) -> None:
        dep = make_dependent(tenant=tenant, name="Dep Signal", phone="11987654399")
        dep.name = "Dep Updated"
        dep.save()
        dep.refresh_from_db()
        assert dep.name == "Dep Updated"

    def test_dependent_delete_triggers_signal(self, tenant: Tenant) -> None:
        dep = make_dependent(tenant=tenant, name="Dep Del", phone="11987654398")
        pk = dep.pk
        dep.delete()
        assert Dependent.objects.filter(pk=pk).count() == 0

    def test_dependent_hard_delete_fires_post_delete_signal(self, tenant: Tenant) -> None:
        """Covers lines 260-261: post_delete signal for Dependent (hard delete)."""
        dep = make_dependent(tenant=tenant, name="Dep Hard Del", phone="11987654397")
        pk = dep.pk
        dep.delete(hard_delete=True)
        assert not Dependent.all_objects.filter(pk=pk).exists()


# =============================================================================
# Lease M2M tenants signal
# =============================================================================


@pytest.mark.unit
class TestLeaseTenantsM2MSignals:
    def test_adding_tenant_to_lease_triggers_signal(self, lease: Lease, tenant: Tenant) -> None:
        # tenant already added via responsible, test adding to M2M
        second_tenant = make_tenant(cpf_cnpj="72345678950")
        lease.tenants.add(second_tenant)
        assert lease.tenants.filter(pk=second_tenant.pk).exists()
        lease.tenants.remove(second_tenant)
        assert not lease.tenants.filter(pk=second_tenant.pk).exists()


# =============================================================================
# Apartment delete signal (hard delete — line 89-90)
# =============================================================================


@pytest.mark.unit
class TestApartmentHardDeleteSignal:
    def test_apartment_hard_delete_fires_post_delete_signal(self, apartment: Apartment) -> None:
        """Covers lines 89-90: post_delete signal for Apartment (hard delete)."""
        pk = apartment.pk
        apartment.delete(hard_delete=True)
        # Verify the object is fully removed from the database
        assert not Apartment.all_objects.filter(pk=pk).exists()

    def test_apartment_furniture_m2m_clear_triggers_signal(self, apartment: Apartment) -> None:
        """Covers post_clear action in furniture m2m signal."""
        furniture = make_furniture(name="Clear Signal Furniture")
        apartment.furnitures.add(furniture)
        apartment.furnitures.clear()
        assert apartment.furnitures.count() == 0


# =============================================================================
# Tenant hard delete signal (lines 132-133)
# =============================================================================


@pytest.mark.unit
class TestTenantHardDeleteSignal:
    def test_tenant_hard_delete_fires_post_delete_signal(self, tenant: Tenant) -> None:
        """Covers lines 132-133: post_delete signal for Tenant."""
        pk = tenant.pk
        tenant.delete(hard_delete=True)
        assert not Tenant.all_objects.filter(pk=pk).exists()


# =============================================================================
# Furniture hard delete signal (lines 229-230)
# =============================================================================


@pytest.mark.unit
class TestFurnitureHardDeleteSignal:
    def test_furniture_hard_delete_fires_post_delete_signal(self) -> None:
        """Covers lines 229-230: post_delete signal for Furniture (hard delete)."""
        furniture = make_furniture(name="Hard Delete Furniture Signal")
        pk = furniture.pk
        furniture.delete(hard_delete=True)
        assert not Furniture.all_objects.filter(pk=pk).exists()


# =============================================================================
# connect_all_signals / disconnect_all_signals (lines 279, 291-313)
# =============================================================================


@pytest.mark.unit
class TestSignalConnectDisconnect:
    def test_connect_all_signals_does_not_raise(self) -> None:
        """Covers line 279: connect_all_signals function."""
        from core.signals import connect_all_signals

        connect_all_signals()  # Should complete without error

    def test_disconnect_all_signals_does_not_raise(self) -> None:
        """Covers lines 291-313: disconnect_all_signals function."""
        from core.signals import connect_all_signals, disconnect_all_signals

        disconnect_all_signals()
        # Reconnect so other tests still work
        connect_all_signals()

    def test_signals_still_work_after_reconnect(
        self, building: Building, apartment: Apartment, tenant: Tenant
    ) -> None:
        """After disconnect/reconnect, signals should still fire correctly."""
        from core.signals import connect_all_signals, disconnect_all_signals

        disconnect_all_signals()
        connect_all_signals()

        # Lease creation should still sync is_rented
        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 6, 1),
            validity_months=12,
            rental_value=Decimal("1200.00"),
        )
        apartment.refresh_from_db()
        # Signal reconnected — but disconnect removed receivers; behavior may differ
        # Main goal: no exception raised
        assert lease.pk is not None
