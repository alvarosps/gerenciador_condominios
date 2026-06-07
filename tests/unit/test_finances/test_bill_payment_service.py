"""Session 37 — BillPaymentService tests (partial/total, over-allocation, funded_from, reversal)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from finances.models import Bill, Payment
from finances.services.bill_payment_service import BillPaymentService

from tests.factories import make_bill, make_bill_line_item

pytestmark = pytest.mark.django_db

PAY_DATE = date(2026, 6, 5)


def _bill_with_total(amount: str) -> Bill:
    bill = make_bill()
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


def _amounts(bill: Bill) -> Bill:
    return Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)


def test_total_payment() -> None:
    bill = _bill_with_total("900.00")
    payment = BillPaymentService.pay(bill, PAY_DATE)
    assert payment.amount == Decimal("900.00")
    assert payment.allocations.count() == 1
    assert payment.allocations.first().amount == payment.amount
    annotated = _amounts(bill)
    assert annotated.amount_paid == Decimal("900.00")
    assert annotated.amount_remaining == Decimal("0.00")
    assert annotated.payment_status == "paid"


def test_partial_then_total() -> None:
    bill = _bill_with_total("900.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"))
    mid = _amounts(bill)
    assert mid.payment_status == "partial"
    assert mid.amount_remaining == Decimal("600.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    final = _amounts(bill)
    assert final.payment_status == "paid"
    assert final.amount_paid == Decimal("900.00")


def test_over_allocation_rejected() -> None:
    bill = _bill_with_total("900.00")
    before = Payment.objects.count()
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("1000.00"))
    assert Payment.objects.count() == before
    BillPaymentService.pay(bill, PAY_DATE)  # pay it off
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("1.00"))


def test_non_positive_amount_rejected() -> None:
    bill = _bill_with_total("900.00")
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("0.00"))


def test_funded_from_reserve_persisted_without_reserve_movement() -> None:
    bill = _bill_with_total("300.00")
    payment = BillPaymentService.pay(bill, PAY_DATE, funded_from="reserve")
    assert payment.funded_from == "reserve"
    assert _amounts(bill).payment_status == "paid"


def test_reversal_recomposes_remaining() -> None:
    bill = _bill_with_total("900.00")
    payment = BillPaymentService.pay(bill, PAY_DATE)
    BillPaymentService.unpay(payment)
    assert not Payment.objects.filter(pk=payment.pk).exists()
    assert Payment.objects.with_deleted().filter(pk=payment.pk).exists()
    annotated = _amounts(bill)
    assert annotated.amount_remaining == Decimal("900.00")
    assert annotated.payment_status == "open"
    # paying again after reversal works
    BillPaymentService.pay(bill, PAY_DATE)
    assert _amounts(bill).payment_status == "paid"


def test_split_cash_and_reserve_two_payments() -> None:
    bill = _bill_with_total("900.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("300.00"), funded_from="caixa")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"), funded_from="reserve")
    annotated = _amounts(bill)
    assert annotated.amount_paid == Decimal("900.00")
    assert annotated.payment_status == "paid"
    assert Payment.objects.filter(allocations__bill=bill).distinct().count() == 2


def test_sequential_over_allocation_rejected() -> None:
    bill = _bill_with_total("900.00")
    BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    with pytest.raises(ValidationError):
        BillPaymentService.pay(bill, PAY_DATE, amount=Decimal("600.00"))
    assert _amounts(bill).amount_paid == Decimal("600.00")
