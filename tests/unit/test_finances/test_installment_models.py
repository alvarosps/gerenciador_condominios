"""Session 41 — InstallmentPlan / Installment model tests (constraints, clean, soft-delete)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from finances.models import (
    BillingAccountType,
    Installment,
    InstallmentPlan,
    InstallmentPlanState,
)

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
        "materialized",
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


def test_embedded_plan_requires_billing_account() -> None:
    """clean() rejeita embedded=True sem billing_account (chave 'billing_account', PT)."""
    plan = InstallmentPlan(embedded=True, billing_account=None)
    with pytest.raises(ValidationError) as exc:
        plan.clean()
    assert "billing_account" in exc.value.message_dict


def test_embedded_plan_requires_consumption_account_type() -> None:
    """clean() rejeita embedded=True com billing_account de tipo IPTU/GENERIC."""
    iptu = make_billing_account(account_type=BillingAccountType.IPTU, external_identifier="123")
    generic = make_billing_account(account_type=BillingAccountType.GENERIC)
    for account in (iptu, generic):
        plan = InstallmentPlan(embedded=True, billing_account=account)
        with pytest.raises(ValidationError) as exc:
            plan.clean()
        assert "billing_account" in exc.value.message_dict


def test_embedded_plan_accepts_water_account() -> None:
    """clean() aceita embedded=True com billing_account account_type=WATER."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-1"
    )
    plan = make_installment_plan(
        condominium=account.condominium, embedded=True, billing_account=account
    )
    plan.clean()  # no error


def test_embedded_plan_accepts_electricity_and_internet_accounts() -> None:
    """clean() aceita embedded=True com ELECTRICITY e INTERNET (cobre os 3 tipos de consumo)."""
    for account_type, identifier in (
        (BillingAccountType.ELECTRICITY, "UC-2"),
        (BillingAccountType.INTERNET, ""),
    ):
        account = make_billing_account(account_type=account_type, external_identifier=identifier)
        plan = make_installment_plan(
            condominium=account.condominium, embedded=True, billing_account=account
        )
        plan.clean()  # no error


def test_standalone_plan_allows_iptu_billing_account() -> None:
    """clean() aceita embedded=False COM billing_account de tipo IPTU."""
    account = make_billing_account(account_type=BillingAccountType.IPTU, external_identifier="9988")
    plan = make_installment_plan(
        condominium=account.condominium, embedded=False, billing_account=account
    )
    plan.clean()  # no error: standalone plans may carry an IPTU account


def test_standalone_plan_allows_null_billing_account() -> None:
    """clean() aceita embedded=False com billing_account=None (empréstimo genérico)."""
    plan = make_installment_plan(embedded=False, billing_account=None)
    plan.clean()  # no error


def test_billing_account_field_keeps_protect_and_related_name() -> None:
    """billing_account é FK PROTECT related_name='installment_plans' (atributos preservados)."""
    field = InstallmentPlan._meta.get_field("billing_account")
    assert field.null is True
    assert field.blank is True
    assert field.remote_field.on_delete is models.PROTECT
    assert field.remote_field.related_name == "installment_plans"


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
