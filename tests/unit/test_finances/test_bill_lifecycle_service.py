"""B4 — BillLifecycleService.set_state rejects suspend/cancel on a Bill with a live payment
(total or partial): the Payment/allocation/ReserveMovement would stay live in the cash flow with
no expense behind them. unpay is required first (design §4.4)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from finances.models import Bill, BillLifecycleState
from finances.services.bill_lifecycle_service import BillLifecycleService
from finances.services.bill_payment_service import BillPaymentService
from tests.factories import make_bill, make_bill_line_item

pytestmark = pytest.mark.django_db


def _paid_bill(*, amount: str = "300.00", pay_amount: str | None = None) -> Bill:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    BillPaymentService.pay(
        bill, date(2026, 6, 5), amount=Decimal(pay_amount) if pay_amount else None
    )
    return bill


@pytest.mark.parametrize(
    "target_state", [BillLifecycleState.SUSPENDED, BillLifecycleState.CANCELED]
)
def test_set_state_rejects_fully_paid_bill(target_state: str) -> None:
    bill = _paid_bill()
    with pytest.raises(ValidationError):
        BillLifecycleService.set_state(bill, target_state)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


@pytest.mark.parametrize(
    "target_state", [BillLifecycleState.SUSPENDED, BillLifecycleState.CANCELED]
)
def test_set_state_rejects_partially_paid_bill(target_state: str) -> None:
    bill = _paid_bill(pay_amount="100.00")
    with pytest.raises(ValidationError):
        BillLifecycleService.set_state(bill, target_state)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.ACTIVE


def test_set_state_allowed_after_unpay() -> None:
    bill = _paid_bill()
    payment = bill.allocations.get().payment
    BillPaymentService.unpay(payment)
    BillLifecycleService.set_state(bill, BillLifecycleState.SUSPENDED)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.SUSPENDED


def test_set_state_allowed_for_unpaid_bill() -> None:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    BillLifecycleService.set_state(bill, BillLifecycleState.SUSPENDED)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.SUSPENDED


def test_set_state_defer_allowed_on_partially_paid_bill() -> None:
    """defer is NOT blocked by the paid guard (unlike suspend/cancel): the paid part stays live
    and only amount_remaining is rescheduled by InstallmentPlanService.convert_deferred (B9)."""
    bill = _paid_bill(pay_amount="100.00")
    BillLifecycleService.set_state(bill, BillLifecycleState.DEFERRED)
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.DEFERRED
