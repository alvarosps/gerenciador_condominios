"""Session 37 — BillService.create_with_lines tests (atomicity, offset, normalization)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from finances.models import Bill, BillBehavior, InstallmentPlanState
from finances.services.bill_generation_service import BillGenerationService
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import BillDraft, BillService
from finances.services.installment_plan_service import InstallmentPlanService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_condominium,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


def _create(cond, lines, *, user=None, **draft_kwargs):
    draft_defaults = {
        "condominium": cond,
        "competence_month": date(2026, 6, 1),
        "due_date": date(2026, 6, 10),
        "description": "Conta avulsa",
        "behavior": BillBehavior.ONE_TIME,
    }
    draft_defaults.update(draft_kwargs)
    return BillService.create_with_lines(BillDraft(**draft_defaults), lines, user=user)


def test_create_with_two_lines_sums_total() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [
            {"description": "Consumo", "amount": Decimal("600.00")},
            {"description": "Extra", "amount": Decimal("400.00")},
        ],
    )
    assert bill.line_items.count() == 2
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1000.00")


def test_offset_line_is_subtracted() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [
            {"description": "A", "amount": Decimal("600.00")},
            {"description": "B", "amount": Decimal("400.00")},
            {"description": "Desconto", "amount": Decimal("100.00"), "is_offset": True},
        ],
    )
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("900.00")


def test_negative_line_rolls_back_whole_bill() -> None:
    cond = make_condominium()
    before = Bill.all_objects.count()
    with pytest.raises(ValidationError):
        _create(
            cond,
            [
                {"description": "Ok", "amount": Decimal("100.00")},
                {"description": "Ruim", "amount": Decimal("-1.00")},
            ],
        )
    assert Bill.all_objects.count() == before


def test_competence_month_normalized_to_day_one() -> None:
    cond = make_condominium()
    bill = _create(cond, [], competence_month=date(2026, 6, 15))
    assert bill.competence_month == date(2026, 6, 1)


def test_one_time_bill_persists_identifier_and_notes() -> None:
    cond = make_condominium()
    bill = _create(
        cond,
        [{"description": "X", "amount": Decimal("50.00")}],
        external_identifier="NF-123",
        notes="obs",
    )
    bill.refresh_from_db()
    assert bill.billing_account_id is None
    assert bill.behavior == BillBehavior.ONE_TIME
    assert bill.external_identifier == "NF-123"
    assert bill.notes == "obs"


def test_empty_lines_allowed() -> None:
    cond = make_condominium()
    bill = _create(cond, [])
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("0.00")


def test_user_propagated_to_bill_and_lines() -> None:
    cond = make_condominium()
    user = User.objects.create(username="creator")
    bill = _create(cond, [{"description": "X", "amount": Decimal("50.00")}], user=user)
    assert bill.created_by_id == user.id
    assert bill.updated_by_id == user.id
    line = bill.line_items.first()
    assert line is not None
    assert line.created_by_id == user.id


# --- B4: a Bill with a live payment (total OR partial) cannot be deleted — unpay first ---


def test_delete_rejects_fully_paid_bill() -> None:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    BillPaymentService.pay(bill, date(2026, 6, 5))
    with pytest.raises(ValidationError):
        BillService.delete(bill)
    assert Bill.objects.filter(pk=bill.pk).exists()  # not soft-deleted


def test_delete_rejects_partially_paid_bill() -> None:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    BillPaymentService.pay(bill, date(2026, 6, 5), amount=Decimal("100.00"))
    with pytest.raises(ValidationError):
        BillService.delete(bill)
    assert Bill.objects.filter(pk=bill.pk).exists()


def test_delete_allowed_after_unpay() -> None:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    payment = BillPaymentService.pay(bill, date(2026, 6, 5))
    BillPaymentService.unpay(payment)
    BillService.delete(bill)
    assert not Bill.objects.filter(pk=bill.pk).exists()


def test_delete_allowed_for_unpaid_bill() -> None:
    bill = make_bill(competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal("300.00"))
    BillService.delete(bill)
    assert not Bill.objects.filter(pk=bill.pk).exists()


# --- B8d: deleting a Bill materialized from an Installment must revert the plan so
# generation can recreate the parcela — otherwise it is orphaned forever ---


def test_delete_standalone_installment_bill_reverts_plan_to_active() -> None:
    plan = make_installment_plan(
        embedded=False,
        installment_count=1,
        start_due_date=date(2026, 6, 10),
        default_due_day=10,
    )
    InstallmentPlanService.materialize_schedule(plan)
    bills = BillGenerationService.ensure_month_bills(2026, 6)
    plan.refresh_from_db()
    assert plan.lifecycle_state == InstallmentPlanState.MATERIALIZED
    bill = next(b for b in bills if b.installment is not None)

    BillService.delete(bill)

    plan.refresh_from_db()
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE
    # generation can now recreate the parcela Bill for the same month
    regenerated = BillGenerationService.ensure_month_bills(2026, 6)
    assert any(b.installment_id == plan.installments.get().id for b in regenerated)
