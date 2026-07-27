"""Session 78 — third-party cash impact (design §5/§5.1/§5.2).

The invariant in one sentence: a third-party payment settles the bill WITHOUT taking money
out of the cash; the settlement with the person DOES take it out.

Every expected figure is computed BY HAND in the test (never re-derived from the service's own
formula), all Decimal, no floats. Only freezegun is mocked; ORM and services are real.
"""

import itertools
from datetime import date
from decimal import Decimal
from typing import Any, Protocol, cast

import pytest
from freezegun import freeze_time

from core.models import FinancialSettings, Person
from finances.models import (
    Bill,
    BillLifecycleState,
    FundedFrom,
    PaymentAllocation,
    ThirdPartySettlement,
)
from finances.services.bill_payment_service import BillPaymentService
from finances.services.condo_balance_service import CondoBalanceService
from finances.services.condo_month_close_service import CondoMonthCloseService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_building,
    make_payment,
    make_person,
)

pytestmark = pytest.mark.django_db

JUNE = date(2026, 6, 1)
JULY = date(2026, 7, 1)
_street_numbers = itertools.count(7000)


class _BillRemaining(Protocol):
    amount_remaining: Decimal


def _bill(amount: str, *, condominium: Any = None, building: Any = None) -> Bill:
    bill = make_bill(
        condominium=condominium,
        building=building,
        competence_month=JUNE,
        due_date=date(2026, 6, 10),
        lifecycle_state=BillLifecycleState.ACTIVE,
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount), is_offset=False)
    return bill


def _pay_third_party(bill: Bill, amount: str, person: Person, when: date) -> None:
    """A third party pays an existing condo bill: Payment(THIRD_PARTY, paid_by) + allocation.

    Built directly (not through BillPaymentService.pay, which only learns funded_from
    third_party in S80) so this session's cash assertions do not depend on unwritten code.
    """
    payment = make_payment(
        condominium=bill.condominium,
        payment_date=when,
        amount=Decimal(amount),
        funded_from=FundedFrom.THIRD_PARTY,
        paid_by=person,
    )
    PaymentAllocation.objects.create(payment=payment, bill=bill, amount=Decimal(amount))


def _settle(amount: str, person: Person, when: date, condominium: Any) -> ThirdPartySettlement:
    return ThirdPartySettlement.objects.create(
        condominium=condominium,
        person=person,
        settlement_date=when,
        amount=Decimal(amount),
    )


def _remaining(bill: Bill) -> Decimal:
    # amount_remaining is a with_amounts annotation; django-stubs does not propagate dynamic
    # annotations onto the model instance, so it is read through a Protocol cast (same pattern
    # as BillPaymentService._BillRemaining).
    annotated = cast(_BillRemaining, Bill.objects.with_amounts(date(2026, 6, 15)).get(pk=bill.pk))
    return annotated.amount_remaining


# --- 1/2: the third-party payment settles the bill and leaves the cash alone ----------


@freeze_time("2026-06-15")
def test_third_party_payment_does_not_change_cash() -> None:
    bill = _bill("400.00")
    baseline = CondoBalanceService.cash_change_of_month(2026, 6)
    assert baseline == Decimal("0.00")  # by hand: no cash in, no cash out yet

    _pay_third_party(bill, "400.00", make_person(), date(2026, 6, 7))

    assert CondoBalanceService.cash_change_of_month(2026, 6) == baseline


@freeze_time("2026-06-15")
def test_third_party_payment_settles_the_bill() -> None:
    """The two effects coexist: the bill is paid AND the cash never moved."""
    bill = _bill("400.00")
    assert _remaining(bill) == Decimal("400.00")

    _pay_third_party(bill, "400.00", make_person(), date(2026, 6, 7))

    assert _remaining(bill) == Decimal("0.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("0.00")


# --- 3/4/5: the settlement is a real cash outflow --------------------------------------


@freeze_time("2026-06-15")
def test_settlement_reduces_cash_change_by_its_exact_amount() -> None:
    person = make_person()
    bill = _bill("400.00")
    _pay_third_party(bill, "400.00", person, date(2026, 6, 7))
    baseline = CondoBalanceService.cash_change_of_month(2026, 6)
    assert baseline == Decimal("0.00")

    _settle("250.00", person, date(2026, 6, 20), bill.condominium)

    # by hand: cash in 0.00 - cash out 250.00
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-250.00")


@freeze_time("2026-06-15")
def test_soft_deleted_settlement_stops_counting() -> None:
    person = make_person()
    bill = _bill("400.00")
    _pay_third_party(bill, "400.00", person, date(2026, 6, 7))
    settlement = _settle("250.00", person, date(2026, 6, 20), bill.condominium)
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-250.00")

    settlement.delete()  # soft delete

    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("0.00")


@freeze_time("2026-07-15")
def test_cash_balance_carries_the_settlement_into_the_next_month() -> None:
    # The baseline anchors the walk: without it cash_balance starts AT as_of_month and never
    # walks June (pre-existing _cash_baseline behaviour, not specific to this session).
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("1000.00"), initial_balance_date=JUNE
    )
    person = make_person()
    bill = _bill("400.00")
    _pay_third_party(bill, "400.00", person, date(2026, 6, 7))
    _settle("250.00", person, date(2026, 6, 20), bill.condominium)

    # by hand: baseline 1000.00 + June cash change (-250.00) => 750.00 at the 1st of July
    assert CondoBalanceService.cash_balance(JULY) == Decimal("750.00")


# --- 6/7/8: the wedge, with the KPIs pinned first (the residual alone is vacuous) -------


@freeze_time("2026-06-15")
def test_wedge_with_third_party_purchase_and_settlement() -> None:
    """Key test of the session: a purchase AND a settlement in the same month.

    settlements_out cancels on BOTH sides of the identity, so `assert wedge_ok` alone would
    pass for ANY value (including a wrong one). The concrete KPIs are pinned first.
    """
    person = make_person()
    purchase = _bill("300.00")  # third-party purchase: a Bill that is born paid
    purchase.paid_by_person = person
    purchase.save(update_fields=["paid_by_person"])
    _pay_third_party(purchase, "300.00", person, date(2026, 6, 5))
    _settle("120.00", person, date(2026, 6, 25), purchase.condominium)

    # by hand — competence: revenue 0.00 - expense 300.00 (the purchase is an active Bill)
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-300.00")
    # by hand — cash: in 0.00 - out 120.00 (settlement only; the third-party payment is not cash)
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-120.00")
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.overview(2026, 6)["wedge_ok"] is True


@freeze_time("2026-06-15")
def test_wedge_with_purchase_only() -> None:
    person = make_person()
    purchase = _bill("300.00")
    purchase.paid_by_person = person
    purchase.save(update_fields=["paid_by_person"])
    _pay_third_party(purchase, "300.00", person, date(2026, 6, 5))

    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-300.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("0.00")
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")


@freeze_time("2026-06-15")
def test_wedge_with_settlement_only() -> None:
    person = make_person()
    bill = _bill("300.00")  # keeps a condominium around; competence expense 300.00
    _settle("120.00", person, date(2026, 6, 25), bill.condominium)

    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-300.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-120.00")
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.overview(2026, 6)["wedge_ok"] is True


# --- 9: per-building scope -------------------------------------------------------------


@freeze_time("2026-06-15")
def test_settlements_out_is_zero_when_building_filtered() -> None:
    """The settlement has no building; a building-filtered cash must not subtract it.

    The wedge stays green either way (the term cancels), so only this direct assertion
    catches the bug — design §5.1.
    """
    building = make_building(street_number=next(_street_numbers))
    person = make_person()
    bill = _bill("300.00", condominium=building.condominium, building=building)
    _pay_third_party(bill, "300.00", person, date(2026, 6, 5))
    _settle("120.00", person, date(2026, 6, 25), building.condominium)

    components = CondoBalanceService._components(2026, 6, building.id)
    assert components.settlements_out == Decimal(0)
    assert CondoBalanceService.cash_change_of_month(2026, 6, building.id) == Decimal("0.00")
    # condo-wide, the same settlement DOES come out
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-120.00")


# --- 10: the frozen close ---------------------------------------------------------------


@freeze_time("2026-06-30")
def test_month_close_freezes_cash_balance_with_the_settlement_deducted() -> None:
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("1000.00"), initial_balance_date=JUNE
    )
    person = make_person()
    bill = _bill("400.00")
    _pay_third_party(bill, "400.00", person, date(2026, 6, 7))
    _settle("250.00", person, date(2026, 6, 20), bill.condominium)

    snapshot = CondoMonthCloseService.close(2026, 6)

    # by hand: 1000.00 baseline - 250.00 settlement (the third-party payment never touched cash)
    assert snapshot.cash_balance_end == Decimal("750.00")


# --- 11: regression — a month with nothing third-party is untouched ----------------------


@freeze_time("2026-06-15")
def test_month_without_third_party_activity_is_unchanged() -> None:
    bill = _bill("400.00")
    BillPaymentService.pay(bill, date(2026, 6, 7), Decimal("400.00"), FundedFrom.CAIXA)

    components = CondoBalanceService._components(2026, 6, None)
    assert components.settlements_out == Decimal(0)
    # by hand: competence -400.00; cash out 400.00 caixa-funded
    assert CondoBalanceService.result_of_month(2026, 6) == Decimal("-400.00")
    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("-400.00")
    assert CondoBalanceService._wedge_residual(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.overview(2026, 6)["wedge_ok"] is True


# --- 12: regression-lock — the month comes from settlement_date, never created_at ---------


@freeze_time("2026-06-15")
def test_settlement_counts_by_settlement_date_not_created_at() -> None:
    """Pins the FIELD, not just the behavior: every other test in this file dates its
    settlements inside the frozen month, so created_at and settlement_date coincide there and
    a refactor to created_at would stay green. Here they deliberately differ."""
    person = make_person()
    bill = _bill("400.00")
    _settle("90.00", person, JULY, bill.condominium)  # created in June, dated July

    assert CondoBalanceService.cash_change_of_month(2026, 6) == Decimal("0.00")
    assert CondoBalanceService.cash_change_of_month(2026, 7) == Decimal("-90.00")


@freeze_time("2026-06-15")
def test_settlements_do_not_leak_across_month_edges() -> None:
    """Both month boundaries are exact — 05-31 and 07-01 stay out of June."""
    person = make_person()
    bill = _bill("400.00")
    for when, amount in (
        (date(2026, 5, 31), "50.00"),
        (date(2026, 6, 1), "7.00"),
        (date(2026, 6, 30), "17.00"),
        (date(2026, 7, 1), "70.00"),
    ):
        _settle(amount, person, when, bill.condominium)

    assert CondoBalanceService._components(2026, 5, None).settlements_out == Decimal("50.00")
    assert CondoBalanceService._components(2026, 6, None).settlements_out == Decimal("24.00")
    assert CondoBalanceService._components(2026, 7, None).settlements_out == Decimal("70.00")
