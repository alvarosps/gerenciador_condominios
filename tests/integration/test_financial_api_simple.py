"""Integration tests for simple financial API endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from core.models import CreditCard, ExpenseCategory, FinancialSettings, Person


@pytest.fixture
def person_data():
    return {
        "name": "Rodrigo Silva",
        "relationship": "Proprietário",
        "phone": "11999998888",
        "email": "rodrigo@test.com",
        "is_owner": True,
        "is_employee": False,
        "notes": "Test person",
    }


@pytest.fixture
def person(admin_user):
    return Person.objects.create(
        name="Rodrigo Silva",
        relationship="Proprietário",
        phone="11999998888",
        email="rodrigo@test.com",
        is_owner=True,
        is_employee=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def employee_person(admin_user):
    return Person.objects.create(
        name="Rosa Oliveira",
        relationship="Funcionária",
        is_employee=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def credit_card_data(person):
    return {
        "person_id": person.pk,
        "nickname": "Nubank",
        "last_four_digits": "1234",
        "closing_day": 15,
        "due_day": 22,
        "is_active": True,
    }


@pytest.fixture
def credit_card(person, admin_user):
    return CreditCard.objects.create(
        person=person,
        nickname="Nubank",
        last_four_digits="1234",
        closing_day=15,
        due_day=22,
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def inactive_credit_card(person, admin_user):
    return CreditCard.objects.create(
        person=person,
        nickname="Itaú",
        last_four_digits="5678",
        closing_day=10,
        due_day=17,
        is_active=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category_data():
    return {
        "name": "Manutenção",
        "description": "Gastos com manutenção",
        "color": "#FF5733",
    }


@pytest.fixture
def category(admin_user):
    return ExpenseCategory.objects.create(
        name="Manutenção",
        description="Gastos com manutenção",
        color="#FF5733",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestPersonAPI:
    url = "/api/persons/"

    def test_list_persons(self, authenticated_api_client, person):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Rodrigo Silva"

    def test_create_person(self, authenticated_api_client, person_data):
        response = authenticated_api_client.post(self.url, person_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Rodrigo Silva"
        assert response.data["is_owner"] is True
        assert Person.objects.count() == 1

    def test_retrieve_person(self, authenticated_api_client, person):
        response = authenticated_api_client.get(f"{self.url}{person.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Rodrigo Silva"
        assert "credit_cards" in response.data

    def test_update_person(self, authenticated_api_client, person):
        data = {
            "name": "Rodrigo Souza",
            "relationship": "Proprietário",
            "is_owner": True,
            "is_employee": False,
        }
        response = authenticated_api_client.put(f"{self.url}{person.pk}/", data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Rodrigo Souza"

    def test_partial_update_person(self, authenticated_api_client, person):
        response = authenticated_api_client.patch(
            f"{self.url}{person.pk}/",
            {"name": "Rodrigo Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Rodrigo Updated"

    def test_delete_person(self, authenticated_api_client, person):
        response = authenticated_api_client.delete(f"{self.url}{person.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Soft delete — should not appear in default queryset
        assert Person.objects.count() == 0
        assert Person.all_objects.count() == 1

    def test_filter_by_is_owner(self, authenticated_api_client, person, employee_person):
        response = authenticated_api_client.get(f"{self.url}?is_owner=true")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Rodrigo Silva"

    def test_filter_by_is_employee(self, authenticated_api_client, person, employee_person):
        response = authenticated_api_client.get(f"{self.url}?is_employee=true")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Rosa Oliveira"

    def test_search_by_name(self, authenticated_api_client, person, employee_person):
        response = authenticated_api_client.get(f"{self.url}?search=rodrigo")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Rodrigo Silva"


@pytest.mark.integration
@pytest.mark.django_db
class TestCreditCardAPI:
    url = "/api/credit-cards/"

    def test_list_credit_cards(self, authenticated_api_client, credit_card):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["nickname"] == "Nubank"

    def test_create_credit_card(self, authenticated_api_client, credit_card_data):
        response = authenticated_api_client.post(self.url, credit_card_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["nickname"] == "Nubank"
        assert CreditCard.objects.count() == 1

    def test_filter_by_person(self, authenticated_api_client, credit_card, person):
        response = authenticated_api_client.get(f"{self.url}?person_id={person.pk}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_filter_by_is_active(self, authenticated_api_client, credit_card, inactive_credit_card):
        response = authenticated_api_client.get(f"{self.url}?is_active=true")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["nickname"] == "Nubank"

    def test_credit_card_includes_person(self, authenticated_api_client, credit_card):
        response = authenticated_api_client.get(f"{self.url}{credit_card.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert "person" in response.data
        assert response.data["person"]["name"] == "Rodrigo Silva"


@pytest.mark.integration
@pytest.mark.django_db
class TestExpenseCategoryAPI:
    url = "/api/expense-categories/"

    def test_list_categories(self, authenticated_api_client, category):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Manutenção"

    def test_create_category(self, authenticated_api_client, category_data):
        response = authenticated_api_client.post(self.url, category_data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Manutenção"

    def test_update_category(self, authenticated_api_client, category):
        response = authenticated_api_client.put(
            f"{self.url}{category.pk}/",
            {"name": "Reparos", "description": "Reparos gerais", "color": "#333333"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Reparos"

    def test_delete_category(self, authenticated_api_client, category):
        response = authenticated_api_client.delete(f"{self.url}{category.pk}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert ExpenseCategory.objects.count() == 0
        assert ExpenseCategory.all_objects.count() == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestFinancialSettingsAPI:
    url = "/api/financial-settings/current/"

    def test_get_current_creates_default(self, authenticated_api_client):
        assert FinancialSettings.objects.count() == 0
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert FinancialSettings.objects.count() == 1
        assert Decimal(response.data["initial_balance"]) == Decimal("0.00")

    def test_get_current_returns_existing(self, authenticated_api_client):
        FinancialSettings.objects.create(
            initial_balance=Decimal("5000.00"),
            initial_balance_date=date(2026, 1, 1),
            notes="Saldo inicial do condomínio",
        )
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["initial_balance"]) == Decimal("5000.00")
        assert response.data["notes"] == "Saldo inicial do condomínio"

    def test_update_settings(self, authenticated_api_client):
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        response = authenticated_api_client.put(
            self.url,
            {
                "initial_balance": "10000.00",
                "initial_balance_date": "2026-03-01",
                "notes": "Atualizado",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["initial_balance"]) == Decimal("10000.00")

    def test_partial_update_settings(self, authenticated_api_client):
        FinancialSettings.objects.create(
            initial_balance=Decimal("5000.00"),
            initial_balance_date=date(2026, 1, 1),
            notes="Original",
        )
        response = authenticated_api_client.patch(
            self.url,
            {"notes": "Parcialmente atualizado"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "Parcialmente atualizado"
        assert Decimal(response.data["initial_balance"]) == Decimal("5000.00")

    def test_singleton_enforcement(self, authenticated_api_client):
        FinancialSettings.objects.create(
            initial_balance=Decimal("1000.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        # GET should return the same record
        response1 = authenticated_api_client.get(self.url)
        response2 = authenticated_api_client.get(self.url)
        assert response1.data["id"] == response2.data["id"]
        assert FinancialSettings.objects.count() == 1
