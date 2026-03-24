"""Integration tests for Income, RentPayment, EmployeePayment, PersonIncome API endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import (
    Apartment,
    Building,
    EmployeePayment,
    ExpenseCategory,
    Income,
    Lease,
    Person,
    PersonIncome,
    RentPayment,
    Tenant,
)


@pytest.fixture
def person_income_test(admin_user):
    return Person.objects.create(
        name="Rodrigo Income Test",
        relationship="Proprietário",
        phone="11999990505",
        email="rodrigo_income_test@test.com",
        is_owner=True,
        is_employee=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_person_test(admin_user):
    return Person.objects.create(
        name="Rosa Income Test",
        relationship="Funcionária",
        phone="11988880505",
        email="rosa_income_test@test.com",
        is_owner=False,
        is_employee=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def building_income_test(admin_user):
    return Building.objects.create(
        street_number=9505,
        name="Edifício Income Test",
        address="Rua Teste, 9505",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment_income_test(building_income_test, admin_user):
    return Apartment.objects.create(
        building=building_income_test,
        number=505,
        rental_value=Decimal("1300.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant_income_test(admin_user):
    return Tenant.objects.create(
        name="João Income Test",
        cpf_cnpj="52998224725",
        phone="11977770505",
        marital_status="Solteiro(a)",
        profession="Engenheiro",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease_income_test(apartment_income_test, tenant_income_test, admin_user):
    return Lease.objects.create(
        apartment=apartment_income_test,
        responsible_tenant=tenant_income_test,
        start_date=date(2026, 1, 1),
        validity_months=12,
        tag_fee=Decimal("50.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category_income_test(admin_user):
    return ExpenseCategory.objects.create(
        name="Receita Extra Session05",
        description="Receitas diversas session05",
        color="#00FF05",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def income_obj(admin_user, person_income_test, building_income_test, category_income_test):
    return Income.objects.create(
        description="Receita de lavanderia s05",
        amount=Decimal("200.00"),
        income_date=date(2026, 3, 15),
        person=person_income_test,
        building=building_income_test,
        category=category_income_test,
        is_recurring=False,
        is_received=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def recurring_income_obj(admin_user, person_income_test):
    return Income.objects.create(
        description="Aposentadoria s05",
        amount=Decimal("3500.00"),
        income_date=date(2026, 1, 1),
        person=person_income_test,
        is_recurring=True,
        expected_monthly_amount=Decimal("3500.00"),
        is_received=True,
        received_date=date(2026, 1, 5),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def rent_payment_obj(admin_user, lease_income_test):
    return RentPayment.objects.create(
        lease=lease_income_test,
        reference_month=date(2026, 3, 1),
        amount_paid=Decimal("1300.00"),
        payment_date=date(2026, 3, 10),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_payment_obj(admin_user, employee_person_test):
    return EmployeePayment.objects.create(
        person=employee_person_test,
        reference_month=date(2026, 3, 1),
        base_salary=Decimal("800.00"),
        variable_amount=Decimal("150.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=5,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def person_income_apartment_obj(admin_user, person_income_test, apartment_income_test):
    return PersonIncome.objects.create(
        person=person_income_test,
        income_type="apartment_rent",
        apartment=apartment_income_test,
        start_date=date(2026, 1, 1),
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def person_income_stipend_obj(admin_user, person_income_test):
    return PersonIncome.objects.create(
        person=person_income_test,
        income_type="fixed_stipend",
        fixed_amount=Decimal("1100.00"),
        start_date=date(2026, 1, 1),
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


# =============================================================================
# IncomeViewSet Tests
# =============================================================================


@pytest.mark.django_db
class TestIncomeAPI:
    url = "/api/incomes/"

    def test_list_incomes(self, authenticated_api_client, income_obj):
        response = authenticated_api_client.get(self.url, {"person_id": income_obj.person_id})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        descriptions = [item["description"] for item in results]
        assert "Receita de lavanderia s05" in descriptions

    def test_create_income(
        self,
        authenticated_api_client,
        person_income_test,
        building_income_test,
        category_income_test,
    ):
        data = {
            "description": "Venda de material reciclado s05",
            "amount": "350.00",
            "income_date": "2026-04-01",
            "person_id": person_income_test.pk,
            "building_id": building_income_test.pk,
            "category_id": category_income_test.pk,
            "is_recurring": False,
            "is_received": False,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["description"] == "Venda de material reciclado s05"
        assert response.data["person"]["name"] == "Rodrigo Income Test"

    def test_create_recurring_income(self, authenticated_api_client, person_income_test):
        data = {
            "description": "Aposentadoria mensal s05",
            "amount": "3500.00",
            "income_date": "2026-01-01",
            "person_id": person_income_test.pk,
            "is_recurring": True,
            "expected_monthly_amount": "3500.00",
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_recurring"] is True
        assert response.data["expected_monthly_amount"] == "3500.00"

    def test_filter_by_person(self, authenticated_api_client, income_obj, recurring_income_obj):
        response = authenticated_api_client.get(self.url, {"person_id": income_obj.person_id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 2

    def test_filter_by_is_recurring(
        self, authenticated_api_client, income_obj, recurring_income_obj
    ):
        response = authenticated_api_client.get(
            self.url,
            {"is_recurring": "true", "person_id": income_obj.person_id},
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all(item["is_recurring"] for item in results)

    def test_filter_by_is_received(
        self, authenticated_api_client, income_obj, recurring_income_obj
    ):
        response = authenticated_api_client.get(
            self.url,
            {"is_received": "false", "person_id": income_obj.person_id},
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all(not item["is_received"] for item in results)

    def test_filter_by_date_range(self, authenticated_api_client, income_obj, recurring_income_obj):
        response = authenticated_api_client.get(
            self.url,
            {
                "date_from": "2026-03-01",
                "date_to": "2026-03-31",
                "person_id": income_obj.person_id,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all("2026-03" in item["income_date"] for item in results)

    def test_mark_received(self, authenticated_api_client, income_obj):
        url = f"{self.url}{income_obj.pk}/mark_received/"
        response = authenticated_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_received"] is True
        assert response.data["received_date"] is not None

    def test_mark_received_with_date(self, authenticated_api_client, income_obj):
        url = f"{self.url}{income_obj.pk}/mark_received/"
        response = authenticated_api_client.post(
            url, {"received_date": "2026-03-20"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_received"] is True
        assert response.data["received_date"] == "2026-03-20"


# =============================================================================
# RentPaymentViewSet Tests
# =============================================================================


@pytest.mark.django_db
class TestRentPaymentAPI:
    url = "/api/rent-payments/"

    def test_list_rent_payments(self, authenticated_api_client, rent_payment_obj):
        response = authenticated_api_client.get(self.url, {"lease_id": rent_payment_obj.lease_id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_rent_payment(self, authenticated_api_client, lease_income_test):
        data = {
            "lease_id": lease_income_test.pk,
            "reference_month": "2026-04-01",
            "amount_paid": "1300.00",
            "payment_date": "2026-04-10",
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["amount_paid"] == "1300.00"

    def test_retrieve_with_nested_lease(self, authenticated_api_client, rent_payment_obj):
        url = f"{self.url}{rent_payment_obj.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "lease" in response.data
        lease_data = response.data["lease"]
        assert "apartment" in lease_data
        assert "responsible_tenant" in lease_data

    def test_filter_by_lease(self, authenticated_api_client, rent_payment_obj):
        response = authenticated_api_client.get(self.url, {"lease_id": rent_payment_obj.lease_id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_apartment(
        self, authenticated_api_client, rent_payment_obj, apartment_income_test
    ):
        response = authenticated_api_client.get(
            self.url, {"apartment_id": apartment_income_test.pk}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_building(
        self, authenticated_api_client, rent_payment_obj, building_income_test
    ):
        response = authenticated_api_client.get(self.url, {"building_id": building_income_test.pk})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_month_range(self, authenticated_api_client, rent_payment_obj):
        response = authenticated_api_client.get(
            self.url,
            {
                "month_from": "2026-03-01",
                "month_to": "2026-03-31",
                "lease_id": rent_payment_obj.lease_id,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_duplicate_reference_month(
        self, authenticated_api_client, rent_payment_obj, lease_income_test
    ):
        data = {
            "lease_id": lease_income_test.pk,
            "reference_month": "2026-03-01",
            "amount_paid": "1300.00",
            "payment_date": "2026-03-15",
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# EmployeePaymentViewSet Tests
# =============================================================================


@pytest.mark.django_db
class TestEmployeePaymentAPI:
    url = "/api/employee-payments/"

    def test_list_employee_payments(self, authenticated_api_client, employee_payment_obj):
        response = authenticated_api_client.get(
            self.url, {"person_id": employee_payment_obj.person_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_employee_payment(self, authenticated_api_client, employee_person_test):
        data = {
            "person_id": employee_person_test.pk,
            "reference_month": "2026-04-01",
            "base_salary": "800.00",
            "variable_amount": "200.00",
            "rent_offset": "0.00",
            "cleaning_count": 6,
            "is_paid": False,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["base_salary"] == "800.00"
        assert response.data["variable_amount"] == "200.00"

    def test_total_paid_in_response(self, authenticated_api_client, employee_payment_obj):
        url = f"{self.url}{employee_payment_obj.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_paid"] == "950.00"

    def test_filter_by_person(self, authenticated_api_client, employee_payment_obj):
        response = authenticated_api_client.get(
            self.url, {"person_id": employee_payment_obj.person_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_is_paid(self, authenticated_api_client, employee_payment_obj):
        response = authenticated_api_client.get(
            self.url,
            {"is_paid": "false", "person_id": employee_payment_obj.person_id},
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all(not item["is_paid"] for item in results)

    def test_mark_paid(self, authenticated_api_client, employee_payment_obj):
        url = f"{self.url}{employee_payment_obj.pk}/mark_paid/"
        response = authenticated_api_client.post(url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_paid"] is True
        assert response.data["payment_date"] is not None

    def test_duplicate_reference_month(
        self, authenticated_api_client, employee_payment_obj, employee_person_test
    ):
        data = {
            "person_id": employee_person_test.pk,
            "reference_month": "2026-03-01",
            "base_salary": "800.00",
            "variable_amount": "0.00",
            "rent_offset": "0.00",
            "cleaning_count": 0,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PersonIncomeViewSet Tests
# =============================================================================


@pytest.mark.django_db
class TestPersonIncomeAPI:
    url = "/api/person-incomes/"

    def test_list_person_incomes(self, authenticated_api_client, person_income_apartment_obj):
        response = authenticated_api_client.get(
            self.url, {"person_id": person_income_apartment_obj.person_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_create_apartment_rent(
        self, authenticated_api_client, person_income_test, apartment_income_test
    ):
        data = {
            "person_id": person_income_test.pk,
            "income_type": "apartment_rent",
            "apartment_id": apartment_income_test.pk,
            "start_date": "2026-01-01",
            "is_active": True,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["income_type"] == "apartment_rent"
        assert response.data["apartment"] is not None

    def test_create_fixed_stipend(self, authenticated_api_client, person_income_test):
        data = {
            "person_id": person_income_test.pk,
            "income_type": "fixed_stipend",
            "fixed_amount": "1100.00",
            "start_date": "2026-01-01",
            "is_active": True,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["income_type"] == "fixed_stipend"
        assert response.data["fixed_amount"] == "1100.00"

    def test_current_value_apartment_with_lease(
        self,
        authenticated_api_client,
        person_income_apartment_obj,
        lease_income_test,
    ):
        url = f"{self.url}{person_income_apartment_obj.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["current_value"] == "1300.00"

    def test_current_value_apartment_no_lease(
        self, authenticated_api_client, person_income_apartment_obj, apartment_income_test
    ):
        """Without a lease, current_value returns apartment.rental_value directly."""
        url = f"{self.url}{person_income_apartment_obj.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # rental_value lives on Apartment, so it's always available even without a lease
        assert response.data["current_value"] == str(apartment_income_test.rental_value)

    def test_current_value_fixed_stipend(self, authenticated_api_client, person_income_stipend_obj):
        url = f"{self.url}{person_income_stipend_obj.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["current_value"] == "1100.00"

    def test_filter_by_person(
        self, authenticated_api_client, person_income_apartment_obj, person_income_test
    ):
        response = authenticated_api_client.get(self.url, {"person_id": person_income_test.pk})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 1

    def test_filter_by_income_type(
        self,
        authenticated_api_client,
        person_income_apartment_obj,
        person_income_stipend_obj,
    ):
        response = authenticated_api_client.get(
            self.url,
            {
                "income_type": "apartment_rent",
                "person_id": person_income_apartment_obj.person_id,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all(item["income_type"] == "apartment_rent" for item in results)

    def test_filter_by_is_active(self, authenticated_api_client, person_income_apartment_obj):
        response = authenticated_api_client.get(
            self.url,
            {
                "is_active": "true",
                "person_id": person_income_apartment_obj.person_id,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert len(results) >= 1
        assert all(item["is_active"] for item in results)
