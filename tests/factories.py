"""Baker-based factory helpers for all core models."""

import itertools
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from model_bakery import baker

from core.validators.brazilian import CPFValidator

User = get_user_model()

# A few CPFs that specific tests pin (auth login, uniqueness lookups). Everything else just needs
# "any valid, unique CPF" and uses make_tenant() with the counter-based generator below.
CPF_VALID_PRIMARY = "52998224725"

_cpf_seq = itertools.count(1)
_condominium_seq = itertools.count(1)


def _generate_valid_cpf(seed: int) -> str:
    """Build a CPF with correct check digits from ``seed`` — always valid, never repeats.

    Replaces the old module-global ``itertools.cycle`` over a finite ``TEST_CPFS`` list, whose
    position depended on import/execution order and intermittently recycled values into
    ``Tenant.full_clean`` under the parallel suite (cross-test order flakiness). Reuses the
    official check-digit math from ``core.validators.brazilian`` (DRY).
    """
    base = f"{seed:09d}"
    first = CPFValidator.calculate_checksum_digit(base, 10)
    second = CPFValidator.calculate_checksum_digit(f"{base}{first}", 11)
    return f"{base}{first}{second}"


def _next_cpf() -> str:
    return _generate_valid_cpf(next(_cpf_seq))


def make_condominium(user=None, **kwargs):
    # Unique default name: Condominium.name is unique among active rows
    # (unique_active_condominium_name), so a fixed literal would collide across factory calls.
    defaults = {"name": f"Test Condominium {next(_condominium_seq)}"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Condominium", **defaults)


def make_building(street_number: int = 100, user=None, condominium=None, **kwargs):
    defaults = {}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults.update(kwargs)
    return baker.make(
        "core.Building", street_number=street_number, condominium=condominium, **defaults
    )


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


def make_finance_category(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {"name": "Categoria Teste", "sort_order": 0}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Category", condominium=condominium, **defaults)


def make_billing_account(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "name": "Conta de Água",
        "default_due_day": 10,
        "expected_amount": Decimal("100.00"),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.BillingAccount", condominium=condominium, **defaults)


def make_bill(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "competence_month": date(2026, 6, 1),
        "due_date": date(2026, 6, 10),
        "description": "Conta Teste",
        "behavior": "recurring",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Bill", condominium=condominium, **defaults)


def make_bill_line_item(bill=None, user=None, **kwargs):
    if bill is None:
        bill = make_bill(user=user)
    defaults = {"description": "Linha Teste", "amount": Decimal("100.00"), "is_offset": False}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.BillLineItem", bill=bill, **defaults)


def make_installment_plan(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "description": "Parcelamento Teste",
        "total_amount": Decimal("1200.00"),
        "installment_count": 12,
        "start_due_date": date(2026, 6, 10),
        "default_due_day": 10,
        "embedded": False,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.InstallmentPlan", condominium=condominium, **defaults)


def make_installment(plan=None, user=None, **kwargs):
    if plan is None:
        plan = make_installment_plan(user=user)
    defaults = {"number": 1, "due_date": date(2026, 6, 10), "amount": Decimal("100.00")}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Installment", plan=plan, **defaults)


def make_employee(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "name": "Funcionário Teste",
        "payment_type": "fixed",
        "base_salary": Decimal("2000.00"),
        "default_due_day": 5,
        "is_active": True,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Employee", condominium=condominium, **defaults)


def make_bill_skip(billing_account=None, user=None, **kwargs):
    if billing_account is None:
        billing_account = make_billing_account(user=user)
    defaults = {"reference_month": date(2026, 6, 1)}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.BillSkip", billing_account=billing_account, **defaults)


def make_payment(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "payment_date": date(2026, 6, 5),
        "amount": Decimal("100.00"),
        "funded_from": "caixa",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Payment", condominium=condominium, **defaults)


def make_payment_allocation(payment=None, bill=None, user=None, **kwargs):
    if payment is None:
        payment = make_payment(user=user)
    if bill is None:
        bill = make_bill(user=user)
    defaults = {"amount": Decimal("100.00")}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.PaymentAllocation", payment=payment, bill=bill, **defaults)


def make_reserve(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {"name": "Reserva Teste"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.Reserve", condominium=condominium, **defaults)


def make_reserve_movement(reserve=None, user=None, **kwargs):
    if reserve is None:
        reserve = make_reserve(user=user)
    defaults = {
        "kind": "deposit",
        "amount": Decimal("100.00"),
        "movement_date": date(2026, 6, 5),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.ReserveMovement", reserve=reserve, **defaults)


def make_income_entry(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "description": "Receita Teste",
        "amount": Decimal("100.00"),
        "income_date": date(2026, 6, 5),
        "is_received": False,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.IncomeEntry", condominium=condominium, **defaults)


def make_condo_month_close(condominium=None, user=None, **kwargs):
    if condominium is None:
        condominium = make_condominium(user=user)
    defaults = {
        "reference_month": date(2026, 6, 1),
        "status": "open",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.CondoMonthClose", condominium=condominium, **defaults)


def make_water_statement(bill=None, user=None, **kwargs):
    if bill is None:
        bill = make_bill(user=user)
    defaults = {"consumo_m3": 158}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.WaterBillStatement", bill=bill, **defaults)


def make_electricity_statement(bill=None, user=None, **kwargs):
    if bill is None:
        bill = make_bill(user=user)
    defaults = {"consumo_kwh": 1752}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("finances.ElectricityBillStatement", bill=bill, **defaults)
