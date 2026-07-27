"""Integration tests for ``POST /api/finances/bills/{id}/apply_invoice/`` (session 69).

Multipart upload of a sanitized invoice PDF (S59 fixtures, no PII) → in-memory parse → applied
DIRECTLY to the target bill (lines + statement + editable header) via InvoiceApplyService ->
BillService.update_with_lines (S58/S69), in the SAME transaction. Sibling of
test_parse_invoice_api.py, which stays UNTOUCHED (its own 12 tests are the regression: the
VERIFY gate runs that file verbatim and it must stay 100% green with zero edits — that file is
not duplicated here, per the brief's "not a new test, the criterion is the regression run").

Mock policy (tests/CLAUDE.md): the ONLY external boundary here is reading the PDF bytes. The S59
fixtures are sanitized ``.txt`` layouts rendered to a real positional PDF by ``invoice_pdf_bytes``
(reportlab), so ``pdfplumber.open`` runs against a real artifact and is NEVER mocked. ORM,
``detect_and_parse``, the parsers, the services and ``BillSerializer`` are all real.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from finances.models import (
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    InstallmentPlanState,
)
from finances.services.bill_payment_service import BillPaymentService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_installment,
    make_installment_plan,
)
from tests.unit.test_finances.conftest import invoice_pdf_bytes

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

DMAE_UC = "117.111.0049.0508.00"


def _apply_url(bill_id: int) -> str:
    return f"/api/finances/bills/{bill_id}/apply_invoice/"


def _pdf_upload(fixture_name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        f"{fixture_name}.pdf", invoice_pdf_bytes(fixture_name), content_type="application/pdf"
    )


def _water_bill(account, **overrides: object):
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


def test_apply_invoice_requires_authentication(api_client):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC
    )
    bill = _water_bill(account)
    resp = api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_apply_invoice_forbidden_for_non_admin(regular_authenticated_api_client):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC
    )
    bill = _water_bill(account)
    resp = regular_authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_apply_invoice_happy_path_dmae(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = _water_bill(account, user=admin_user)
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["amount_total"] == "3157.05"
    assert resp.data["amount_is_estimated"] is False
    assert resp.data["water_statement"]["consumo_m3"] == 28
    assert len(resp.data["line_items"]) > 1


def test_apply_invoice_account_mismatch_returns_400(authenticated_api_client, admin_user):
    other_account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-OUTRA", user=admin_user
    )
    bill = _water_bill(other_account, user=admin_user)
    lines_before = BillLineItem.objects.filter(bill=bill).count()
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert BillLineItem.objects.filter(bill=bill).count() == lines_before


def test_apply_invoice_competence_mismatch_returns_400(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = _water_bill(
        account, competence_month=date(2026, 6, 1), due_date=date(2026, 6, 10), user=admin_user
    )
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "05/2026" in resp.data["error"]
    assert "06/2026" in resp.data["error"]


def test_apply_invoice_non_pdf_returns_400(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = _water_bill(account, user=admin_user)
    upload = SimpleUploadedFile("nope.pdf", b"isto nao e um pdf", content_type="application/pdf")
    resp = authenticated_api_client.post(_apply_url(bill.id), {"file": upload}, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "PDF" in resp.data["error"]


def test_apply_invoice_unknown_issuer_returns_422(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = _water_bill(account, user=admin_user)
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("desconhecida")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "reconhecido" in resp.data["error"]


def test_apply_invoice_paid_bill_returns_400(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = _water_bill(account, user=admin_user)
    BillPaymentService.pay(bill, date(2026, 5, 5), user=admin_user)
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "pagamento" in resp.data["error"].lower()


def test_apply_invoice_preserves_installment_line_end_to_end(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    plan = make_installment_plan(
        embedded=True,
        billing_account=account,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        user=admin_user,
    )
    installment = make_installment(plan=plan, number=3, amount=Decimal("530.24"), user=admin_user)
    bill = _water_bill(account, user=admin_user)
    installment_line = make_bill_line_item(
        bill=bill, installment=installment, amount=Decimal("530.24"), description="Parcela 3/59"
    )
    resp = authenticated_api_client.post(
        _apply_url(bill.id), {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    parcela_lines = BillLineItem.objects.filter(bill=bill, installment=installment)
    assert parcela_lines.count() == 1
    assert parcela_lines.get().pk == installment_line.pk
