"""Unit tests for ``detect_and_parse`` — issuer detection by CNPJ + error mapping."""

from collections.abc import Callable

import pytest
from finances.models import BillingAccountType
from finances.services.invoice_parsing.registry import (
    CEEE_CNPJ,
    DMAE_CNPJ,
    detect_and_parse,
)

RenderFixture = Callable[[str], bytes]


def test_detect_dmae_by_cnpj_delegates_to_water_parser(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: PDF with CNPJ 92.924.901/0001-98 -> ParsedInvoice account_type == WATER."""
    invoice = detect_and_parse(render_invoice_pdf("dmae_850_maio"))
    assert invoice.account_type == BillingAccountType.WATER


def test_detect_ceee_by_cnpj_delegates_to_electricity_parser(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: PDF with CNPJ 08.467.115/0001-00 -> ParsedInvoice account_type == ELECTRICITY."""
    invoice = detect_and_parse(render_invoice_pdf("ceee_850_solar"))
    assert invoice.account_type == BillingAccountType.ELECTRICITY


def test_unknown_issuer_raises_value_error_pt(render_invoice_pdf: RenderFixture) -> None:
    """registry: unrecognized CNPJ -> ValueError with PT message (caller S60 maps to 422)."""
    with pytest.raises(ValueError, match="não reconhecido"):
        detect_and_parse(render_invoice_pdf("desconhecida"))


def test_non_pdf_bytes_raises_value_error_pt() -> None:
    """registry: bytes that are not a PDF -> PT ValueError 'Arquivo não é um PDF válido.'."""
    with pytest.raises(ValueError, match="não é um PDF válido"):
        detect_and_parse(b"this is plainly not a pdf file")


def test_pdf_without_pages_raises_value_error_pt() -> None:
    """registry: a structurally valid PDF with zero pages -> PT 'Arquivo não é um PDF válido.'."""
    empty_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"
    )
    with pytest.raises(ValueError, match="não é um PDF válido"):
        detect_and_parse(empty_pdf)


def test_malformed_dmae_without_description_raises_pt(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: DMAE issuer but missing the description section -> PT ValueError."""
    with pytest.raises(ValueError, match="Seção de descrição"):
        detect_and_parse(render_invoice_pdf("dmae_no_description"))


def test_malformed_dmae_without_total_raises_pt(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: DMAE issuer but missing the printed total -> PT ValueError."""
    with pytest.raises(ValueError, match="Total da fatura DMAE"):
        detect_and_parse(render_invoice_pdf("dmae_no_total"))


def test_malformed_ceee_without_items_raises_pt(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: CEEE issuer but missing the billed-items section -> PT ValueError."""
    with pytest.raises(ValueError, match="Seção de itens"):
        detect_and_parse(render_invoice_pdf("ceee_no_items"))


def test_cnpj_detection_tolerates_whitespace_from_extract_text(
    render_invoice_pdf: RenderFixture,
) -> None:
    """registry: CNPJ split across whitespace/words by extract_text still matches (digit comparison)."""
    assert DMAE_CNPJ == "92.924.901/0001-98"
    assert CEEE_CNPJ == "08.467.115/0001-00"
    # The fixture renders '92.924.901' and '/ 0001-98' as separate words; the only way to
    # match is to compare digit-strings after stripping the reflowed whitespace.
    invoice = detect_and_parse(render_invoice_pdf("dmae_cnpj_spaced"))
    assert invoice.account_type == BillingAccountType.WATER
