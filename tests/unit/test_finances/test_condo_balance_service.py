"""Session 45 — CondoBalanceService unit tests (design §4.2/§4.3/§4.4/§4.5).

Worked examples (explicit values) for competence result, cash change, reserve zero-sum,
condo-scoped anchored cash, total/overdue, the wedge identity, and the §18 edge cases.
Only freezegun is mocked (today / current month); ORM and services are real.
"""

import itertools
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from finances.models import BillLifecycleState, FundedFrom
from finances.services.bill_payment_service import BillPaymentService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from finances.services.reserve_service import ReserveService
from freezegun import freeze_time

from core.models import FinancialSettings, Person
from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_building,
    make_income_entry,
    make_lease,
    make_rent_payment,
    make_reserve,
    make_reserve_movement,
)

pytestmark = pytest.mark.django_db

JUNE = date(2026, 6, 1)
_street_numbers = itertools.count(1000)


def _collectible_lease(rent: str = "1000.00", *, building=None, paid: bool = False):
    """A non-deleted, owner-less, non-offset lease that is collectible for June 2026."""
    if building is None:
        building = make_building(street_number=next(_street_numbers))
    apartment = make_apartment(building=building)
    lease = make_lease(apartment=apartment, rental_value=Decimal(rent), start_date=date(2026, 1, 1))
    if paid:
        make_rent_payment(lease=lease, reference_month=JUNE, amount_paid=Decimal(rent))
    return lease


def _active_bill_with_amount(amount: str, *, building=None, condominium=None):
    bill = make_bill(
        condominium=condominium,
        building=building,
        competence_month=JUNE,
        lifecycle_state=BillLifecycleState.ACTIVE,
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount), is_offset=False)
    return bill


@freeze_time("2026-06-15")
def test_result_of_month_worked_example() -> None:
    _collectible_lease("1000.00", paid=True)  # received_collectible += 1000
    _collectible_lease("1000.00", paid=False)  # expected_unpaid += 1000
    make_income_entry(amount=Decimal("500.00"), income_date=date(2026, 6, 10))  # income += 500
    _active_bill_with_amount("800.00")  # expense subtracts 800
    # revenue 2500 (received 1000, expected 1000, income 500) minus expense 800 = 1700
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("1700.00")


@freeze_time("2026-06-15")
def test_result_excludes_non_active_bills() -> None:
    _active_bill_with_amount("800.00")  # active, counts
    deferred = make_bill(competence_month=JUNE, lifecycle_state=BillLifecycleState.DEFERRED)
    make_bill_line_item(bill=deferred, amount=Decimal("999.00"))
    suspended = make_bill(competence_month=JUNE, lifecycle_state=BillLifecycleState.SUSPENDED)
    make_bill_line_item(bill=suspended, amount=Decimal("999.00"))
    # only the active 800 is an expense → result = -800
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-800.00")


@freeze_time("2026-06-15")
def test_result_excludes_owner_lease_payment() -> None:
    owner = Person.objects.create(name="Dono")
    apartment = make_apartment()
    apartment.owner = owner
    apartment.save()
    lease = make_lease(apartment=apartment, rental_value=Decimal("1000.00"))
    make_rent_payment(lease=lease, reference_month=JUNE, amount_paid=Decimal("1000.00"))
    # owner-set lease is not collectible → received_collectible filters it out
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("0.00")


@freeze_time("2026-06-15")
def test_cash_change_worked_example() -> None:
    _collectible_lease("1000.00", paid=True)  # cash in += 1000
    make_income_entry(
        amount=Decimal("300.00"),
        income_date=date(2026, 6, 1),
        is_received=True,
        received_date=date(2026, 6, 5),
    )  # cash in += 300
    bill = _active_bill_with_amount("200.00")
    BillPaymentService.pay(
        bill, date(2026, 6, 7), Decimal("200.00"), FundedFrom.CAIXA
    )  # cash out 200
    # 1000 + 300 - 200
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("1100.00")


@freeze_time("2026-06-15")
def test_reserve_funded_payment_is_not_a_cash_outflow() -> None:
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("500.00"), movement_date=JUNE
    )
    bill = _active_bill_with_amount("300.00", condominium=reserve.condominium)
    before = CondoBalanceService.cash_change_of_month(2026, 6)
    BillPaymentService.pay(bill, date(2026, 6, 8), Decimal("300.00"), FundedFrom.RESERVE)
    after = CondoBalanceService.cash_change_of_month(2026, 6)
    # the deposit (cash -500) is the only cash effect; the reserve payment does NOT change cash
    assert before == after == Decimal("-500.00")
    assert CondoBalanceService.reserve_balance(reserve.condominium_id) == Decimal("200.00")


@freeze_time("2026-06-15")
def test_income_competence_and_cash_in_different_months() -> None:
    make_income_entry(
        amount=Decimal("400.00"),
        income_date=date(2026, 1, 20),
        is_received=True,
        received_date=date(2026, 6, 3),
    )
    # competence belongs to January, cash to June — no double counting
    assert CondoBalanceService.result_of_month(2026, 1) == Decimal("400.00")
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("400.00")
    assert CondoBalanceService.cash_change_of_month(2026, 1) == Decimal("0.00")


@freeze_time("2026-06-15")
def test_reserve_transfer_is_zero_sum_on_total_balance() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("1000.00"), initial_balance_date=date(2026, 6, 1)
    )
    reserve = make_reserve()
    before = CondoBalanceService.total_balance(date(2026, 7, 1))
    ReserveService.deposit(reserve, Decimal("500.00"), JUNE)
    after = CondoBalanceService.total_balance(date(2026, 7, 1))
    assert before == after  # cash -500, reserve +500
    assert CondoBalanceService.reserve_balance() == Decimal("500.00")
    # symmetric withdrawal (reserve -> cash) also leaves the total unchanged
    ReserveService.withdraw(reserve, Decimal("500.00"), JUNE)
    assert CondoBalanceService.total_balance(date(2026, 7, 1)) == before
    assert CondoBalanceService.reserve_balance() == Decimal("0.00")


@freeze_time("2026-06-15")
def test_reserve_balance_never_negative_via_guard() -> None:
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("100.00"), movement_date=JUNE
    )
    with pytest.raises(ValidationError):
        ReserveService.withdraw(reserve, Decimal("150.00"), JUNE)
    assert CondoBalanceService.reserve_balance() == Decimal("100.00")  # unchanged


@freeze_time("2026-06-15")
def test_cash_balance_baseline_from_financial_settings() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 3, 1)
    )
    _collectible_lease("700.00", paid=True)  # June cash +700
    # baseline 0 (Mar) + open months Mar..May (0) + June 700, as of first instant of July
    assert CondoBalanceService.cash_balance(date(2026, 7, 1)) == Decimal("700.00")


@freeze_time("2026-06-15")
def test_cash_balance_anchored_on_last_close() -> None:

    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 5, 1)
    )
    _collectible_lease("900.00", paid=True)  # June cash +900
    CondoMonthCloseService.close(2026, 5)  # closes May with cash_balance_end = 0
    # cash at end of June = May close (0) + June change (900); the past is not recomputed
    assert CondoBalanceService.cash_balance(date(2026, 7, 1)) == Decimal("900.00")


@freeze_time("2026-06-15")
def test_cash_balance_can_be_negative() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("0.00"), initial_balance_date=date(2026, 6, 1)
    )
    bill = _active_bill_with_amount("500.00")
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("500.00"), FundedFrom.CAIXA)
    assert CondoBalanceService.cash_balance(date(2026, 7, 1)) == Decimal("-500.00")


@freeze_time("2026-06-15")
def test_total_balance_is_cash_plus_reserve() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("300.00"), initial_balance_date=date(2026, 6, 1)
    )
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("200.00"), movement_date=JUNE
    )
    cash = CondoBalanceService.cash_balance(date(2026, 7, 1))
    reserve_balance = CondoBalanceService.reserve_balance()
    assert CondoBalanceService.total_balance(date(2026, 7, 1)) == cash + reserve_balance


@freeze_time("2026-06-15")
def test_overdue_bills_total_only_remaining_of_overdue_active() -> None:
    overdue = make_bill(
        competence_month=date(2026, 5, 1),
        due_date=date(2026, 6, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
    )
    make_bill_line_item(bill=overdue, amount=Decimal("300.00"))
    # not overdue (future due date)
    future = make_bill(
        competence_month=JUNE, due_date=date(2026, 6, 30), lifecycle_state=BillLifecycleState.ACTIVE
    )
    make_bill_line_item(bill=future, amount=Decimal("999.00"))
    # deferred bill, past due → excluded
    deferred = make_bill(
        competence_month=date(2026, 5, 1),
        due_date=date(2026, 6, 1),
        lifecycle_state=BillLifecycleState.DEFERRED,
    )
    make_bill_line_item(bill=deferred, amount=Decimal("999.00"))
    assert CondoBalanceService.overdue_bills_total() == Decimal("300.00")
    assert CondoBalanceService.overdue_bills_count() == 1


@freeze_time("2026-06-15")
def test_wedge_fully_settled_equals_result() -> None:
    _collectible_lease("1000.00", paid=True)
    bill = _active_bill_with_amount("400.00")
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("400.00"), FundedFrom.CAIXA)
    # nothing pending, no reserve transfers → the two KPIs are exactly equal
    result = CondoBalanceService.result_of_month(2026, 6)
    cash_change = CondoBalanceService.cash_change_of_month(2026, 6)
    assert result == cash_change == Decimal("600.00")
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.overview(2026, 6)["wedge_ok"] is True


@freeze_time("2026-06-15")
def test_wedge_with_pendencies_residual_zero() -> None:
    _collectible_lease("1000.00", paid=False)  # receivable pending
    _active_bill_with_amount("700.00")  # payable pending
    make_reserve_movement(
        reserve=make_reserve(), kind="deposit", amount=Decimal("50.00"), movement_date=JUNE
    )
    # Pin the concrete KPIs so this is NOT a vacuous residual==0 check: a definitional drift in
    # either public method would break these assertions and the now-independent wedge.
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("300.00")  # 1000 unpaid - 700
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-50.00")  # -50 deposit out
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.overview(2026, 6)["wedge_ok"] is True


@freeze_time("2026-06-15")
def test_empty_month_is_zero() -> None:
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.reserve_balance() == Decimal("0.00")
    assert CondoBalanceService.total_balance(date(2026, 7, 1)) == Decimal("0.00")
    assert CondoBalanceService.overdue_bills_total() == Decimal("0.00")


@freeze_time("2026-06-15")
def test_soft_deleted_bill_excluded_from_expense() -> None:
    bill = _active_bill_with_amount("500.00")
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-500.00")
    bill.delete()  # soft delete
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("0.00")


@freeze_time("2026-06-30T23:30:00")
def test_month_boundary_uses_sao_paulo_month() -> None:
    # 2026-06-30 23:30 UTC is already 2026-06-30 20:30 in São Paulo → still June.
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("10.00"), initial_balance_date=date(2026, 6, 1)
    )
    # cash_balance(None) anchors on current_month_sp() == June, not July.
    assert CondoBalanceService.cash_balance() == Decimal("10.00")


@freeze_time("2026-06-15")
def test_building_scoped_figures() -> None:
    building = make_building(street_number=next(_street_numbers))
    other = make_building(street_number=next(_street_numbers))
    make_income_entry(amount=Decimal("200.00"), income_date=date(2026, 6, 5), building=building)
    make_income_entry(amount=Decimal("999.00"), income_date=date(2026, 6, 5), building=other)
    bill = _active_bill_with_amount("80.00", building=building)
    _active_bill_with_amount("999.00", building=other)
    # building-scoped competence: 200 income - 80 expense (the other building is excluded)
    assert CondoBalanceService.result_of_month(2026, 6, building.id) == Decimal("120.00")
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("80.00"), FundedFrom.CAIXA)
    assert CondoBalanceService.cash_change_of_month(2026, 6, building.id) == Decimal("-80.00")
    overdue = make_bill(
        building=building,
        competence_month=date(2026, 5, 1),
        due_date=date(2026, 6, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
    )
    make_bill_line_item(bill=overdue, amount=Decimal("70.00"))
    assert CondoBalanceService.overdue_bills_total(building.id) == Decimal("70.00")
    assert CondoBalanceService.overdue_bills_count(building.id) == 1
    # Reserve/total are condo-level — a per-building overview reports them as None, never a
    # building-cash + whole-condo-reserve mix.
    overview = CondoBalanceService.overview(2026, 6, building.id)
    assert overview["reserve_balance"] is None
    assert overview["total_balance"] is None
    assert overview["cash_change_of_month"] == "-80.00"  # building-scoped figures still present


@freeze_time("2026-06-15")
def test_soft_deleted_reserve_excluded_from_reserve_balance() -> None:
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("500.00"), movement_date=JUNE
    )
    assert CondoBalanceService.reserve_balance() == Decimal("500.00")
    reserve.delete()  # soft delete: its movements must drop out of the balance
    assert CondoBalanceService.reserve_balance() == Decimal("0.00")
    assert CondoBalanceService.total_balance(date(2026, 7, 1)) == Decimal("0.00")


@freeze_time("2026-06-15")
def test_salary_offset_lease_counted_once_as_payroll_not_revenue() -> None:
    # Rosa (design §4.6): a salary-offset lease (850 rent) is EXCLUDED from collectible_leases,
    # so its rent is never revenue; the payroll Bill (base 850 - rent abatement 205 = 645 net)
    # enters as expense exactly once.
    building = make_building(street_number=next(_street_numbers))
    apartment = make_apartment(building=building)
    make_lease(
        apartment=apartment,
        rental_value=Decimal("850.00"),
        is_salary_offset=True,
        start_date=date(2026, 1, 1),
    )
    payroll = make_bill(competence_month=JUNE, lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=payroll, amount=Decimal("850.00"), is_offset=False)  # base
    make_bill_line_item(bill=payroll, amount=Decimal("205.00"), is_offset=True)  # rent abatement
    # 0 revenue (offset lease excluded) - 645 net payroll expense; if rent counted, it would be +205
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-645.00")


@freeze_time("2026-06-15")
def test_reserve_service_rejects_non_positive_amounts() -> None:
    reserve = make_reserve()
    with pytest.raises(ValidationError):
        ReserveService.deposit(reserve, Decimal("0.00"), JUNE)
    with pytest.raises(ValidationError):
        ReserveService.withdraw(reserve, Decimal("-1.00"), JUNE)
