"""Baker-based factory helpers for all core models."""

import itertools
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from model_bakery import baker

User = get_user_model()

TEST_CPFS = [
    "52998224725",
    "11144477735",
    "12345678909",
    "98765432100",
    "45612378901",
    "78901234567",
    "32165498700",
    "65498732100",
    "14725836900",
    "25836914700",
    "36914725800",
    "74185296300",
]

_cpf_cycle = itertools.cycle(TEST_CPFS)


def _next_cpf() -> str:
    return next(_cpf_cycle)


def make_building(street_number: int = 100, user=None, **kwargs):
    defaults = {}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Building", street_number=street_number, **defaults)


def make_apartment(building=None, number: int = 101, user=None, **kwargs):
    if building is None:
        building = make_building(user=user)
    defaults = {
        "rental_value": Decimal("1000.00"),
        "rental_value_double": Decimal("1500.00"),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Apartment", building=building, number=number, **defaults)


def make_tenant(cpf_cnpj: str | None = None, user=None, **kwargs):
    defaults = {
        "cpf_cnpj": cpf_cnpj or _next_cpf(),
        "name": kwargs.pop("name", "Test Tenant"),
        "phone": kwargs.pop("phone", "11999999999"),
        "marital_status": "Solteiro(a)",
        "profession": "Engenheiro",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Tenant", **defaults)


def make_lease(apartment=None, tenant=None, user=None, **kwargs):
    if apartment is None:
        apartment = make_apartment(user=user)
    if tenant is None:
        tenant = make_tenant(user=user)
    defaults = {
        "rental_value": Decimal("1000.00"),
        "start_date": date(2026, 1, 1),
        "validity_months": 12,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Lease", apartment=apartment, responsible_tenant=tenant, **defaults)


def make_person(user=None, **kwargs):
    defaults = {"name": "Test Person"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Person", **defaults)


def make_expense(user=None, **kwargs):
    defaults = {
        "description": "Test Expense",
        "total_amount": Decimal("100.00"),
        "expense_date": date(2026, 1, 15),
        "expense_type": "one_time_expense",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Expense", **defaults)


def make_expense_installment(expense=None, user=None, **kwargs):
    if expense is None:
        expense = make_expense(user=user, is_installment=True)
    defaults = {
        "installment_number": 1,
        "total_installments": 1,
        "amount": expense.total_amount,
        "due_date": date(2026, 2, 15),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.ExpenseInstallment", expense=expense, **defaults)


def make_income(user=None, **kwargs):
    defaults = {
        "description": "Test Income",
        "amount": Decimal("500.00"),
        "income_date": date(2026, 1, 15),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Income", **defaults)


def make_furniture(name: str = "Test Furniture", user=None, **kwargs):
    defaults: dict = {"name": name}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Furniture", **defaults)


def make_dependent(tenant=None, user=None, **kwargs):
    if tenant is None:
        tenant = make_tenant(user=user)
    defaults = {
        "name": "Test Dependent",
        "phone": "11987654321",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Dependent", tenant=tenant, **defaults)


def make_credit_card(person=None, user=None, **kwargs):
    if person is None:
        person = make_person(user=user)
    defaults = {
        "nickname": "Test Card",
        "last_four_digits": "1234",
        "closing_day": 15,
        "due_day": 22,
        "is_active": True,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.CreditCard", person=person, **defaults)


def make_expense_category(name: str = "Test Category", user=None, **kwargs):
    defaults: dict = {"name": name, "color": "#6B7280"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.ExpenseCategory", **defaults)


def make_rent_payment(lease=None, user=None, **kwargs):
    if lease is None:
        lease = make_lease(user=user)
    defaults = {
        "reference_month": date(2026, 3, 1),
        "amount_paid": Decimal("1000.00"),
        "payment_date": date(2026, 3, 5),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.RentPayment", lease=lease, **defaults)


def make_employee_payment(person=None, user=None, **kwargs):
    if person is None:
        person = make_person(user=user)
    defaults = {
        "reference_month": date(2026, 3, 1),
        "base_salary": Decimal("800.00"),
        "variable_amount": Decimal("0.00"),
        "rent_offset": Decimal("0.00"),
        "cleaning_count": 0,
        "is_paid": False,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.EmployeePayment", person=person, **defaults)


def make_person_income(person=None, user=None, **kwargs):
    if person is None:
        person = make_person(user=user)
    defaults = {
        "income_type": "fixed_stipend",
        "fixed_amount": Decimal("1000.00"),
        "start_date": date(2026, 1, 1),
        "is_active": True,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.PersonIncome", person=person, **defaults)


def make_person_payment(person=None, user=None, **kwargs):
    if person is None:
        person = make_person(user=user)
    defaults = {
        "reference_month": date(2026, 3, 1),
        "amount": Decimal("500.00"),
        "payment_date": date(2026, 3, 5),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.PersonPayment", person=person, **defaults)
