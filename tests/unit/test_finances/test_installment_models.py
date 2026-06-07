"""Session 41 — InstallmentPlan / Installment model tests (constraints, clean, soft-delete)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from finances.models import Installment, InstallmentPlan, InstallmentPlanState

from tests.factories import make_billing_account, make_installment, make_installment_plan

pytestmark = pytest.mark.django_db


def test_inherits_audit_and_soft_delete_mixins() -> None:
    plan = make_installment_plan()
    assert plan.created_at is not None
    assert plan.updated_at is not None
    assert plan.is_deleted is False
    inst = make_installment(plan=plan)
    assert inst.is_deleted is False

    plan.delete()  # soft delete
    assert InstallmentPlan.objects.filter(pk=plan.pk).count() == 0
    assert (
        InstallmentPlan.all_objects.filter(pk=plan.pk).count() == 1
    )  # all_objects includes deleted


def test_lifecycle_state_default_and_choices() -> None:
    plan = make_installment_plan()
    assert plan.lifecycle_state == InstallmentPlanState.ACTIVE
    assert {c[0] for c in InstallmentPlanState.choices} == {
        "active",
        "paid",
        "deferred",
        "canceled",
    }


def test_total_amount_negative_rejected() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_installment_plan(total_amount=Decimal("-1.00"))


def test_installment_count_zero_rejected() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        make_installment_plan(installment_count=0)


def test_installment_amount_negative_rejected_zero_allowed() -> None:
    plan = make_installment_plan()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_installment(plan=plan, number=9, amount=Decimal("-1.00"))
    zero = make_installment(plan=plan, number=10, amount=Decimal("0.00"))
    assert zero.amount == Decimal("0.00")


def test_partial_unique_plan_number_soft_delete_frees_slot() -> None:
    plan = make_installment_plan()
    first = make_installment(plan=plan, number=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_installment(plan=plan, number=1)
    first.delete()  # soft delete frees the (plan, number) slot
    second = make_installment(plan=plan, number=1)
    assert second.pk != first.pk


def test_clean_embedded_requires_linked_account() -> None:
    plan = InstallmentPlan(embedded=True, linked_billing_account=None)
    with pytest.raises(ValidationError) as exc:
        plan.clean()
    assert "linked_billing_account" in exc.value.message_dict


def test_clean_standalone_forbids_linked_account() -> None:
    account = make_billing_account()
    plan = InstallmentPlan(embedded=False, linked_billing_account=account)
    with pytest.raises(ValidationError) as exc:
        plan.clean()
    assert "linked_billing_account" in exc.value.message_dict


def test_installment_is_cascade_child_on_hard_delete() -> None:
    plan = make_installment_plan()
    make_installment(plan=plan, number=1)
    make_installment(plan=plan, number=2)
    plan.delete(hard_delete=True)
    assert Installment.all_objects.filter(plan_id=plan.pk).count() == 0


def test_str_is_portuguese() -> None:
    plan = make_installment_plan(description="IPTU 2026", installment_count=10)
    assert "IPTU 2026" in str(plan)
    inst = make_installment(plan=plan, number=3)
    assert "Parcela 3/10" in str(inst)
