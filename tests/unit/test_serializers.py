"""Tests for serializers — validation, nested read/write, financial serializers."""

from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Apartment,
    Building,
    CreditCard,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    ExpenseType,
    Furniture,
    Income,
    Person,
    RentPayment,
    Tenant,
)
from core.serializers import (
    ApartmentSerializer,
    ExpenseCategorySerializer,
    ExpenseInstallmentSerializer,
    ExpenseSerializer,
    IncomeSerializer,
    PersonIncomeSerializer,
    PersonSerializer,
    RentPaymentSerializer,
    TenantSerializer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def building(admin_user) -> Building:
    return Building.objects.create(
        street_number=501,
        name="Edifício Serializer",
        address="Rua Serializer, 501",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building: Building, admin_user) -> Apartment:
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user) -> Tenant:
    return Tenant.objects.create(
        name="Tenant Serializer",
        cpf_cnpj="52998224725",
        phone="11987654321",
        marital_status="Solteiro(a)",
        profession="Dev",
    )


@pytest.fixture
def person(admin_user) -> Person:
    return Person.objects.create(
        name="Person Serializer",
        relationship="Filho",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def credit_card(person: Person, admin_user) -> CreditCard:
    return CreditCard.objects.create(
        person=person,
        nickname="Nubank",
        last_four_digits="1234",
        closing_day=5,
        due_day=12,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category(admin_user) -> ExpenseCategory:
    return ExpenseCategory.objects.create(
        name="Alimentação Serializer",
        color="#FF5733",
        created_by=admin_user,
        updated_by=admin_user,
    )


# =============================================================================
# ApartmentSerializer
# =============================================================================


@pytest.mark.unit
class TestApartmentSerializer:
    def test_read_returns_nested_building(self, apartment: Apartment) -> None:
        data = ApartmentSerializer(apartment).data
        assert isinstance(data["building"], dict)
        assert data["building"]["street_number"] == 501

    def test_read_building_id_not_in_output(self, apartment: Apartment) -> None:
        data = ApartmentSerializer(apartment).data
        assert "building_id" not in data

    def test_write_uses_building_id(self, building: Building) -> None:
        payload = {
            "building_id": building.pk,
            "number": 202,
            "rental_value": "1800.00",
            "max_tenants": 3,
        }
        serializer = ApartmentSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        apt = serializer.save()
        assert apt.building_id == building.pk

    def test_create_with_furniture_ids(self, building: Building) -> None:
        f1 = Furniture.objects.create(name="Sofa Serializer")
        payload = {
            "building_id": building.pk,
            "number": 203,
            "rental_value": "1600.00",
            "max_tenants": 2,
            "furniture_ids": [f1.pk],
        }
        serializer = ApartmentSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        apt = serializer.save()
        assert apt.furnitures.filter(pk=f1.pk).exists()

    def test_update_furniture_ids(self, apartment: Apartment) -> None:
        f1 = Furniture.objects.create(name="TV Serializer")
        serializer = ApartmentSerializer(
            apartment, data={"furniture_ids": [f1.pk]}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        assert apartment.furnitures.filter(pk=f1.pk).exists()

    def test_update_no_furniture_ids_keeps_existing(self, apartment: Apartment) -> None:
        f1 = Furniture.objects.create(name="Microwave Serializer")
        apartment.furnitures.set([f1])
        # Update without furniture_ids — should keep existing
        serializer = ApartmentSerializer(
            apartment, data={"rental_value": "1700.00"}, partial=True
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        assert apartment.furnitures.filter(pk=f1.pk).exists()


# =============================================================================
# TenantSerializer
# =============================================================================


@pytest.mark.unit
class TestTenantSerializer:
    def test_valid_cpf_passes(self) -> None:
        payload = {
            "name": "Test CPF",
            "cpf_cnpj": "529.982.247-25",
            "is_company": False,
            "phone": "11987654321",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
        }
        serializer = TenantSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_cpf_fails_validation(self) -> None:
        payload = {
            "name": "Test Invalid CPF",
            "cpf_cnpj": "000.000.000-00",
            "is_company": False,
            "phone": "11987654321",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
        }
        serializer = TenantSerializer(data=payload)
        assert not serializer.is_valid()
        # The TenantSerializer validate() raises non_field_errors for cpf/cnpj
        assert "non_field_errors" in serializer.errors or "cpf_cnpj" in serializer.errors

    def test_valid_cnpj_for_company_passes(self) -> None:
        payload = {
            "name": "Empresa LTDA",
            "cpf_cnpj": "11.222.333/0001-81",
            "is_company": True,
            "phone": "11987654321",
            "marital_status": "Solteiro(a)",
            "profession": "Empresa",
        }
        serializer = TenantSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_cnpj_for_company_fails(self) -> None:
        payload = {
            "name": "Empresa Inválida",
            "cpf_cnpj": "00.000.000/0000-00",
            "is_company": True,
            "phone": "11987654321",
            "marital_status": "Solteiro(a)",
            "profession": "Empresa",
        }
        serializer = TenantSerializer(data=payload)
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors or "cpf_cnpj" in serializer.errors

    def test_create_with_dependents(self) -> None:
        payload = {
            "name": "Tenant Dep",
            "cpf_cnpj": "98765432100",
            "is_company": False,
            "phone": "11987654321",
            "marital_status": "Casado(a)",
            "profession": "Dev",
            "dependents": [{"name": "Child 1", "phone": "11987654399"}],
        }
        serializer = TenantSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        tenant = serializer.save()
        assert tenant.dependents.count() == 1

    def test_update_removes_deleted_dependents(self, tenant: Tenant) -> None:
        from core.models import Dependent

        dep = Dependent.objects.create(
            tenant=tenant, name="Old Dep", phone="11987654399"
        )
        # Update providing empty dependents list — should remove old
        serializer = TenantSerializer(
            tenant,
            data={"dependents": []},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        assert not Dependent.objects.filter(pk=dep.pk).exists()

    def test_update_existing_dependent(self, tenant: Tenant) -> None:
        from core.models import Dependent

        dep = Dependent.objects.create(
            tenant=tenant, name="Existing Dep", phone="11987654399"
        )
        serializer = TenantSerializer(
            tenant,
            data={
                "dependents": [{"id": dep.pk, "name": "Updated Dep", "phone": "11987654399"}]
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        dep.refresh_from_db()
        assert dep.name == "Updated Dep"

    def test_invalid_phone_fails(self) -> None:
        payload = {
            "name": "Bad Phone",
            "cpf_cnpj": "04628375835",
            "is_company": False,
            "phone": "not-a-phone",
            "marital_status": "Solteiro(a)",
            "profession": "Dev",
        }
        serializer = TenantSerializer(data=payload)
        assert not serializer.is_valid()
        assert "phone" in serializer.errors


# =============================================================================
# ExpenseSerializer
# =============================================================================


@pytest.mark.unit
class TestExpenseSerializer:
    def test_card_purchase_requires_credit_card(self, person: Person) -> None:
        payload = {
            "description": "Compra sem cartão",
            "expense_type": "card_purchase",
            "total_amount": "500.00",
            "expense_date": "2026-01-01",
            "person_id": person.pk,
            # no credit_card_id
        }
        serializer = ExpenseSerializer(data=payload)
        assert not serializer.is_valid()
        assert "credit_card_id" in serializer.errors

    def test_bank_loan_requires_person(self, credit_card: CreditCard) -> None:
        payload = {
            "description": "Empréstimo sem pessoa",
            "expense_type": "bank_loan",
            "total_amount": "5000.00",
            "expense_date": "2026-01-01",
            # no person_id
        }
        serializer = ExpenseSerializer(data=payload)
        assert not serializer.is_valid()
        assert "person_id" in serializer.errors

    def test_water_bill_requires_building(self) -> None:
        payload = {
            "description": "Conta água sem prédio",
            "expense_type": "water_bill",
            "total_amount": "200.00",
            "expense_date": "2026-01-01",
        }
        serializer = ExpenseSerializer(data=payload)
        assert not serializer.is_valid()
        assert "building_id" in serializer.errors

    def test_installment_requires_total_installments(self, person: Person, credit_card: CreditCard) -> None:
        payload = {
            "description": "Parcelado sem total",
            "expense_type": "card_purchase",
            "total_amount": "600.00",
            "expense_date": "2026-01-01",
            "person_id": person.pk,
            "credit_card_id": credit_card.pk,
            "is_installment": True,
            # no total_installments
        }
        serializer = ExpenseSerializer(data=payload)
        assert not serializer.is_valid()
        assert "total_installments" in serializer.errors

    def test_recurring_requires_expected_monthly_amount(self) -> None:
        payload = {
            "description": "Recorrente sem valor mensal",
            "expense_type": "fixed_expense",
            "total_amount": "150.00",
            "expense_date": "2026-01-01",
            "is_recurring": True,
            # no expected_monthly_amount
        }
        serializer = ExpenseSerializer(data=payload)
        assert not serializer.is_valid()
        assert "expected_monthly_amount" in serializer.errors

    def test_get_remaining_installments(self, person: Person, credit_card: CreditCard) -> None:
        expense = Expense.objects.create(
            description="Test Expense",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("300.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            credit_card=credit_card,
            is_installment=True,
            total_installments=3,
        )
        ExpenseInstallment.objects.create(
            expense=expense, installment_number=1, total_installments=3,
            amount=Decimal("100.00"), due_date=date(2026, 2, 1), is_paid=True
        )
        ExpenseInstallment.objects.create(
            expense=expense, installment_number=2, total_installments=3,
            amount=Decimal("100.00"), due_date=date(2026, 3, 1), is_paid=False
        )
        ExpenseInstallment.objects.create(
            expense=expense, installment_number=3, total_installments=3,
            amount=Decimal("100.00"), due_date=date(2026, 4, 1), is_paid=False
        )
        data = ExpenseSerializer(expense).data
        assert data["remaining_installments"] == 2
        assert data["total_paid"] == "100.00"
        assert data["total_remaining"] == "200.00"

    def test_get_remaining_installments_zero_when_none(self, person: Person) -> None:
        expense = Expense.objects.create(
            description="No Installments",
            expense_type=ExpenseType.ONE_TIME_EXPENSE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 1, 1),
            person=person,
        )
        data = ExpenseSerializer(expense).data
        assert data["remaining_installments"] == 0
        assert data["total_paid"] == "0"
        assert data["total_remaining"] == "0"


# =============================================================================
# ExpenseInstallmentSerializer
# =============================================================================


@pytest.mark.unit
class TestExpenseInstallmentSerializer:
    def test_is_overdue_true_for_past_unpaid(self, person: Person, credit_card: CreditCard) -> None:
        expense = Expense.objects.create(
            description="Overdue Test",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            expense_date=date(2025, 1, 1),
            person=person,
            credit_card=credit_card,
            is_installment=True,
            total_installments=1,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense, installment_number=1, total_installments=1,
            amount=Decimal("100.00"), due_date=date(2020, 1, 1), is_paid=False
        )
        data = ExpenseInstallmentSerializer(inst).data
        assert data["is_overdue"] is True

    def test_is_overdue_false_for_paid(self, person: Person, credit_card: CreditCard) -> None:
        expense = Expense.objects.create(
            description="Paid Test",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            expense_date=date(2025, 1, 1),
            person=person,
            credit_card=credit_card,
            is_installment=True,
            total_installments=1,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense, installment_number=1, total_installments=1,
            amount=Decimal("100.00"), due_date=date(2020, 1, 1),
            is_paid=True, paid_date=date(2020, 1, 10)
        )
        data = ExpenseInstallmentSerializer(inst).data
        assert data["is_overdue"] is False

    def test_is_overdue_false_for_future(self, person: Person, credit_card: CreditCard) -> None:
        expense = Expense.objects.create(
            description="Future Test",
            expense_type=ExpenseType.CARD_PURCHASE,
            total_amount=Decimal("100.00"),
            expense_date=date(2026, 1, 1),
            person=person,
            credit_card=credit_card,
            is_installment=True,
            total_installments=1,
        )
        inst = ExpenseInstallment.objects.create(
            expense=expense, installment_number=1, total_installments=1,
            amount=Decimal("100.00"), due_date=date(2099, 12, 31), is_paid=False
        )
        data = ExpenseInstallmentSerializer(inst).data
        assert data["is_overdue"] is False


# =============================================================================
# ExpenseCategorySerializer
# =============================================================================


@pytest.mark.unit
class TestExpenseCategorySerializer:
    def test_subcategories_empty_for_root(self, category: ExpenseCategory) -> None:
        data = ExpenseCategorySerializer(category).data
        assert data["subcategories"] == []

    def test_subcategories_returned_for_parent(
        self, category: ExpenseCategory, admin_user
    ) -> None:
        sub = ExpenseCategory.objects.create(
            name="Sub Alimentação",
            color="#FF0000",
            parent=category,
            created_by=admin_user,
            updated_by=admin_user,
        )
        data = ExpenseCategorySerializer(category).data
        assert len(data["subcategories"]) == 1
        assert data["subcategories"][0]["id"] == sub.pk

    def test_parent_id_write_only(self, category: ExpenseCategory) -> None:
        data = ExpenseCategorySerializer(category).data
        assert "parent_id" not in data


# =============================================================================
# RentPaymentSerializer
# =============================================================================


@pytest.mark.unit
class TestRentPaymentSerializer:
    def test_reference_month_must_be_first_day(
        self, apartment: Apartment, tenant: Tenant
    ) -> None:
        from core.models import Lease

        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
        )
        payload = {
            "lease_id": lease.pk,
            "reference_month": "2026-03-15",  # not first day
            "amount_paid": "1500.00",
            "payment_date": "2026-03-15",
        }
        serializer = RentPaymentSerializer(data=payload)
        assert not serializer.is_valid()
        assert "reference_month" in serializer.errors

    def test_valid_reference_month(
        self, apartment: Apartment, tenant: Tenant
    ) -> None:
        from core.models import Lease

        lease = Lease.objects.create(
            apartment=apartment,
            responsible_tenant=tenant,
            start_date=date(2025, 1, 1),
            validity_months=12,
        )
        payload = {
            "lease_id": lease.pk,
            "reference_month": "2026-03-01",
            "amount_paid": "1500.00",
            "payment_date": "2026-03-10",
        }
        serializer = RentPaymentSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors


# =============================================================================
# PersonSerializer
# =============================================================================


@pytest.mark.unit
class TestPersonSerializer:
    def test_credit_cards_returned_in_list(self, person: Person, credit_card: CreditCard) -> None:
        data = PersonSerializer(person).data
        assert "credit_cards" in data
        assert isinstance(data["credit_cards"], list)
        assert len(data["credit_cards"]) == 1
        assert data["credit_cards"][0]["nickname"] == "Nubank"

    def test_credit_cards_empty_when_none(self) -> None:
        person_no_cards = Person.objects.create(name="No Cards Person", relationship="Tio")
        data = PersonSerializer(person_no_cards).data
        assert data["credit_cards"] == []


# =============================================================================
# PersonIncomeSerializer
# =============================================================================


@pytest.mark.unit
class TestPersonIncomeSerializer:
    def test_current_value_for_apartment_rent(
        self, person: Person, apartment: Apartment, admin_user
    ) -> None:
        from core.models import PersonIncome, PersonIncomeType

        income = PersonIncome.objects.create(
            person=person,
            income_type=PersonIncomeType.APARTMENT_RENT,
            apartment=apartment,
            start_date=date(2025, 1, 1),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        data = PersonIncomeSerializer(income).data
        assert data["current_value"] == str(apartment.rental_value)

    def test_current_value_for_fixed_stipend(self, person: Person, admin_user) -> None:
        from core.models import PersonIncome, PersonIncomeType

        income = PersonIncome.objects.create(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            fixed_amount=Decimal("500.00"),
            start_date=date(2025, 1, 1),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        data = PersonIncomeSerializer(income).data
        assert data["current_value"] == "500.00"

    def test_current_value_zero_for_unknown_type(self, person: Person, admin_user) -> None:
        from core.models import PersonIncome, PersonIncomeType

        # apartment_rent without apartment set
        income = PersonIncome.objects.create(
            person=person,
            income_type=PersonIncomeType.APARTMENT_RENT,
            start_date=date(2025, 1, 1),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        data = PersonIncomeSerializer(income).data
        assert data["current_value"] == "0"


# =============================================================================
# IncomeSerializer
# =============================================================================


@pytest.mark.unit
class TestIncomeSerializer:
    def test_read_serializes_nested_fields(self, person: Person, category: ExpenseCategory) -> None:
        income = Income.objects.create(
            description="Test Income",
            amount=Decimal("1000.00"),
            income_date=date(2026, 3, 1),
            person=person,
            category=category,
        )
        data = IncomeSerializer(income).data
        assert data["person"]["name"] == "Person Serializer"
        assert data["category"]["name"] == "Alimentação Serializer"

    def test_write_uses_person_id(self, person: Person) -> None:
        payload = {
            "description": "Income via ID",
            "amount": "500.00",
            "income_date": "2026-03-01",
            "person_id": person.pk,
        }
        serializer = IncomeSerializer(data=payload)
        assert serializer.is_valid(), serializer.errors
        income = serializer.save()
        assert income.person_id == person.pk
