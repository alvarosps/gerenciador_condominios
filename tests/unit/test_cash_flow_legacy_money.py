"""Surgical legacy money fixes in CashFlowService (P2.5).

Two classes of bug, both freezing the wrong number into the immutable MonthSnapshot:
- debt-installment and IPTU aggregations summed offset installments (offsets are
  per-person discounts, NOT real condominium expenses → must filter is_offset=False);
- monthly/projected rent income summed lease.rental_value raw, ignoring a pending rent
  increase active for the month (effective_rental_value is the SSOT).

Plus the projection's "current month" anchor must use the São Paulo date, not UTC.
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time

from core.models import (
    Apartment,
    Building,
    Expense,
    ExpenseInstallment,
    ExpenseType,
    FinancialSettings,
    Lease,
    Tenant,
)
from core.services.cash_flow_service import CashFlowService

pytestmark = pytest.mark.django_db


@pytest.fixture
def building() -> Building:
    return Building.objects.create(street_number=611, name="Legacy CF", address="Rua CF, 611")


@pytest.fixture
def apartment(building: Building) -> Apartment:
    return Apartment.objects.create(
        building=building, number=101, rental_value=Decimal("1500.00"), max_tenants=2
    )


@pytest.fixture
def tenant() -> Tenant:
    return Tenant.objects.create(
        name="CF Legacy Tenant",
        cpf_cnpj="52998224725",
        phone="11987654321",
        marital_status="Solteiro(a)",
        profession="Dev",
        due_day=10,
    )


@pytest.fixture
def lease(apartment: Apartment, tenant: Tenant) -> Lease:
    return Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 1),
        validity_months=24,
        rental_value=Decimal("1500.00"),
    )


def _make_installment(
    *, expense_type: str, is_offset: bool, amount: Decimal, is_debt: bool = False
) -> ExpenseInstallment:
    expense = Expense.objects.create(
        description="Legacy",
        total_amount=amount,
        expense_date=date(2026, 3, 1),
        expense_type=expense_type,
        is_installment=True,
        is_debt_installment=is_debt,
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
# is_offset excluded from debt / IPTU aggregations
# ──────────────────────────────────────────


def test_debt_installments_exclude_offset() -> None:
    """_collect_debt_installments must skip is_offset installments (regression: it summed
    them, doubling the debt figure frozen into the snapshot)."""
    _make_installment(
        expense_type=ExpenseType.CARD_PURCHASE,
        is_debt=True,
        is_offset=False,
        amount=Decimal("100.00"),
    )
    _make_installment(
        expense_type=ExpenseType.CARD_PURCHASE,
        is_debt=True,
        is_offset=True,
        amount=Decimal("999.00"),
    )
    result = CashFlowService.get_monthly_expenses(2026, 3)
    assert result["debt_installments"] == Decimal("100.00")


def test_property_tax_excludes_offset() -> None:
    """_collect_property_tax must skip is_offset IPTU installments."""
    _make_installment(
        expense_type=ExpenseType.PROPERTY_TAX, is_offset=False, amount=Decimal("200.00")
    )
    _make_installment(
        expense_type=ExpenseType.PROPERTY_TAX, is_offset=True, amount=Decimal("888.00")
    )
    result = CashFlowService.get_monthly_expenses(2026, 3)
    assert result["property_tax"] == Decimal("200.00")


# ──────────────────────────────────────────
# effective_rental_value honored in income aggregations
# ──────────────────────────────────────────


def test_monthly_income_uses_effective_rental(lease: Lease) -> None:
    """A pending increase active for March must drive rent_income and the detail's
    rental_value — not the raw lease.rental_value."""
    lease.pending_rental_value = Decimal("1700.00")
    lease.pending_rental_value_date = date(2026, 3, 1)
    lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])

    result = CashFlowService.get_monthly_income(2026, 3)
    assert result["rent_income"] == Decimal("1700.00")
    assert result["rent_details"][0]["rental_value"] == Decimal("1700.00")


def test_projected_income_uses_effective_rental(lease: Lease) -> None:
    """_get_projected_income must use the effective rent for the projected month."""
    lease.pending_rental_value = Decimal("1700.00")
    lease.pending_rental_value_date = date(2026, 6, 1)
    lease.save(update_fields=["pending_rental_value", "pending_rental_value_date"])

    projected = CashFlowService._get_projected_income(2026, 6)
    assert projected == Decimal("1700.00")


def test_effective_equals_raw_without_pending(lease: Lease) -> None:
    """Without a pending increase, effective == raw (non-regression)."""
    result = CashFlowService.get_monthly_income(2026, 3)
    assert result["rent_income"] == Decimal("1500.00")
    assert CashFlowService._get_projected_income(2026, 6) == Decimal("1500.00")


# ──────────────────────────────────────────
# projection anchors on the São Paulo "today"
# ──────────────────────────────────────────


@freeze_time("2026-02-01 01:00:00")
def test_projection_anchor_uses_sp_today(lease: Lease) -> None:
    """At 22:00 SP on Jan 31 (= 01:00 UTC Feb 1) the projection's first month must be
    January (SP), not February (UTC)."""
    FinancialSettings.objects.create(
        initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 1, 1)
    )
    projection = CashFlowService.get_cash_flow_projection(months=1)
    assert projection[0]["year"] == 2026
    assert projection[0]["month"] == 1
