"""Surgical legacy money fixes in FinancialDashboardService (P2.5).

- IPTU/debt aggregations summed is_offset installments (offsets are per-person discounts,
  not real expenses) — four querysets must filter expense__is_offset=False.
- Income summary summed lease.rental_value raw, ignoring a pending rent increase
  (effective_rental_value is the SSOT).
- A cached GET (get_dashboard_summary / _detail_employee) created EmployeePayment rows;
  carry-forward belongs to MonthAdvanceService at month close, never a read path.
"""

from datetime import date
from decimal import Decimal

import pytest

from core.models import (
    Apartment,
    Building,
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    Lease,
    Person,
    Tenant,
)
from core.services.financial_dashboard_service import FinancialDashboardService
from core.services.month_advance_service import MonthAdvanceService

pytestmark = pytest.mark.django_db

_MONTH_START = date(2026, 3, 1)
_NEXT_MONTH = date(2026, 4, 1)


def _make_iptu_installment(*, is_offset: bool, amount: Decimal, due: date = date(2026, 3, 15)):
    expense = Expense.objects.create(
        description="IPTU",
        expense_type=ExpenseType.PROPERTY_TAX,
        total_amount=amount,
        expense_date=date(2026, 3, 1),
        is_installment=True,
        is_offset=is_offset,
    )
    return ExpenseInstallment.objects.create(
        expense=expense,
        installment_number=1,
        total_installments=1,
        amount=amount,
        due_date=due,
        is_paid=False,
    )


def _make_debt_installment(*, expense_type: str, is_offset: bool, amount: Decimal):
    expense = Expense.objects.create(
        description="Debt",
        expense_type=expense_type,
        total_amount=amount,
        expense_date=date(2026, 3, 1),
        is_installment=True,
        is_debt_installment=True,
        is_offset=is_offset,
    )
    return ExpenseInstallment.objects.create(
        expense=expense,
        installment_number=1,
        total_installments=1,
        amount=amount,
        due_date=date(2026, 3, 15),
    )


# ──────────────────────────────────────────
# is_offset excluded from IPTU / debt aggregations
# ──────────────────────────────────────────


def test_dashboard_iptu_summary_excludes_offset() -> None:
    """_build_expense_summary IPTU total must skip is_offset installments."""
    _make_iptu_installment(is_offset=False, amount=Decimal("200.00"))
    _make_iptu_installment(is_offset=True, amount=Decimal("777.00"))
    summary = FinancialDashboardService._build_expense_summary(
        _MONTH_START, _NEXT_MONTH, 2026, 3, set()
    )
    assert summary["iptu"]["total"] == Decimal("200.00")


def test_dashboard_iptu_detail_excludes_offset() -> None:
    """_detail_iptu in-month total must skip is_offset installments."""
    _make_iptu_installment(is_offset=False, amount=Decimal("200.00"))
    _make_iptu_installment(is_offset=True, amount=Decimal("777.00"))
    detail = FinancialDashboardService._detail_iptu(_MONTH_START, _NEXT_MONTH)
    assert detail["total"] == Decimal("200.00")


def test_dashboard_overdue_iptu_excludes_offset() -> None:
    """_build_overdue_previous_months unpaid IPTU from earlier months must skip offsets."""
    _make_iptu_installment(is_offset=False, amount=Decimal("150.00"), due=date(2026, 2, 10))
    _make_iptu_installment(is_offset=True, amount=Decimal("666.00"), due=date(2026, 2, 10))
    overdue = FinancialDashboardService._build_overdue_previous_months(2026, 3)
    iptu_items = [item for item in overdue if item["type"] == "iptu"]
    assert len(iptu_items) == 1
    assert iptu_items[0]["amount"] == Decimal("150.00")


def test_dashboard_utility_debt_by_building_excludes_offset() -> None:
    """_build_utility_by_building debt installments must skip is_offset installments."""
    _make_debt_installment(
        expense_type=ExpenseType.WATER_BILL, is_offset=False, amount=Decimal("80.00")
    )
    _make_debt_installment(
        expense_type=ExpenseType.WATER_BILL, is_offset=True, amount=Decimal("555.00")
    )
    data = FinancialDashboardService._build_utility_by_building(
        ExpenseType.WATER_BILL, _MONTH_START, _NEXT_MONTH
    )
    debt_total = sum(
        (
            Decimal(str(d["amount"]))
            for entry in data["by_building"]
            for d in entry["debt_installments"]
        ),
        Decimal("0.00"),
    )
    assert debt_total == Decimal("80.00")


# ──────────────────────────────────────────
# effective_rental_value honored in income summary
# ──────────────────────────────────────────


def test_income_summary_uses_effective_rental() -> None:
    """_build_income_summary must use the effective rent for the month (honoring a pending
    increase), not lease.rental_value."""
    building = Building.objects.create(street_number=621, name="Inc", address="Rua Inc, 621")
    apartment = Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
        is_rented=True,
    )
    tenant = Tenant.objects.create(
        name="Inc Tenant",
        cpf_cnpj="52998224725",
        phone="11987654321",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
    )
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=24,
        rental_value=Decimal("1500.00"),
    )
    lease.pending_rental_value = Decimal("1800.00")
    lease.pending_rental_value_date = date(2026, 3, 1)
    lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])

    summary = FinancialDashboardService._build_income_summary(_MONTH_START)
    assert summary["total_monthly_income"] == Decimal("1800.00")
    assert summary["condominium_income"] == Decimal("1800.00")


# ──────────────────────────────────────────
# no EmployeePayment write inside the cached GET
# ──────────────────────────────────────────


def test_dashboard_summary_does_not_create_employee_payments() -> None:
    """get_dashboard_summary must NOT create EmployeePayment in a month that has none
    (regression: _ensure_employee_payments mutated the DB inside a cached read)."""
    employee = Person.objects.create(name="Func", relationship="Funcionário", is_employee=True)
    EmployeePayment.objects.create(
        person=employee,
        reference_month=date(2026, 2, 1),
        base_salary=Decimal("800.00"),
        variable_amount=Decimal("0.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=0,
        is_paid=False,
    )
    before = EmployeePayment.objects.count()
    FinancialDashboardService.get_dashboard_summary(2026, 3)
    assert EmployeePayment.objects.count() == before


def test_detail_employee_does_not_create_payments() -> None:
    """_detail_employee must NOT create EmployeePayment for a month with none."""
    employee = Person.objects.create(name="Func2", relationship="Funcionário", is_employee=True)
    EmployeePayment.objects.create(
        person=employee,
        reference_month=date(2026, 2, 1),
        base_salary=Decimal("900.00"),
        variable_amount=Decimal("0.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=0,
        is_paid=False,
    )
    before = EmployeePayment.objects.count()
    FinancialDashboardService._detail_employee(_MONTH_START)
    assert EmployeePayment.objects.count() == before


def test_month_advance_still_carries_forward() -> None:
    """The correct path (MonthAdvanceService._carry_forward_employee_payments at close)
    still creates next month's EmployeePayment — the read-path removal didn't break it."""
    employee = Person.objects.create(name="Func3", relationship="Funcionário", is_employee=True)
    EmployeePayment.objects.create(
        person=employee,
        reference_month=date(2026, 2, 1),
        base_salary=Decimal("1000.00"),
        variable_amount=Decimal("50.00"),
        rent_offset=Decimal("0.00"),
        cleaning_count=2,
        is_paid=True,
    )
    created = MonthAdvanceService()._carry_forward_employee_payments(
        date(2026, 2, 1), date(2026, 3, 1)
    )
    assert created == 1
    march = EmployeePayment.objects.get(person=employee, reference_month=date(2026, 3, 1))
    assert march.base_salary == Decimal("1000.00")
    assert march.variable_amount == Decimal("0.00")
