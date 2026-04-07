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


def make_apartment(building=None, number: str = "101", user=None, **kwargs):
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
        "full_name": kwargs.pop("full_name", "Test Tenant"),
        "phone": kwargs.pop("phone", "11999999999"),
        "nationality": "Brasileiro",
        "marital_status": "Solteiro(a)",
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
        "due_day": 5,
        "start_date": date(2026, 1, 1),
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
