"""Tests for core model __str__, properties, soft delete, and AuditMixin."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from core.models import (
    Apartment,
    Building,
    ContractRule,
    Dependent,
    Expense,
    Furniture,
    Landlord,
    Lease,
    RentAdjustment,
    RentPayment,
    Tenant,
)
from core.services.landlord_service import LandlordService
from tests.constants import TEST_PASSWORD
from tests.factories import (
    make_apartment,
    make_building,
    make_dependent,
    make_furniture,
    make_lease,
    make_rent_payment,
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
        # Activation is owned by LandlordService (the model no longer auto-deactivates on save);
        # the partial unique constraint guarantees a single active landlord.
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
            is_active=False,
        )
        LandlordService.activate(second)
        landlord.refresh_from_db()
        second.refresh_from_db()
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
        user = django_user_model.objects.create_user(
            username="restoreruser", password=TEST_PASSWORD
        )
        b = make_building(street_number=781, name="Predio E", address="Rua E")
        b.delete()
        b.restore(restored_by=user)
        b.refresh_from_db()
        assert b.is_deleted is False
        assert b.updated_by == user


@pytest.mark.unit
class TestDefaultManagerSoftDelete:
    """The default manager of every soft-delete model must exclude deleted rows.

    Django elects ``_default_manager`` (used by ALL reverse/related managers) from the
    Meta ``default_manager_name``; without it the first-declared manager (``all_objects``)
    would leak soft-deleted rows through related managers like ``apartment.furnitures``.
    """

    def test_default_manager_is_soft_delete_manager(self) -> None:
        from core.models import Expense, ExpenseInstallment, RentAdjustment
        from core.models import SoftDeleteManager as Manager

        for model in (Furniture, Tenant, Lease, RentAdjustment, Expense, ExpenseInstallment):
            assert isinstance(model._default_manager, Manager), model.__name__

    def test_related_manager_excludes_soft_deleted_furniture(self) -> None:
        apartment = make_apartment()
        keep = make_furniture(name="Sofá Ativo")
        gone = make_furniture(name="Mesa Deletada")
        apartment.furnitures.add(keep, gone)
        gone.delete()

        names = {f.name for f in apartment.furnitures.all()}
        assert names == {"Sofá Ativo"}

    def test_related_manager_excludes_soft_deleted_tenant(self) -> None:
        lease = make_lease()
        responsible = lease.responsible_tenant
        extra = make_tenant(name="Inquilino Extra")
        lease.tenants.add(responsible, extra)
        extra.delete()

        names = {t.name for t in lease.tenants.all()}
        assert extra.name not in names
        assert responsible.name in names

    def test_related_manager_excludes_soft_deleted_rent_adjustment(self) -> None:
        from core.models import RentAdjustment

        lease = make_lease()
        keep = RentAdjustment.objects.create(
            lease=lease,
            adjustment_date=date(2026, 1, 1),
            percentage=Decimal("5.00"),
            previous_value=Decimal("1000.00"),
            new_value=Decimal("1050.00"),
        )
        gone = RentAdjustment.objects.create(
            lease=lease,
            adjustment_date=date(2026, 2, 1),
            percentage=Decimal("3.00"),
            previous_value=Decimal("1050.00"),
            new_value=Decimal("1081.50"),
        )
        gone.delete()

        pks = {ra.pk for ra in lease.rent_adjustments.all()}
        assert pks == {keep.pk}

    def test_all_objects_still_includes_deleted(self) -> None:
        keep = make_furniture(name="Cadeira Viva")
        gone = make_furniture(name="Cadeira Morta")
        gone.delete()

        all_pks = set(Furniture.all_objects.values_list("pk", flat=True))
        assert keep.pk in all_pks
        assert gone.pk in all_pks


# =============================================================================
# AuditMixin.save respects update_fields
# =============================================================================


@pytest.mark.unit
class TestAuditMixinUpdateFields:
    """A partial save (update_fields) must still persist updated_at — the audit trail was
    previously skipped when the caller's update_fields omitted it."""

    def test_save_with_update_fields_persists_updated_at(self, tenant: Tenant) -> None:
        original = Tenant.objects.get(pk=tenant.pk).updated_at
        tenant.warning_count = 7
        tenant.save(update_fields=["warning_count"])
        reloaded = Tenant.objects.get(pk=tenant.pk)
        assert reloaded.updated_at > original
        assert reloaded.warning_count == 7

    def test_save_with_update_fields_does_not_touch_other_fields(self, tenant: Tenant) -> None:
        original_name = tenant.name
        tenant.warning_count = 3
        # Mutate a field NOT in update_fields — it must not be persisted.
        tenant.name = "Nome Que Não Deve Persistir"
        tenant.save(update_fields=["warning_count"])
        reloaded = Tenant.objects.get(pk=tenant.pk)
        assert reloaded.name == original_name
        assert reloaded.warning_count == 3

    def test_full_save_still_updates_updated_at(self, tenant: Tenant) -> None:
        original = Tenant.objects.get(pk=tenant.pk).updated_at
        tenant.warning_count = 9
        tenant.save()
        assert Tenant.objects.get(pk=tenant.pk).updated_at > original


# =============================================================================
# CPF/CNPJ normalization at the single entry point
# =============================================================================


@pytest.mark.unit
class TestCpfCnpjNormalization:
    def test_tenant_cpf_normalized_to_digits_on_save(self) -> None:
        tenant = make_tenant(cpf_cnpj="529.982.247-25")
        assert tenant.cpf_cnpj == "52998224725"
        assert Tenant.objects.get(pk=tenant.pk).cpf_cnpj == "52998224725"

    def test_company_cnpj_normalized_on_save(self) -> None:
        tenant = make_tenant(cpf_cnpj="11.222.333/0001-81", is_company=True)
        assert tenant.cpf_cnpj == "11222333000181"

    def test_formatted_and_raw_cpf_are_same_identity(self) -> None:
        make_tenant(cpf_cnpj="52998224725")
        # Recreating with the formatted form of the same CPF must collide (same identity).
        with pytest.raises((IntegrityError, ValidationError)), transaction.atomic():
            make_tenant(cpf_cnpj="529.982.247-25")

    def test_landlord_cpf_normalized_on_save(self) -> None:
        landlord = Landlord.objects.create(
            name="Locador Normalizado",
            marital_status="Casado(a)",
            cpf_cnpj="529.982.247-25",
            phone="11999990000",
            street="Rua X",
            street_number="1",
            neighborhood="Centro",
            city="São Paulo",
            state="SP",
            zip_code="01000-000",
            is_active=False,
        )
        assert landlord.cpf_cnpj == "52998224725"

    def test_dependent_cpf_normalized_on_save(self) -> None:
        dep = make_dependent(cpf_cnpj="529.982.247-25")
        assert dep.cpf_cnpj == "52998224725"

    def test_dependent_blank_cpf_stays_blank(self) -> None:
        dep = make_dependent(cpf_cnpj="")
        assert dep.cpf_cnpj == ""


# =============================================================================
# Apartment.delete fires sync_apartment_is_rented
# =============================================================================


@pytest.mark.unit
class TestApartmentDeleteCascade:
    def test_apartment_delete_sets_is_rented_false_via_signal(self) -> None:
        lease = make_lease()
        apartment = lease.apartment
        apartment.is_rented = True
        apartment.save(update_fields=["is_rented"])
        lease_updated_before = Lease.objects.get(pk=lease.pk).updated_at

        apartment.delete()

        # Lease soft-deleted, with a fresh updated_at (per-instance delete fired the signal).
        deleted_lease = Lease.all_objects.get(pk=lease.pk)
        assert deleted_lease.is_deleted is True
        assert deleted_lease.updated_at > lease_updated_before
        # is_rented recalculated to False (no active lease remains).
        assert Apartment.all_objects.get(pk=apartment.pk).is_rented is False

    def test_apartment_restore_then_is_rented_consistent(self) -> None:
        lease = make_lease()
        apartment = lease.apartment
        apartment.delete()
        apartment.restore()
        # After restore there is no active lease, so is_rented must not be a stale True.
        assert Apartment.all_objects.get(pk=apartment.pk).is_rented is False


# =============================================================================
# RentPayment.lease PROTECT
# =============================================================================


@pytest.mark.unit
class TestRentPaymentProtect:
    def test_hard_delete_lease_with_payments_is_protected(self) -> None:
        payment = make_rent_payment()
        lease = payment.lease
        with pytest.raises(ProtectedError):
            lease.delete(hard_delete=True)
        # Payment history preserved.
        assert RentPayment.all_objects.filter(pk=payment.pk).exists()

    def test_soft_delete_lease_keeps_payments(self) -> None:
        payment = make_rent_payment()
        lease = payment.lease
        lease.delete()  # soft delete
        assert RentPayment.all_objects.filter(pk=payment.pk).exists()


# =============================================================================
# Expense.clean and money CheckConstraints
# =============================================================================


@pytest.mark.unit
class TestExpenseCleanNonNegative:
    def test_expense_clean_allows_zero(self) -> None:
        expense = Expense(
            description="Conta zerada",
            expense_type="one_time_expense",
            total_amount=Decimal("0.00"),
            expense_date=date(2026, 1, 1),
        )
        expense.full_clean()  # must not raise

    def test_expense_clean_rejects_negative(self) -> None:
        expense = Expense(
            description="Conta negativa",
            expense_type="one_time_expense",
            total_amount=Decimal("-1.00"),
            expense_date=date(2026, 1, 1),
        )
        with pytest.raises(ValidationError):
            expense.full_clean()


@pytest.mark.unit
class TestMoneyCheckConstraints:
    """Negative money values must be rejected at the DB level (CheckConstraints).

    A bulk ``.update()`` is used to bypass ``save()``/``full_clean`` and exercise the DB constraint
    directly (the model's full_clean would otherwise catch it first as a ValidationError).
    """

    def test_lease_tag_fee_negative_rejected_by_db(self) -> None:
        lease = make_lease()
        with pytest.raises(IntegrityError), transaction.atomic():
            Lease.objects.filter(pk=lease.pk).update(tag_fee=Decimal("-1.00"))

    def test_lease_deposit_amount_negative_rejected_by_db(self) -> None:
        lease = make_lease()
        with pytest.raises(IntegrityError), transaction.atomic():
            Lease.objects.filter(pk=lease.pk).update(deposit_amount=Decimal("-1.00"))

    def test_lease_pending_rental_value_negative_rejected_by_db(self) -> None:
        lease = make_lease()
        with pytest.raises(IntegrityError), transaction.atomic():
            Lease.objects.filter(pk=lease.pk).update(pending_rental_value=Decimal("-1.00"))

    def test_rent_adjustment_previous_value_negative_rejected(self) -> None:
        ra = RentAdjustment.objects.create(
            lease=make_lease(),
            adjustment_date=date(2026, 1, 1),
            percentage=Decimal("5.00"),
            previous_value=Decimal("1000.00"),
            new_value=Decimal("1050.00"),
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            RentAdjustment.objects.filter(pk=ra.pk).update(previous_value=Decimal("-1.00"))

    def test_rent_adjustment_new_value_negative_rejected(self) -> None:
        ra = RentAdjustment.objects.create(
            lease=make_lease(),
            adjustment_date=date(2026, 1, 1),
            percentage=Decimal("5.00"),
            previous_value=Decimal("1000.00"),
            new_value=Decimal("1050.00"),
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            RentAdjustment.objects.filter(pk=ra.pk).update(new_value=Decimal("-1.00"))


# =============================================================================
# Landlord single-active invariant + service
# =============================================================================


@pytest.mark.unit
class TestLandlordActivation:
    def _make_landlord(self, *, name: str, cpf: str, is_active: bool) -> Landlord:
        return Landlord.objects.create(
            name=name,
            marital_status="Casado(a)",
            cpf_cnpj=cpf,
            phone="11999990000",
            street="Rua",
            street_number="1",
            neighborhood="Centro",
            city="São Paulo",
            state="SP",
            zip_code="01000-000",
            is_active=is_active,
        )

    def test_activate_deactivates_others(self) -> None:
        first = self._make_landlord(name="L1", cpf="52998224725", is_active=True)
        second = self._make_landlord(name="L2", cpf="11144477735", is_active=False)
        LandlordService.activate(second)
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.is_active is False
        assert second.is_active is True
        assert Landlord.objects.filter(is_active=True).count() == 1

    def test_partial_unique_active_landlord_constraint(self) -> None:
        self._make_landlord(name="L1", cpf="52998224725", is_active=True)
        # A second active landlord must be rejected by the partial unique constraint.
        with pytest.raises(IntegrityError), transaction.atomic():
            self._make_landlord(name="L2", cpf="11144477735", is_active=True)

    def test_activate_sets_updated_at_on_deactivated(self) -> None:
        first = self._make_landlord(name="L1", cpf="52998224725", is_active=True)
        original_updated = Landlord.objects.get(pk=first.pk).updated_at
        second = self._make_landlord(name="L2", cpf="11144477735", is_active=False)
        LandlordService.activate(second)
        first.refresh_from_db()
        assert first.is_active is False
        assert first.updated_at > original_updated
