"""Integration tests for financial CRUD gaps — scenarios not covered elsewhere."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import (
    Apartment,
    Building,
    CreditCard,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    Income,
    Lease,
    Person,
    PersonIncome,
    PersonPayment,
    RentPayment,
    Tenant,
)


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=9900,
        name="Edifício Financial Gaps",
        address="Rua Financial, 9900",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=401,
        rental_value=Decimal("1400.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Tenant Financial Gaps",
        cpf_cnpj="52998224725",
        phone="11999009900",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
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
        rental_value=Decimal("1400.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def owner_person(admin_user):
    return Person.objects.create(
        name="Dono Financial Gaps",
        relationship="Proprietário",
        phone="11999009901",
        is_owner=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_person(admin_user):
    return Person.objects.create(
        name="Funcionário Financial Gaps",
        relationship="Funcionário",
        phone="11999009902",
        is_employee=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def credit_card(owner_person, admin_user):
    return CreditCard.objects.create(
        person=owner_person,
        nickname="Inter Gaps",
        last_four_digits="9900",
        closing_day=12,
        due_day=19,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def parent_category(admin_user):
    return ExpenseCategory.objects.create(
        name="Habitação",
        description="Despesas de moradia",
        color="#123456",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def income_obj(owner_person, admin_user):
    return Income.objects.create(
        description="Renda extra gaps",
        amount=Decimal("400.00"),
        income_date=date(2026, 3, 10),
        person=owner_person,
        is_recurring=False,
        is_received=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def rent_payment_obj(lease, admin_user):
    return RentPayment.objects.create(
        lease=lease,
        reference_month=date(2026, 3, 1),
        amount_paid=Decimal("1400.00"),
        payment_date=date(2026, 3, 10),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_payment_obj(employee_person, admin_user):
    return EmployeePayment.objects.create(
        person=employee_person,
        reference_month=date(2026, 3, 1),
        base_salary=Decimal("900.00"),
        variable_amount=Decimal("100.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=4,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def person_income_obj(owner_person, apartment, admin_user):
    return PersonIncome.objects.create(
        person=owner_person,
        income_type="apartment_rent",
        apartment=apartment,
        start_date=date(2026, 1, 1),
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


# =============================================================================
# CreditCard — update, delete, toggle is_active
# =============================================================================


@pytest.mark.integration
class TestCreditCardUpdateDelete:
    url = "/api/credit-cards/"

    def test_update_credit_card(self, authenticated_api_client, credit_card, owner_person):
        payload = {
            "person_id": owner_person.pk,
            "nickname": "Inter Atualizado",
            "last_four_digits": "9900",
            "closing_day": 15,
            "due_day": 22,
            "is_active": True,
        }
        response = authenticated_api_client.put(
            f"{self.url}{credit_card.pk}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["nickname"] == "Inter Atualizado"
        assert response.data["closing_day"] == 15

    def test_partial_update_credit_card_toggle_inactive(
        self, authenticated_api_client, credit_card
    ):
        response = authenticated_api_client.patch(
            f"{self.url}{credit_card.pk}/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False

    def test_delete_credit_card(self, authenticated_api_client, credit_card):
        response = authenticated_api_client.delete(f"{self.url}{credit_card.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CreditCard.objects.filter(pk=credit_card.pk).exists()


# =============================================================================
# ExpenseCategory — hierarchy (parent_id)
# =============================================================================


@pytest.mark.integration
class TestExpenseCategoryHierarchy:
    url = "/api/expense-categories/"

    def test_create_child_category_with_parent_id(
        self, authenticated_api_client, parent_category
    ):
        payload = {
            "name": "Condomínio",
            "description": "Taxa de condomínio",
            "color": "#abcdef",
            "parent_id": parent_category.pk,
        }
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Condomínio"
        assert response.data["parent"] == parent_category.pk

    def test_parent_category_shows_subcategories(
        self, authenticated_api_client, parent_category, admin_user
    ):
        child = ExpenseCategory.objects.create(
            name="Reforma",
            parent=parent_category,
            color="#ffffff",
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = authenticated_api_client.get(f"{self.url}{parent_category.pk}/")
        assert response.status_code == status.HTTP_200_OK
        subcategory_ids = [s["id"] for s in response.data["subcategories"]]
        assert child.pk in subcategory_ids

    def test_create_root_category_without_parent(self, authenticated_api_client):
        payload = {"name": "Transporte", "color": "#999999"}
        response = authenticated_api_client.post(self.url, payload, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["parent"] is None


# =============================================================================
# Income — mark_received, update, delete
# =============================================================================


@pytest.mark.integration
class TestIncomeUpdateDelete:
    url = "/api/incomes/"

    def test_update_income(self, authenticated_api_client, income_obj, owner_person):
        payload = {
            "description": "Renda extra atualizada",
            "amount": "500.00",
            "income_date": "2026-04-01",
            "person_id": owner_person.pk,
            "is_recurring": False,
            "is_received": False,
        }
        response = authenticated_api_client.put(
            f"{self.url}{income_obj.pk}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "Renda extra atualizada"
        assert response.data["amount"] == "500.00"

    def test_partial_update_income(self, authenticated_api_client, income_obj):
        response = authenticated_api_client.patch(
            f"{self.url}{income_obj.pk}/",
            {"amount": "450.00"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount"] == "450.00"

    def test_delete_income_soft_deletes(self, authenticated_api_client, income_obj):
        response = authenticated_api_client.delete(f"{self.url}{income_obj.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Income.objects.filter(pk=income_obj.pk).exists()
        assert Income.all_objects.filter(pk=income_obj.pk).exists()

    def test_mark_received_sets_date(self, authenticated_api_client, income_obj):
        response = authenticated_api_client.post(
            f"{self.url}{income_obj.pk}/mark_received/",
            {"received_date": "2026-03-10"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_received"] is True
        assert response.data["received_date"] == "2026-03-10"


# =============================================================================
# RentPayment — update, delete
# =============================================================================


@pytest.mark.integration
class TestRentPaymentUpdateDelete:
    url = "/api/rent-payments/"

    def test_update_rent_payment(
        self, authenticated_api_client, rent_payment_obj, lease
    ):
        payload = {
            "lease_id": lease.pk,
            "reference_month": "2026-03-01",
            "amount_paid": "1450.00",
            "payment_date": "2026-03-12",
        }
        response = authenticated_api_client.put(
            f"{self.url}{rent_payment_obj.pk}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount_paid"] == "1450.00"
        assert response.data["payment_date"] == "2026-03-12"

    def test_partial_update_rent_payment(
        self, authenticated_api_client, rent_payment_obj
    ):
        response = authenticated_api_client.patch(
            f"{self.url}{rent_payment_obj.pk}/",
            {"notes": "Pago com atraso"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "Pago com atraso"

    def test_delete_rent_payment_soft_deletes(
        self, authenticated_api_client, rent_payment_obj
    ):
        response = authenticated_api_client.delete(f"{self.url}{rent_payment_obj.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not RentPayment.objects.filter(pk=rent_payment_obj.pk).exists()
        assert RentPayment.all_objects.filter(pk=rent_payment_obj.pk).exists()


# =============================================================================
# EmployeePayment — mark_paid
# =============================================================================


@pytest.mark.integration
class TestEmployeePaymentMarkPaid:
    url = "/api/employee-payments/"

    def test_mark_paid_with_date(
        self, authenticated_api_client, employee_payment_obj
    ):
        response = authenticated_api_client.post(
            f"{self.url}{employee_payment_obj.pk}/mark_paid/",
            {"payment_date": "2026-03-28"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_paid"] is True
        assert response.data["payment_date"] == "2026-03-28"

    def test_update_employee_payment(
        self, authenticated_api_client, employee_payment_obj, employee_person
    ):
        payload = {
            "person_id": employee_person.pk,
            "reference_month": "2026-03-01",
            "base_salary": "950.00",
            "variable_amount": "150.00",
            "rent_offset": "0.00",
            "cleaning_count": 5,
            "is_paid": False,
        }
        response = authenticated_api_client.put(
            f"{self.url}{employee_payment_obj.pk}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["base_salary"] == "950.00"

    def test_delete_employee_payment(
        self, authenticated_api_client, employee_payment_obj
    ):
        response = authenticated_api_client.delete(
            f"{self.url}{employee_payment_obj.pk}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not EmployeePayment.objects.filter(pk=employee_payment_obj.pk).exists()


# =============================================================================
# PersonIncome — update, delete
# =============================================================================


@pytest.mark.integration
class TestPersonIncomeUpdateDelete:
    url = "/api/person-incomes/"

    def test_update_person_income_fixed_stipend(
        self, authenticated_api_client, owner_person, admin_user
    ):
        pi = PersonIncome.objects.create(
            person=owner_person,
            income_type="fixed_stipend",
            fixed_amount=Decimal("1000.00"),
            start_date=date(2026, 1, 1),
            is_active=True,
            created_by=admin_user,
            updated_by=admin_user,
        )
        payload = {
            "person_id": owner_person.pk,
            "income_type": "fixed_stipend",
            "fixed_amount": "1200.00",
            "start_date": "2026-01-01",
            "is_active": True,
        }
        response = authenticated_api_client.put(
            f"{self.url}{pi.pk}/", payload, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["fixed_amount"] == "1200.00"

    def test_partial_update_person_income(
        self, authenticated_api_client, person_income_obj
    ):
        response = authenticated_api_client.patch(
            f"{self.url}{person_income_obj.pk}/",
            {"is_active": False},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_active"] is False

    def test_delete_person_income_soft_deletes(
        self, authenticated_api_client, person_income_obj
    ):
        response = authenticated_api_client.delete(f"{self.url}{person_income_obj.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not PersonIncome.objects.filter(pk=person_income_obj.pk).exists()
        assert PersonIncome.all_objects.filter(pk=person_income_obj.pk).exists()
