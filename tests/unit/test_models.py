"""Tests for core model __str__, properties, soft delete, and AuditMixin."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from core.models import (
    Apartment,
    Building,
    ContractRule,
    Dependent,
    Furniture,
    Landlord,
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

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def building() -> Building:
    return make_building(street_number=999, name="Edifício Teste", address="Rua Teste, 999")


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return make_apartment(building=building, number=101, max_tenants=2)


@pytest.fixture
def tenant() -> Tenant:
    return make_tenant(
        cpf_cnpj="52998224725",
        name="João Teste",
        profession="Engenheiro",
    )


@pytest.fixture
def furniture() -> Furniture:
    return make_furniture(name="Geladeira Teste", description="Frost Free")


# =============================================================================
# Building
# =============================================================================


@pytest.mark.unit
class TestBuildingModel:
    def test_str(self, building: Building) -> None:
        assert str(building) == "Edifício Teste - 999"

    def test_soft_delete(self, building: Building) -> None:
        pk = building.pk
        building.delete()
        assert Building.objects.filter(pk=pk).count() == 0
        assert Building.objects.with_deleted().filter(pk=pk).count() == 1
        assert Building.objects.with_deleted().get(pk=pk).is_deleted is True

    def test_soft_delete_sets_deleted_at(self, building: Building) -> None:
        building.delete()
        building.refresh_from_db()
        assert building.deleted_at is not None

    def test_hard_delete(self, building: Building) -> None:
        pk = building.pk
        building.delete(hard_delete=True)
        assert Building.objects.with_deleted().filter(pk=pk).count() == 0

    def test_restore(self, building: Building) -> None:
        building.delete()
        building.restore()
        assert building.is_deleted is False
        assert building.deleted_at is None

    def test_deleted_only_manager(self, building: Building) -> None:
        building.delete()
        assert Building.objects.deleted_only().filter(pk=building.pk).count() == 1

    def test_audit_mixin_created_at(self, building: Building) -> None:
        assert building.created_at is not None

    def test_audit_mixin_updated_at_changes_on_save(self, building: Building) -> None:
        original_updated_at = building.updated_at
        building.name = "Novo Nome"
        building.save()
        building.refresh_from_db()
        assert building.updated_at >= original_updated_at


# =============================================================================
# Apartment
# =============================================================================


@pytest.mark.unit
class TestApartmentModel:
    def test_str(self, apartment: Apartment) -> None:
        assert str(apartment) == "Apto 101 - 999"

    def test_default_is_rented_false(self, apartment: Apartment) -> None:
        assert apartment.is_rented is False

    def test_soft_delete(self, apartment: Apartment) -> None:
        pk = apartment.pk
        apartment.delete()
        assert Apartment.objects.filter(pk=pk).count() == 0
        assert Apartment.objects.with_deleted().filter(pk=pk, is_deleted=True).count() == 1


# =============================================================================
# Furniture
# =============================================================================


@pytest.mark.unit
class TestFurnitureModel:
    def test_str(self, furniture: Furniture) -> None:
        assert str(furniture) == "Geladeira Teste"

    def test_soft_delete(self, furniture: Furniture) -> None:
        pk = furniture.pk
        furniture.delete()
        assert Furniture.objects.filter(pk=pk).count() == 0
        assert Furniture.objects.with_deleted().filter(pk=pk).count() == 1


# =============================================================================
# Tenant
# =============================================================================


@pytest.mark.unit
class TestTenantModel:
    def test_str(self, tenant: Tenant) -> None:
        assert str(tenant) == "João Teste"

    def test_clean_validates_cpf(self, tenant: Tenant) -> None:
        tenant.cpf_cnpj = "000.000.000-00"
        with pytest.raises(ValidationError) as exc_info:
            tenant.clean()
        assert "cpf_cnpj" in exc_info.value.message_dict

    def test_clean_validates_cnpj_for_company(self) -> None:
        company = Tenant(
            name="Empresa Teste",
            cpf_cnpj="00000000000000",  # invalid CNPJ
            is_company=True,
            phone="11987654321",
            marital_status="Solteiro(a)",
            profession="Empresa",
        )
        with pytest.raises(ValidationError) as exc_info:
            company.clean()
        assert "cpf_cnpj" in exc_info.value.message_dict

    def test_soft_delete(self, tenant: Tenant) -> None:
        pk = tenant.pk
        tenant.delete()
        assert Tenant.objects.filter(pk=pk).count() == 0


# =============================================================================
# Dependent
# =============================================================================


@pytest.mark.unit
class TestDependentModel:
    def test_str(self, tenant: Tenant) -> None:
        dep = make_dependent(tenant=tenant, name="Maria Teste", phone="11987654322")
        assert str(dep) == "Maria Teste (dependente de João Teste)"

    def test_soft_delete(self, tenant: Tenant) -> None:
        dep = make_dependent(tenant=tenant, name="Maria Teste", phone="11987654322")
        pk = dep.pk
        dep.delete()
        assert Dependent.objects.filter(pk=pk).count() == 0
        assert Dependent.objects.with_deleted().filter(pk=pk).count() == 1


# =============================================================================
# Lease
# =============================================================================


@pytest.mark.unit
class TestLeaseModel:
    def test_str(self, apartment: Apartment, tenant: Tenant) -> None:
        lease = make_lease(
            apartment=apartment,
            tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        assert str(lease) == "Locação do Apto 101 - 999"

    def test_soft_delete_sets_is_rented_false(self, apartment: Apartment, tenant: Tenant) -> None:
        lease = make_lease(
            apartment=apartment,
            tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
            rental_value=Decimal("1500.00"),
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        lease.delete()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_clean_validates_lease_dates(self, apartment: Apartment, tenant: Tenant) -> None:
        # Start date more than 10 years in the past
        lease = Lease(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2000, 1, 1),
            validity_months=12,
        )
        with pytest.raises(ValidationError) as exc_info:
            lease.clean()
        assert "start_date" in exc_info.value.message_dict


# =============================================================================
# Landlord
# =============================================================================


@pytest.fixture
def landlord() -> Landlord:
    return Landlord.objects.create(
        name="Proprietário Teste",
        marital_status="Casado(a)",
        cpf_cnpj="52998224725",
        phone="11987654321",
        street="Rua das Flores",
        street_number="123",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01234-567",
    )


@pytest.mark.unit
class TestLandlordModel:
    def test_str(self, landlord: Landlord) -> None:
        assert str(landlord) == "Proprietário Teste"

    def test_full_address_without_complement(self, landlord: Landlord) -> None:
        address = landlord.full_address
        assert "Rua das Flores 123" in address
        assert "Centro" in address
        assert "São Paulo" in address
        assert "SP" in address
        assert "01234-567" in address
        assert "Complemento" not in address or landlord.complement == ""

    def test_full_address_with_complement(self, landlord: Landlord) -> None:
        landlord.complement = "Apto 5"
        landlord.save()
        assert "Apto 5" in landlord.full_address

    def test_get_active(self, landlord: Landlord) -> None:
        active = Landlord.get_active()
        assert active is not None
        assert active.pk == landlord.pk

    def test_only_one_active_landlord(self, landlord: Landlord) -> None:
        second = Landlord.objects.create(
            name="Proprietário 2",
            marital_status="Solteiro(a)",
            cpf_cnpj="11144477735",
            phone="11912345678",
            street="Rua B",
            street_number="456",
            neighborhood="Bairro B",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="20000-000",
            is_active=True,
        )
        landlord.refresh_from_db()
        assert landlord.is_active is False
        assert second.is_active is True

    def test_soft_delete(self, landlord: Landlord) -> None:
        pk = landlord.pk
        landlord.delete()
        assert Landlord.objects.filter(pk=pk).count() == 0


# =============================================================================
# ContractRule
# =============================================================================


@pytest.mark.unit
class TestContractRuleModel:
    def test_str_short_content(self) -> None:
        rule = ContractRule.objects.create(
            content="Não fumar nas áreas comuns.",
            order=1,
        )
        assert str(rule) == "Não fumar nas áreas comuns."

    def test_str_truncates_long_content(self) -> None:
        long_content = "A" * 100
        rule = ContractRule.objects.create(content=long_content, order=2)
        assert len(str(rule)) <= 53  # 50 chars + "..."

    def test_str_strips_html_tags(self) -> None:
        rule = ContractRule.objects.create(
            content="<strong>Proibido pets</strong>",
            order=3,
        )
        assert "<strong>" not in str(rule)
        assert "Proibido pets" in str(rule)

    def test_get_active_rules(self) -> None:
        ContractRule.objects.create(content="<p>Regra ativa</p>", order=1, is_active=True)
        ContractRule.objects.create(content="<p>Regra inativa</p>", order=2, is_active=False)
        rules = ContractRule.get_active_rules()
        assert any("Regra ativa" in r for r in rules)
        assert all("Regra inativa" not in r for r in rules)


# =============================================================================
# SoftDeleteManager
# =============================================================================


@pytest.mark.unit
class TestSoftDeleteManager:
    def test_with_deleted_includes_all(self) -> None:
        b1 = make_building(street_number=777, name="Predio A", address="Rua A")
        b2 = make_building(street_number=778, name="Predio B", address="Rua B")
        b1.delete()
        all_pks = set(Building.objects.with_deleted().values_list("pk", flat=True))
        assert b1.pk in all_pks
        assert b2.pk in all_pks

    def test_deleted_only_excludes_active(self) -> None:
        b = make_building(street_number=779, name="Predio C", address="Rua C")
        pk = b.pk
        b.delete()
        deleted = Building.objects.deleted_only()
        assert deleted.filter(pk=pk).exists()
        # Active buildings should not appear
        active = make_building(street_number=780, name="Predio D", address="Rua D")
        assert not deleted.filter(pk=active.pk).exists()

    def test_restore_with_user(self, django_user_model: type) -> None:
        user = django_user_model.objects.create_user(username="restoreruser", password="pass")
        b = make_building(street_number=781, name="Predio E", address="Rua E")
        b.delete()
        b.restore(restored_by=user)
        b.refresh_from_db()
        assert b.is_deleted is False
        assert b.updated_by == user
