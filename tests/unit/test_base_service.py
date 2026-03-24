"""Unit tests for core/services/base.py — BaseService CRUD operations."""

from decimal import Decimal

import pytest

from core.models import Building, Tenant
from core.services.base import BaseService


class BuildingService(BaseService[Building]):
    model = Building


class TenantService(BaseService[Tenant]):
    model = Tenant


@pytest.fixture
def building_service():
    return BuildingService()


@pytest.fixture
def tenant_service():
    return TenantService()


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=7701,
        name="Base Service Building",
        address="Rua Base, 7701",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Base Service Tenant",
        cpf_cnpj="11144477735",  # Valid CPF
        phone="11988880001",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=5,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.unit
class TestBaseServiceGetQueryset:
    def test_returns_queryset(self, building_service):
        qs = building_service.get_queryset()
        assert hasattr(qs, "filter")

    def test_includes_soft_deleted_because_uses_default_manager(self, building_service, admin_user):
        # BaseService uses _default_manager which is Building.all_objects (standard Manager)
        # This means get_queryset() returns ALL objects, including soft-deleted ones.
        b = Building.objects.create(
            street_number=7702,
            name="Deleted",
            address="Rua Deleted, 7702",
            created_by=admin_user,
            updated_by=admin_user,
        )
        b.delete()
        qs = building_service.get_queryset()
        # _default_manager is all_objects (Manager), not SoftDeleteManager, so deleted record is visible
        assert qs.filter(pk=b.pk).exists()


@pytest.mark.unit
class TestBaseServiceGetById:
    def test_returns_instance_when_found(self, building_service, building):
        result = building_service.get_by_id(building.pk)
        assert result is not None
        assert result.pk == building.pk

    def test_returns_none_when_not_found(self, building_service):
        result = building_service.get_by_id(999999)
        assert result is None


@pytest.mark.unit
class TestBaseServiceGetAll:
    def test_returns_list(self, building_service, building):
        result = building_service.get_all()
        assert isinstance(result, list)
        assert any(b.pk == building.pk for b in result)


@pytest.mark.unit
class TestBaseServiceCreate:
    def test_creates_and_returns_instance(self, building_service, admin_user):
        instance = building_service.create(
            street_number=7703,
            name="Created Building",
            address="Rua Created, 7703",
            created_by=admin_user,
            updated_by=admin_user,
        )
        assert instance.pk is not None
        assert Building.objects.filter(pk=instance.pk).exists()


@pytest.mark.unit
class TestBaseServiceUpdate:
    def test_updates_field(self, building_service, building):
        updated = building_service.update(building, name="Updated Name")
        assert updated.name == "Updated Name"
        building.refresh_from_db()
        assert building.name == "Updated Name"


@pytest.mark.unit
class TestBaseServiceDelete:
    def test_soft_deletes_instance(self, building_service, admin_user):
        b = Building.objects.create(
            street_number=7704,
            name="To Delete",
            address="Rua Delete, 7704",
            created_by=admin_user,
            updated_by=admin_user,
        )
        building_service.delete(b)
        assert not Building.objects.filter(pk=b.pk).exists()
        assert Building.all_objects.filter(pk=b.pk, is_deleted=True).exists()


@pytest.mark.unit
class TestBaseServiceExists:
    def test_returns_true_when_exists(self, building_service, building):
        assert building_service.exists(building.pk) is True

    def test_returns_false_when_not_exists(self, building_service):
        assert building_service.exists(999999) is False


@pytest.mark.unit
class TestBaseServiceCount:
    def test_returns_integer(self, building_service, building):
        count = building_service.count()
        assert isinstance(count, int)
        assert count >= 1


@pytest.mark.unit
class TestBaseServiceFilter:
    def test_filters_correctly(self, building_service, building):
        results = building_service.filter(street_number=building.street_number)
        assert len(results) == 1
        assert results[0].pk == building.pk

    def test_no_match_returns_empty_list(self, building_service):
        results = building_service.filter(street_number=99999)
        assert results == []
