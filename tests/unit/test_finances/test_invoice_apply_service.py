"""Unit tests for ``InvoiceApplyService.apply`` (session 69).

Builds ``ParsedInvoice`` / ``ParsedLine`` (S59 dataclasses) by hand (no PDF) over a real DB and
exercises the parse-and-apply-to-target-bill orchestration: line/statement/header replace via
``BillService.update_with_lines`` (S58), embedded-installment preservation/dedup (S69), the
``amount_is_estimated`` clear (S65 delegation), and the 400 guards (account/competence/lifecycle
mismatch; paid/closed-month rejected by delegation). No mocks — pure ORM + dataclasses.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time

from finances.models import (
    Bill,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    ElectricityBillStatement,
    InstallmentPlanState,
    WaterBillStatement,
)
from finances.services.bill_payment_service import BillPaymentService
from finances.services.invoice_apply_service import InvoiceApplyService
from finances.services.invoice_parsing.base import ParsedInvoice, ParsedLine
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condo_month_close,
    make_installment,
    make_installment_plan,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

WATER_UC = "117.111.0049.0508.00"
FROZEN = "2026-05-05 12:00:00"


def _water_invoice(**overrides: object) -> ParsedInvoice:
    kwargs: dict[str, object] = {
        "competence_month": date(2026, 5, 1),
        "due_date": date(2026, 6, 4),
        "external_identifier": WATER_UC,
        "account_type": BillingAccountType.WATER,
        "line_items": [ParsedLine(description="AGUA", amount=Decimal("100.00"))],
    }
    kwargs.update(overrides)
    return ParsedInvoice(**kwargs)


def _estimated_bill(account, **overrides: object) -> Bill:
    defaults: dict[str, object] = {
        "billing_account": account,
        "condominium": account.condominium,
        "competence_month": date(2026, 5, 1),
        "due_date": date(2026, 5, 10),
        "description": account.name,
        "behavior": "recurring",
        "lifecycle_state": BillLifecycleState.ACTIVE,
        "amount_is_estimated": True,
    }
    defaults.update(overrides)
    bill = make_bill(**defaults)
    make_bill_line_item(bill=bill, amount=Decimal("90.00"), description="Estimativa")
    return bill


def test_apply_replaces_lines_and_updates_header(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    original_competence = bill.competence_month
    invoice = _water_invoice(
        due_date=date(2026, 6, 10),
        line_items=[ParsedLine(description="AGUA", amount=Decimal("158.30"))],
    )

    InvoiceApplyService.apply(bill, invoice, user=admin_user)

    bill.refresh_from_db()
    assert bill.due_date == date(2026, 6, 10)
    assert bill.external_identifier == WATER_UC
    assert bill.competence_month == original_competence
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("158.30")
    assert BillLineItem.objects.filter(bill=bill).count() == 1
    assert BillLineItem.objects.get(bill=bill).description == "AGUA"


def test_apply_upserts_statement(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    invoice = _water_invoice(statement={"consumo_m3": 158, "leitura_atual": 1158})

    InvoiceApplyService.apply(bill, invoice, user=admin_user)

    statement = WaterBillStatement.objects.get(bill=bill)
    assert statement.consumo_m3 == 158
    assert ElectricityBillStatement.objects.filter(bill=bill).exists() is False


def test_apply_clears_estimated_flag(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    assert bill.amount_is_estimated is True

    InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)

    bill.refresh_from_db()
    assert bill.amount_is_estimated is False


def test_apply_preserves_embedded_installment_line(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    installment = make_installment(plan=plan, number=3, amount=Decimal("530.24"), user=admin_user)
    bill = _estimated_bill(account)
    installment_line = make_bill_line_item(
        bill=bill, installment=installment, amount=Decimal("530.24"), description="Parcela 3/59"
    )
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="AGUA", amount=Decimal("100.00")),
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3),
        ]
    )

    InvoiceApplyService.apply(bill, invoice, user=admin_user)

    parcela_lines = BillLineItem.objects.filter(bill=bill, installment=installment)
    assert parcela_lines.count() == 1
    assert parcela_lines.get().pk == installment_line.pk
    annotated = Bill.objects.with_amounts(date(2026, 7, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("630.24")  # 100 (AGUA) + 530.24 (parcela, once)


def test_apply_account_mismatch_rejected(admin_user) -> None:
    other_account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-OUTRA", user=admin_user
    )
    bill = _estimated_bill(other_account)
    lines_before = BillLineItem.objects.filter(bill=bill).count()

    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)

    assert BillLineItem.objects.filter(bill=bill).count() == lines_before


def test_apply_no_billing_account_rejected(admin_user) -> None:
    bill = make_bill(
        competence_month=date(2026, 5, 1),
        due_date=date(2026, 5, 10),
        behavior="one_time",
        lifecycle_state=BillLifecycleState.ACTIVE,
        user=admin_user,
    )
    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)


def test_apply_competence_mismatch_rejected(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account, competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10))
    invoice = _water_invoice(competence_month=date(2026, 5, 1))

    with pytest.raises(ValidationError) as exc_info:
        InvoiceApplyService.apply(bill, invoice, user=admin_user)
    assert "05/2026" in str(exc_info.value)
    assert "06/2026" in str(exc_info.value)


@pytest.mark.parametrize(
    "state",
    [BillLifecycleState.SUSPENDED, BillLifecycleState.DEFERRED, BillLifecycleState.CANCELED],
)
def test_apply_non_active_bill_rejected(admin_user, state) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account, lifecycle_state=state)
    lines_before = BillLineItem.objects.filter(bill=bill).count()

    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)

    assert BillLineItem.objects.filter(bill=bill).count() == lines_before


@freeze_time(FROZEN)
def test_apply_paid_bill_rejected(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    BillPaymentService.pay(bill, date(2026, 5, 5), user=admin_user)
    line_description_before = BillLineItem.objects.get(bill=bill).description

    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)

    assert BillLineItem.objects.get(bill=bill).description == line_description_before


@freeze_time(FROZEN)
def test_apply_closed_month_rejected(admin_user) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    make_condo_month_close(
        condominium=account.condominium,
        reference_month=date(2026, 5, 1),
        status="closed",
        closed_at=timezone.now(),
    )
    lines_before = BillLineItem.objects.filter(bill=bill).count()

    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, _water_invoice(), user=admin_user)

    assert BillLineItem.objects.filter(bill=bill).count() == lines_before


def test_apply_is_atomic(admin_user) -> None:
    """A failure in the statement upsert (bad field) rolls back lines/header/flag together."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = _estimated_bill(account)
    original_due_date = bill.due_date
    invoice = _water_invoice(
        due_date=date(2026, 6, 1),
        line_items=[ParsedLine(description="AGUA", amount=Decimal("999.00"))],
        statement={"consumo_m3": -1},  # PositiveIntegerField -> full_clean() rejects
    )

    with pytest.raises(ValidationError):
        InvoiceApplyService.apply(bill, invoice, user=admin_user)

    bill.refresh_from_db()
    assert bill.due_date == original_due_date
    assert bill.amount_is_estimated is True
    assert BillLineItem.objects.get(bill=bill).description == "Estimativa"
