"""Session 36 — Bill.objects.with_amounts(today) annotation tests (design §4.4).

amount_total (Σ non-offset − Σ offset), amount_paid (Σ allocations), amount_remaining,
payment_status, is_overdue — all ORM annotations, with the anti-cartesian guarantee.
"""

from datetime import date
from decimal import Decimal

import pytest

from finances.models import Bill, BillLifecycleState
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_payment,
    make_payment_allocation,
)

pytestmark = pytest.mark.django_db

TODAY = date(2026, 7, 1)


def _amounts(bill: Bill, today: date = TODAY) -> Bill:
    return Bill.objects.with_amounts(today).get(pk=bill.pk)


def test_amount_total_offset_subtracted() -> None:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal("600.00"), is_offset=False)
    make_bill_line_item(bill=bill, amount=Decimal("400.00"), is_offset=False)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=True)
    assert _amounts(bill).amount_total == Decimal("900.00")


def test_amount_total_offset_equal_keeps_non_negative() -> None:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=False)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=True)
    assert _amounts(bill).amount_total == Decimal("0.00")


def test_no_cartesian_inflation_with_lines_and_allocations() -> None:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal("600.00"))
    make_bill_line_item(bill=bill, amount=Decimal("400.00"))
    make_bill_line_item(bill=bill, amount=Decimal("100.00"), is_offset=True)
    payment = make_payment(condominium=bill.condominium)
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal("300.00"))
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal("200.00"))
    annotated = _amounts(bill)
    assert annotated.amount_total == Decimal("900.00")
    assert annotated.amount_paid == Decimal("500.00")
    assert annotated.amount_remaining == Decimal("400.00")
    assert annotated.payment_status == "partial"


def test_amount_paid_excludes_soft_deleted_allocation() -> None:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal("500.00"))
    payment = make_payment(condominium=bill.condominium)
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal("300.00"))
    dead = make_payment_allocation(payment=payment, bill=bill, amount=Decimal("100.00"))
    dead.delete()  # soft delete excluded
    assert _amounts(bill).amount_paid == Decimal("300.00")


def test_payment_status_open_partial_paid() -> None:
    open_bill = make_bill()
    make_bill_line_item(bill=open_bill, amount=Decimal("900.00"))
    assert _amounts(open_bill).payment_status == "open"

    partial_bill = make_bill()
    make_bill_line_item(bill=partial_bill, amount=Decimal("900.00"))
    p1 = make_payment(condominium=partial_bill.condominium)
    make_payment_allocation(payment=p1, bill=partial_bill, amount=Decimal("300.00"))
    assert _amounts(partial_bill).payment_status == "partial"

    paid_bill = make_bill()
    make_bill_line_item(bill=paid_bill, amount=Decimal("900.00"))
    p2 = make_payment(condominium=paid_bill.condominium)
    make_payment_allocation(payment=p2, bill=paid_bill, amount=Decimal("900.00"))
    annotated = _amounts(paid_bill)
    assert annotated.payment_status == "paid"
    assert annotated.amount_remaining == Decimal("0.00")


def test_is_overdue_true_when_unpaid_past_due_and_active() -> None:
    bill = make_bill(due_date=date(2026, 6, 10), lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("900.00"))
    assert _amounts(bill, TODAY).is_overdue is True


def test_is_overdue_false_when_fully_paid() -> None:
    bill = make_bill(due_date=date(2026, 6, 10))
    make_bill_line_item(bill=bill, amount=Decimal("900.00"))
    payment = make_payment(condominium=bill.condominium)
    make_payment_allocation(payment=payment, bill=bill, amount=Decimal("900.00"))
    assert _amounts(bill, TODAY).is_overdue is False


def test_is_overdue_false_when_not_yet_due() -> None:
    bill = make_bill(due_date=date(2026, 8, 1))
    make_bill_line_item(bill=bill, amount=Decimal("900.00"))
    assert _amounts(bill, TODAY).is_overdue is False


def test_is_overdue_false_for_non_active_states() -> None:
    for state in (
        BillLifecycleState.SUSPENDED,
        BillLifecycleState.DEFERRED,
        BillLifecycleState.CANCELED,
    ):
        bill = make_bill(due_date=date(2026, 6, 10), lifecycle_state=state)
        make_bill_line_item(bill=bill, amount=Decimal("900.00"))
        assert _amounts(bill, TODAY).is_overdue is False


def test_soft_deleted_bill_excluded_from_with_amounts() -> None:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    bill.delete()
    assert not Bill.objects.with_amounts(TODAY).filter(pk=bill.pk).exists()


def test_bill_without_line_items_is_zero_and_open() -> None:
    bill = make_bill()
    annotated = _amounts(bill)
    assert annotated.amount_total == Decimal("0.00")
    assert annotated.amount_paid == Decimal("0.00")
    assert annotated.amount_remaining == Decimal("0.00")
    assert annotated.payment_status == "open"
