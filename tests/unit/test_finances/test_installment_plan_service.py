"""Session 41 — InstallmentPlanService.convert_deferred tests (atomic, no dup/loss, terminal)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from finances.models import Bill, BillLifecycleState, InstallmentPlan, InstallmentPlanState
from finances.services.installment_plan_service import InstallmentPlanService, _split_amount
from freezegun import freeze_time

from tests.factories import make_bill, make_bill_line_item

pytestmark = pytest.mark.django_db


def _deferred_bill(amount: str) -> Bill:
    bill = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.DEFERRED)
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time("2026-06-15")
def test_convert_deferred_creates_plan_and_installments() -> None:
    bill = _deferred_bill("1200.00")
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=12,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    assert plan.embedded is False
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE
    assert plan.total_amount == Decimal("1200.00")
    installments = list(plan.installments.order_by("number"))
    assert len(installments) == 12
    assert sum(i.amount for i in installments) == Decimal("1200.00")
    assert installments[0].due_date == date(2026, 7, 10)
    assert installments[1].due_date == date(2026, 8, 10)
    assert installments[11].due_date == date(2027, 6, 10)


@freeze_time("2026-06-15")
def test_convert_deferred_remainder_on_last_installment() -> None:
    bill = _deferred_bill("100.00")
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=3,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    amounts = [i.amount for i in plan.installments.order_by("number")]
    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(amounts) == Decimal("100.00")


@pytest.mark.parametrize(
    ("total", "count"),
    [("0.05", 9), ("0.54", 12), ("0.01", 3), ("100.00", 3), ("1200.00", 12), ("7.00", 24)],
)
def test_split_amount_parts_are_non_negative_and_sum_exact(total: str, count: int) -> None:
    parts = _split_amount(Decimal(total), count)
    assert len(parts) == count
    assert all(part >= Decimal("0.00") for part in parts), (total, count, parts)
    assert sum(parts) == Decimal(total)


@freeze_time("2026-06-15")
def test_convert_deferred_rejects_negative_total() -> None:
    bill = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.DEFERRED)
    make_bill_line_item(bill=bill, amount=Decimal("10.00"), is_offset=False)
    make_bill_line_item(bill=bill, amount=Decimal("50.00"), is_offset=True)  # net total -40
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0  # atomic: nothing created


@freeze_time("2026-08-15")
def test_deferred_bill_becomes_terminal_outside_all_sums() -> None:
    bill = make_bill(
        behavior="one_time", lifecycle_state=BillLifecycleState.DEFERRED, due_date=date(2026, 1, 10)
    )
    make_bill_line_item(bill=bill, amount=Decimal("1200.00"))
    plan = InstallmentPlanService.convert_deferred(
        deferred_bill=bill,
        installment_count=12,
        start_due_date=date(2026, 7, 10),
        default_due_day=10,
    )
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.CANCELED
    # Canceled -> not overdue and not counted; the value migrated whole, never duplicated.
    annotated = Bill.objects.with_amounts(date(2026, 8, 15)).get(pk=bill.pk)
    assert annotated.is_overdue is False
    assert plan.total_amount == Decimal("1200.00")


@freeze_time("2026-06-15")
def test_convert_deferred_count_zero_is_rejected_atomically() -> None:
    bill = _deferred_bill("100.00")
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=0,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0
    bill.refresh_from_db()
    assert bill.lifecycle_state == BillLifecycleState.DEFERRED


@freeze_time("2026-06-15")
def test_convert_deferred_requires_deferred_state() -> None:
    bill = make_bill(behavior="one_time", lifecycle_state=BillLifecycleState.ACTIVE)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    with pytest.raises(ValidationError):
        InstallmentPlanService.convert_deferred(
            deferred_bill=bill,
            installment_count=3,
            start_due_date=date(2026, 7, 10),
            default_due_day=10,
        )
    assert InstallmentPlan.objects.count() == 0
