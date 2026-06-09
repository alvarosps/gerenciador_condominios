"""Unit tests for ``InvoiceDraftService.build_draft`` (session 60).

Builds ``ParsedInvoice`` / ``ParsedLine`` (S59 dataclasses) by hand (no PDF) over a real DB and
exercises the enrichment: account matching, embedded-installment reconciliation, idempotency and
the past-immutable invariant (build_draft writes NOTHING). No mocks — pure ORM + dataclasses.
"""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import (
    Bill,
    BillingAccount,
    BillingAccountState,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    Installment,
    InstallmentPlanState,
    Payment,
)
from finances.services.invoice_draft_service import InvoiceDraftService
from finances.services.invoice_parsing.base import ParsedInvoice, ParsedLine

from tests.factories import (
    make_bill,
    make_billing_account,
    make_installment,
    make_installment_plan,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

WATER_UC = "117.111.0049.0508.00"


def _water_invoice(**overrides: object) -> ParsedInvoice:
    """A minimal water ParsedInvoice with a single AGUA line (overridable)."""
    kwargs: dict[str, object] = {
        "competence_month": date(2026, 5, 1),
        "due_date": date(2026, 6, 4),
        "external_identifier": WATER_UC,
        "account_type": BillingAccountType.WATER,
        "line_items": [ParsedLine(description="AGUA", amount=Decimal("100.00"))],
    }
    kwargs.update(overrides)
    return ParsedInvoice(**kwargs)  # type: ignore[arg-type]


def test_build_draft_matches_account_by_type_and_identifier(admin_user):
    building = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier=WATER_UC,
        user=admin_user,
    )
    draft = InvoiceDraftService.build_draft(_water_invoice())
    assert draft["matched_account"]["id"] == building.id
    assert draft["bill"]["building_id"] == building.building_id
    assert draft["bill"]["category_id"] == building.category_id


def test_build_draft_no_match_emits_warning_and_null_account(admin_user):
    count_before = BillingAccount.objects.count()
    draft = InvoiceDraftService.build_draft(_water_invoice())
    assert draft["matched_account"] is None
    assert any(WATER_UC in warning for warning in draft["warnings"])
    assert BillingAccount.objects.count() == count_before


def test_build_draft_reconciles_embedded_installment(admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    installment = make_installment(plan=plan, number=3, user=admin_user)
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3)
        ]
    )
    draft = InvoiceDraftService.build_draft(invoice)
    assert draft["line_items"][0]["installment_id"] == installment.pk


def test_build_draft_installment_without_plan_keeps_generic_line_and_warns(admin_user):
    make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3)
        ]
    )
    draft = InvoiceDraftService.build_draft(invoice)
    line = draft["line_items"][0]
    assert line["installment_id"] is None
    assert line["description"] == "Parcela 3/59"
    assert any("Planos de Parcelamento" in warning for warning in draft["warnings"])
    assert Installment.objects.count() == 0


def test_build_draft_idempotency_flags_replacement_for_existing_bill(admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = make_bill(
        billing_account=account,
        competence_month=date(2026, 5, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
        user=admin_user,
    )
    draft = InvoiceDraftService.build_draft(_water_invoice(competence_month=date(2026, 5, 1)))
    assert draft["existing_bill_id"] == bill.pk
    assert any("substituirá" in warning for warning in draft["warnings"])


def test_build_draft_no_existing_bill_no_replacement_warning(admin_user):
    make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    draft = InvoiceDraftService.build_draft(_water_invoice(competence_month=date(2026, 5, 1)))
    assert draft["existing_bill_id"] is None
    assert not any("substituirá" in warning for warning in draft["warnings"])


def test_build_draft_writes_nothing_to_db(admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    make_installment(plan=plan, number=3, user=admin_user)
    make_bill(
        billing_account=account,
        competence_month=date(2026, 5, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
        user=admin_user,
    )
    invoice = _water_invoice(
        competence_month=date(2026, 5, 1),
        line_items=[
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3)
        ],
    )
    counts_before = (
        Bill.objects.count(),
        BillLineItem.objects.count(),
        Installment.objects.count(),
        Payment.objects.count(),
    )
    InvoiceDraftService.build_draft(invoice)
    counts_after = (
        Bill.objects.count(),
        BillLineItem.objects.count(),
        Installment.objects.count(),
        Payment.objects.count(),
    )
    assert counts_before == counts_after


def test_build_draft_preserves_parser_warnings_and_appends(admin_user):
    parser_warning = "A soma das linhas não bate com o total impresso — confira os valores."
    draft = InvoiceDraftService.build_draft(_water_invoice(warnings=[parser_warning]))
    assert parser_warning in draft["warnings"]
    assert any(WATER_UC in warning for warning in draft["warnings"])


def test_build_draft_serializes_statement_passthrough(admin_user):
    statement = {"consumo_m3": 158, "leitura_dias": 30}
    with_statement = InvoiceDraftService.build_draft(_water_invoice(statement=statement))
    assert with_statement["statement"] == statement
    without_statement = InvoiceDraftService.build_draft(_water_invoice(statement=None))
    assert without_statement["statement"] is None


def test_build_draft_line_amounts_are_string_decimal_and_offset_preserved(admin_user):
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="AGUA", amount=Decimal("530.24"), is_offset=False),
            ParsedLine(description="DESCONTO", amount=Decimal("9.61"), is_offset=True),
        ]
    )
    draft = InvoiceDraftService.build_draft(invoice)
    assert draft["line_items"][0]["amount"] == "530.24"
    assert draft["line_items"][0]["is_offset"] is False
    assert draft["line_items"][1]["amount"] == "9.61"
    assert draft["line_items"][1]["is_offset"] is True


def test_build_draft_description_from_matched_account_name(admin_user):
    make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier=WATER_UC,
        name="Conta de Água - 850",
        user=admin_user,
    )
    draft = InvoiceDraftService.build_draft(_water_invoice())
    assert draft["bill"]["description"] == "Conta de Água - 850"


def test_build_draft_description_fallback_when_no_match(admin_user):
    draft = InvoiceDraftService.build_draft(
        _water_invoice(account_type=BillingAccountType.WATER, competence_month=date(2026, 6, 1))
    )
    assert "06/2026" in draft["bill"]["description"]


def test_build_draft_line_exposes_installment_id_not_installment_number(admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    make_installment(plan=plan, number=3, user=admin_user)
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3)
        ]
    )
    draft = InvoiceDraftService.build_draft(invoice)
    line = draft["line_items"][0]
    assert "installment_id" in line
    assert "installment_number" not in line


def test_build_draft_ignores_non_embedded_plan_for_reconciliation(admin_user):
    """An installment number only matches an EMBEDDED active plan of the matched account."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    standalone = make_installment_plan(
        embedded=False,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    make_installment(plan=standalone, number=3, user=admin_user)
    invoice = _water_invoice(
        line_items=[
            ParsedLine(description="Parcela 3/59", amount=Decimal("530.24"), installment_number=3)
        ]
    )
    draft = InvoiceDraftService.build_draft(invoice)
    assert draft["line_items"][0]["installment_id"] is None


def test_build_draft_bill_dates_iso_and_competence_first_day(admin_user):
    draft = InvoiceDraftService.build_draft(
        _water_invoice(competence_month=date(2026, 5, 1), due_date=date(2026, 6, 4))
    )
    assert draft["bill"]["competence_month"] == "2026-05-01"
    assert draft["bill"]["due_date"] == "2026-06-04"
    assert draft["bill"]["account_type"] == BillingAccountType.WATER
    assert draft["bill"]["external_identifier"] == WATER_UC


def test_build_draft_no_installment_number_line_has_null_installment_id(admin_user):
    make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    draft = InvoiceDraftService.build_draft(_water_invoice())
    assert draft["line_items"][0]["installment_id"] is None
    assert draft["line_items"][0]["category_id"] is None


def test_build_draft_idempotency_ignores_soft_deleted_bill(admin_user):
    """A soft-deleted bill for the same (account, competence) must NOT flag replacement."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=WATER_UC, user=admin_user
    )
    bill = make_bill(
        billing_account=account,
        competence_month=date(2026, 5, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
        user=admin_user,
    )
    bill.delete(deleted_by=admin_user)
    draft = InvoiceDraftService.build_draft(_water_invoice(competence_month=date(2026, 5, 1)))
    assert draft["existing_bill_id"] is None


def test_build_draft_match_requires_active_account_state(admin_user):
    """recurring match is by type+identifier; an ended account still matches (admin decides)."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier=WATER_UC,
        lifecycle_state=BillingAccountState.ACTIVE,
        user=admin_user,
    )
    draft = InvoiceDraftService.build_draft(_water_invoice())
    assert draft["matched_account"]["id"] == account.id
