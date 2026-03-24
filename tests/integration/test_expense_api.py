"""Integration tests for Expense and ExpenseInstallment API endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import (
    Building,
    CreditCard,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    Person,
)


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
def building(admin_user):
    return Building.objects.create(
        street_number=836,
        name="Edifício Teste",
        address="Rua Teste, 836",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def category(admin_user):
    return ExpenseCategory.objects.create(
        name="Manutenção",
        description="Gastos com manutenção",
        color="#FF5733",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def simple_expense(admin_user, person, category):
    return Expense.objects.create(
        description="Compra de material",
        expense_type="one_time_expense",
        total_amount=Decimal("500.00"),
        expense_date=date(2026, 3, 15),
        person=person,
        category=category,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def card_expense(admin_user, person, credit_card, category):
    return Expense.objects.create(
        description="Compra no cartão",
        expense_type="card_purchase",
        total_amount=Decimal("1200.00"),
        expense_date=date(2026, 3, 10),
        person=person,
        credit_card=credit_card,
        category=category,
        is_installment=True,
        total_installments=6,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def loan_expense(admin_user, person):
    return Expense.objects.create(
        description="Empréstimo Caixa",
        expense_type="bank_loan",
        total_amount=Decimal("24000.00"),
        expense_date=date(2026, 1, 15),
        person=person,
        bank_name="Caixa Econômica",
        interest_rate=Decimal("1.50"),
        is_installment=True,
        total_installments=12,
        is_paid=False,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def paid_expense(admin_user, person):
    return Expense.objects.create(
        description="Gasto já pago",
        expense_type="one_time_expense",
        total_amount=Decimal("100.00"),
        expense_date=date(2026, 2, 1),
        person=person,
        is_paid=True,
        paid_date=date(2026, 2, 1),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def expense_with_installments(card_expense, admin_user):
    for i in range(1, 7):
        ExpenseInstallment.objects.create(
            expense=card_expense,
            installment_number=i,
            total_installments=6,
            amount=Decimal("200.00"),
            due_date=date(2026, 3 + i, 22) if 3 + i <= 12 else date(2027, 3 + i - 12, 22),
            is_paid=False,
            created_by=admin_user,
            updated_by=admin_user,
        )
    return card_expense


@pytest.mark.integration
@pytest.mark.django_db
class TestExpenseAPI:
    url = "/api/expenses/"

    # --- CRUD ---

    def test_list_expenses(self, authenticated_api_client, simple_expense):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["description"] == "Compra de material"

    def test_create_simple_expense(self, authenticated_api_client, person, category):
        data = {
            "description": "Compra de tinta",
            "expense_type": "one_time_expense",
            "total_amount": "350.00",
            "expense_date": "2026-03-20",
            "person_id": person.pk,
            "category_id": category.pk,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["description"] == "Compra de tinta"
        assert response.data["person"]["name"] == "Rodrigo Silva"
        assert response.data["category"]["name"] == "Manutenção"

    def test_create_card_purchase(self, authenticated_api_client, person, credit_card, category):
        data = {
            "description": "TV Samsung",
            "expense_type": "card_purchase",
            "total_amount": "3600.00",
            "expense_date": "2026-03-10",
            "person_id": person.pk,
            "credit_card_id": credit_card.pk,
            "category_id": category.pk,
            "is_installment": True,
            "total_installments": 12,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["credit_card"]["nickname"] == "Nubank"
        assert response.data["is_installment"] is True

    def test_create_bank_loan(self, authenticated_api_client, person):
        data = {
            "description": "Empréstimo pessoal",
            "expense_type": "bank_loan",
            "total_amount": "10000.00",
            "expense_date": "2026-03-01",
            "person_id": person.pk,
            "bank_name": "Banco do Brasil",
            "interest_rate": "2.00",
            "is_installment": True,
            "total_installments": 24,
        }
        response = authenticated_api_client.post(self.url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["bank_name"] == "Banco do Brasil"

    def test_retrieve_expense_with_installments(
        self, authenticated_api_client, expense_with_installments
    ):
        url = f"{self.url}{expense_with_installments.pk}/"
        response = authenticated_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["installments"]) == 6
        assert response.data["remaining_installments"] == 6

    def test_update_expense(self, authenticated_api_client, simple_expense):
        url = f"{self.url}{simple_expense.pk}/"
        data = {
            "description": "Material atualizado",
            "expense_type": "one_time_expense",
            "total_amount": "600.00",
            "expense_date": "2026-03-15",
        }
        response = authenticated_api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "Material atualizado"
        assert response.data["total_amount"] == "600.00"

    def test_delete_expense(self, authenticated_api_client, simple_expense):
        url = f"{self.url}{simple_expense.pk}/"
        response = authenticated_api_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Expense.objects.count() == 0
        assert Expense.objects.with_deleted().count() == 1

    # --- Filters ---

    def test_filter_by_person(self, authenticated_api_client, simple_expense, paid_expense):
        response = authenticated_api_client.get(self.url, {"person_id": simple_expense.person_id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_filter_by_credit_card(self, authenticated_api_client, card_expense, simple_expense):
        response = authenticated_api_client.get(
            self.url, {"credit_card_id": card_expense.credit_card_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["description"] == "Compra no cartão"

    def test_filter_by_expense_type(self, authenticated_api_client, card_expense, simple_expense):
        response = authenticated_api_client.get(self.url, {"expense_type": "card_purchase"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["expense_type"] == "card_purchase"

    def test_filter_by_category(self, authenticated_api_client, simple_expense, paid_expense):
        response = authenticated_api_client.get(
            self.url, {"category_id": simple_expense.category_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_filter_by_building(
        self, authenticated_api_client, building, admin_user, simple_expense
    ):
        building_expense = Expense.objects.create(
            description="Conta de luz",
            expense_type="electricity_bill",
            total_amount=Decimal("250.00"),
            expense_date=date(2026, 3, 10),
            building=building,
            created_by=admin_user,
            updated_by=admin_user,
        )
        response = authenticated_api_client.get(
            self.url, {"building_id": building_expense.building_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["description"] == "Conta de luz"

    def test_filter_by_is_paid(self, authenticated_api_client, simple_expense, paid_expense):
        response = authenticated_api_client.get(self.url, {"is_paid": "false"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["is_paid"] is False

    def test_filter_by_date_range(self, authenticated_api_client, simple_expense, paid_expense):
        response = authenticated_api_client.get(
            self.url, {"date_from": "2026-03-01", "date_to": "2026-03-31"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["description"] == "Compra de material"

    def test_filter_combined(
        self, authenticated_api_client, simple_expense, card_expense, paid_expense
    ):
        response = authenticated_api_client.get(
            self.url,
            {
                "person_id": simple_expense.person_id,
                "expense_type": "one_time_expense",
                "is_paid": "false",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["description"] == "Compra de material"

    # --- Actions ---

    def test_mark_paid(self, authenticated_api_client, simple_expense):
        url = f"{self.url}{simple_expense.pk}/mark_paid/"
        response = authenticated_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_paid"] is True
        assert response.data["paid_date"] is not None

    @freeze_time("2026-03-20")
    def test_mark_paid_with_date(self, authenticated_api_client, simple_expense):
        url = f"{self.url}{simple_expense.pk}/mark_paid/"
        response = authenticated_api_client.post(url, {"paid_date": "2026-03-18"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_paid"] is True
        assert response.data["paid_date"] == "2026-03-18"

    def test_generate_installments(self, authenticated_api_client, loan_expense):
        url = f"{self.url}{loan_expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["installments"]) == 12
        installment_amount = Decimal("24000.00") / 12
        assert Decimal(response.data["installments"][0]["amount"]) == installment_amount
        first_due = response.data["installments"][0]["due_date"]
        assert first_due == "2026-01-15"

    def test_generate_installments_with_credit_card_due_day(
        self, authenticated_api_client, card_expense
    ):
        url = f"{self.url}{card_expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url, {"start_date": "2026-04-01"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["installments"]) == 6
        for inst in response.data["installments"]:
            due = date.fromisoformat(inst["due_date"])
            assert due.day == 22

    def test_generate_installments_already_exist(
        self, authenticated_api_client, expense_with_installments
    ):
        url = f"{self.url}{expense_with_installments.pk}/generate_installments/"
        response = authenticated_api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_generate_installments_not_installment(self, authenticated_api_client, simple_expense):
        url = f"{self.url}{simple_expense.pk}/generate_installments/"
        response = authenticated_api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
@pytest.mark.django_db
class TestExpenseInstallmentAPI:
    url = "/api/expense-installments/"

    # --- CRUD ---

    def test_list_installments(self, authenticated_api_client, expense_with_installments):
        response = authenticated_api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 6

    def test_retrieve_installment(self, authenticated_api_client, expense_with_installments):
        inst = expense_with_installments.installments.first()
        response = authenticated_api_client.get(f"{self.url}{inst.pk}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["installment_number"] == inst.installment_number

    # --- Filters ---

    def test_filter_by_expense(self, authenticated_api_client, expense_with_installments):
        response = authenticated_api_client.get(
            self.url, {"expense_id": expense_with_installments.pk}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 6

    def test_filter_by_is_paid(self, authenticated_api_client, expense_with_installments):
        inst = expense_with_installments.installments.first()
        inst.is_paid = True
        inst.paid_date = date(2026, 4, 22)
        inst.save()

        response = authenticated_api_client.get(self.url, {"is_paid": "false"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 5

    @freeze_time("2026-06-01")
    def test_filter_by_is_overdue(self, authenticated_api_client, expense_with_installments):
        response = authenticated_api_client.get(self.url, {"is_overdue": "true"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] > 0
        for inst in response.data["results"]:
            assert inst["is_overdue"] is True

    def test_filter_by_due_date_range(self, authenticated_api_client, expense_with_installments):
        response = authenticated_api_client.get(
            self.url, {"due_date_from": "2026-04-01", "due_date_to": "2026-06-30"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

    def test_filter_by_person(self, authenticated_api_client, expense_with_installments, person):
        response = authenticated_api_client.get(self.url, {"person_id": person.pk})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 6

    # --- Actions ---

    @freeze_time("2026-04-25")
    def test_mark_paid(self, authenticated_api_client, expense_with_installments):
        inst = expense_with_installments.installments.first()
        url = f"{self.url}{inst.pk}/mark_paid/"
        response = authenticated_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_paid"] is True
        assert response.data["paid_date"] == "2026-04-25"

    def test_mark_paid_completes_expense(self, authenticated_api_client, expense_with_installments):
        installments = list(expense_with_installments.installments.all())
        for inst in installments[:-1]:
            inst.is_paid = True
            inst.paid_date = date(2026, 4, 1)
            inst.save()

        last_inst = installments[-1]
        url = f"{self.url}{last_inst.pk}/mark_paid/"
        response = authenticated_api_client.post(url, {"paid_date": "2026-09-22"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        expense_with_installments.refresh_from_db()
        assert expense_with_installments.is_paid is True

    def test_bulk_mark_paid(self, authenticated_api_client, expense_with_installments):
        installments = list(expense_with_installments.installments.all()[:3])
        ids = [inst.pk for inst in installments]

        url = f"{self.url}bulk_mark_paid/"
        response = authenticated_api_client.post(
            url, {"installment_ids": ids, "paid_date": "2026-04-25"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        for inst_data in response.data:
            assert inst_data["is_paid"] is True

    def test_bulk_mark_paid_completes_expense(
        self, authenticated_api_client, expense_with_installments
    ):
        all_ids = list(expense_with_installments.installments.values_list("pk", flat=True))

        url = f"{self.url}bulk_mark_paid/"
        response = authenticated_api_client.post(
            url, {"installment_ids": all_ids, "paid_date": "2026-04-25"}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        expense_with_installments.refresh_from_db()
        assert expense_with_installments.is_paid is True

    def test_bulk_mark_paid_invalid_ids(self, authenticated_api_client):
        url = f"{self.url}bulk_mark_paid/"
        response = authenticated_api_client.post(
            url, {"installment_ids": [99999], "paid_date": "2026-04-25"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
