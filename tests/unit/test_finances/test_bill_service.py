"""Session 37 — BillService.create_with_lines tests (atomicity, offset, normalization)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from finances.models import Bill, BillBehavior, BillLineItem, InstallmentPlanState
from finances.services.bill_generation_service import BillGenerationService
from finances.services.bill_payment_service import BillPaymentService
from finances.services.bill_service import BillDraft, BillService
from finances.services.installment_plan_service import InstallmentPlanService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condominium,
    make_installment,
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


# --- S69: update_with_lines preserves embedded-installment lines (only replaces installment__isnull=True) ---


def _embedded_installment_bill():
    """A recurring water bill carrying one embedded-parcela line + one seed (non-parcela) line."""
    account = make_billing_account(account_type="water", external_identifier="UC-EMBED")
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
    )
    installment = make_installment(plan=plan, number=3, amount=Decimal("530.24"))
    bill = make_bill(
        billing_account=account,
        competence_month=date(2026, 6, 1),
        behavior=BillBehavior.RECURRING,
    )
    installment_line = make_bill_line_item(
        bill=bill, installment=installment, amount=Decimal("530.24"), description="Parcela 3/59"
    )
    seed_line = make_bill_line_item(
        bill=bill, amount=Decimal("100.00"), description="Consumo (estimado)"
    )
    return bill, installment, installment_line, seed_line


def test_update_with_lines_preserves_installment_lines() -> None:
    bill, _installment, installment_line, seed_line = _embedded_installment_bill()

    BillService.update_with_lines(
        bill,
        [
            {"description": "Consumo A", "amount": Decimal("70.00")},
            {"description": "Consumo B", "amount": Decimal("80.00")},
        ],
    )

    installment_line.refresh_from_db()
    assert installment_line.is_deleted is False
    assert installment_line.pk is not None
    assert BillLineItem.objects.with_deleted().get(pk=seed_line.pk).is_deleted is True
    non_installment_lines = BillLineItem.objects.filter(bill=bill, installment__isnull=True)
    assert non_installment_lines.count() == 2
    assert BillLineItem.objects.filter(bill=bill, installment__isnull=False).count() == 1
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("680.24")  # 70 + 80 + 530.24 (parcela preserved)


def test_update_with_lines_dedups_incoming_installment_line() -> None:
    bill, installment, installment_line, _seed_line = _embedded_installment_bill()

    BillService.update_with_lines(
        bill,
        [
            {
                "description": "Parcela 3/59",
                "amount": Decimal("530.24"),
                "installment": installment,
            },
            {"description": "Consumo", "amount": Decimal("90.00")},
        ],
    )

    assert BillLineItem.objects.filter(bill=bill, installment=installment).count() == 1
    assert BillLineItem.objects.filter(bill=bill, installment=installment).get().pk == (
        installment_line.pk
    )
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("620.24")  # 90 + 530.24 — parcela never doubled


def test_update_with_lines_creates_new_installment_line_when_absent() -> None:
    account = make_billing_account(account_type="water", external_identifier="UC-NEWLINE")
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
    )
    installment = make_installment(plan=plan, number=1, amount=Decimal("200.00"))
    bill = make_bill(
        billing_account=account,
        competence_month=date(2026, 6, 1),
        behavior=BillBehavior.RECURRING,
    )
    make_bill_line_item(bill=bill, amount=Decimal("50.00"), description="Consumo")

    BillService.update_with_lines(
        bill,
        [
            {
                "description": "Parcela 1/12",
                "amount": Decimal("200.00"),
                "installment": installment,
            }
        ],
    )

    assert BillLineItem.objects.filter(bill=bill, installment=installment).count() == 1
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("200.00")
