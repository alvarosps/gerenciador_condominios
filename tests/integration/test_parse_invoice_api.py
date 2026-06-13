"""Integration tests for ``POST /api/finances/bills/parse_invoice/`` (session 60).

Multipart upload of a sanitized invoice PDF (S59 fixtures, no PII) → in-memory parse → enriched
JSON draft (account match + installment reconciliation + idempotency) that writes NOTHING.

Mock policy (tests/CLAUDE.md): the ONLY external boundary here is reading the PDF bytes. The S59
fixtures are sanitized ``.txt`` layouts rendered to a real positional PDF by ``invoice_pdf_bytes``
(reportlab), so ``pdfplumber.open`` runs against a real artifact and is NEVER mocked. The
non-PDF → 400 path posts genuinely invalid bytes (also no mock). ORM, ``detect_and_parse``, the
parsers, ``InvoiceDraftService`` and ``BillSerializer`` are all real.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

from finances.models import (
    Bill,
    BillingAccountType,
    BillLifecycleState,
    BillLineItem,
    InstallmentPlanState,
)
from tests.factories import make_bill, make_billing_account, make_installment, make_installment_plan
from tests.unit.test_finances.conftest import invoice_pdf_bytes

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PARSE_URL = "/api/finances/bills/parse_invoice/"

DMAE_UC = "117.111.0049.0508.00"
# The authoritative CEEE consumer-unit id is the dotted "Número da UC"; ceee_850_solar's UC matches
# the seeded electricity account 850 (scripts/data/condo_utilities_seed.json).
CEEE_UC = "1.273.678.010-60"


def _pdf_upload(fixture_name: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        f"{fixture_name}.pdf", invoice_pdf_bytes(fixture_name), content_type="application/pdf"
    )


def test_parse_invoice_requires_authentication(api_client):
    resp = api_client.post(PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_parse_invoice_forbidden_for_non_admin(regular_authenticated_api_client):
    resp = regular_authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_parse_invoice_missing_file_returns_400(authenticated_api_client):
    resp = authenticated_api_client.post(PARSE_URL, {}, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "file" in resp.data["error"]


def test_parse_invoice_non_pdf_returns_400(authenticated_api_client):
    upload = SimpleUploadedFile("nope.pdf", b"isto nao e um pdf", content_type="application/pdf")
    resp = authenticated_api_client.post(PARSE_URL, {"file": upload}, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "PDF" in resp.data["error"]


def test_parse_invoice_empty_pdf_returns_400(authenticated_api_client):
    """A structurally valid PDF with zero pages is treated as 'not a valid PDF' (400 PT)."""
    empty_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"
    )
    upload = SimpleUploadedFile("empty.pdf", empty_pdf, content_type="application/pdf")
    resp = authenticated_api_client.post(PARSE_URL, {"file": upload}, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "PDF" in resp.data["error"]


def test_parse_invoice_unknown_issuer_returns_4xx(authenticated_api_client):
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("desconhecida")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "reconhecido" in resp.data["error"]


def test_parse_invoice_dmae_water_returns_draft(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["matched_account"]["id"] == account.id
    assert resp.data["bill"]["account_type"] == BillingAccountType.WATER
    assert resp.data["bill"]["competence_month"] == "2026-05-01"
    assert resp.data["statement"]["consumo_m3"] == 28
    assert len(resp.data["line_items"]) > 0


def test_parse_invoice_ceee_electricity_returns_draft(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.ELECTRICITY, external_identifier=CEEE_UC, user=admin_user
    )
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("ceee_850_solar")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["bill"]["account_type"] == BillingAccountType.ELECTRICITY
    # The parsed Número da UC aligns with the seeded electricity account → build_draft matches it.
    assert resp.data["bill"]["external_identifier"] == CEEE_UC
    assert resp.data["matched_account"]["id"] == account.id
    assert resp.data["statement"]["consumo_kwh"] == 320
    assert resp.data["statement"]["energia_injetada_kwh"] == 145


def test_parse_invoice_no_matching_account_returns_draft_with_warning(authenticated_api_client):
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["matched_account"] is None
    assert any(DMAE_UC in warning for warning in resp.data["warnings"])
    assert Bill.objects.count() == 0


def test_parse_invoice_existing_bill_flags_replacement(authenticated_api_client, admin_user):
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bill = make_bill(
        billing_account=account,
        competence_month=date(2026, 5, 1),
        lifecycle_state=BillLifecycleState.ACTIVE,
        user=admin_user,
    )
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["existing_bill_id"] == bill.pk
    assert any("substituirá" in warning for warning in resp.data["warnings"])


def test_parse_invoice_writes_nothing(authenticated_api_client, admin_user):
    make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier=DMAE_UC, user=admin_user
    )
    bills_before = Bill.objects.count()
    lines_before = BillLineItem.objects.count()
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert Bill.objects.count() == bills_before
    assert BillLineItem.objects.count() == lines_before


def test_parse_invoice_embedded_installment_reconciled_via_api(
    authenticated_api_client, admin_user
):
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
    resp = authenticated_api_client.post(
        PARSE_URL, {"file": _pdf_upload("dmae_850_maio")}, format="multipart"
    )
    assert resp.status_code == status.HTTP_200_OK
    parcela_lines = [line for line in resp.data["line_items"] if line["installment_id"] is not None]
    assert len(parcela_lines) == 1
    assert parcela_lines[0]["installment_id"] == installment.pk
