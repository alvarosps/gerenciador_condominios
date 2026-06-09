"""Unit tests for the DMAE (water) invoice parser — positional extraction, total-conserving.

Pure parsing (no DB, no ORM): each test renders a sanitized fixture into a positional PDF
(reportlab) and feeds the bytes through ``detect_and_parse`` (the real ``pdfplumber`` path).
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from finances.models import BillBehavior, BillingAccountType, SupplyStatus
from finances.money import quantize_money
from finances.services.invoice_parsing.base import ParsedInvoice, ParsedLine
from finances.services.invoice_parsing.registry import detect_and_parse

RenderFixture = Callable[[str], bytes]


def _parse(render_invoice_pdf: RenderFixture, fixture_name: str) -> ParsedInvoice:
    return detect_and_parse(render_invoice_pdf(fixture_name))


def _line(invoice: ParsedInvoice, description_contains: str) -> ParsedLine:
    matches = [line for line in invoice.line_items if description_contains in line.description]
    assert len(matches) == 1, (
        f"expected exactly one line containing {description_contains!r}, "
        f"got {[line.description for line in invoice.line_items]}"
    )
    return matches[0]


def test_dmae_parses_competence_first_day_from_fatura_label(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: competence_month = date(AAAA, MM, 1) extracted from 'FATURA MM/AAAA'."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    assert invoice.competence_month == date(2026, 5, 1)
    assert invoice.due_date == date(2026, 6, 4)


def test_dmae_external_identifier_and_account_type(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: external_identifier = inscrição read; account_type WATER; behavior RECURRING."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    assert invoice.external_identifier == "117.111.0049.0508.00"
    assert invoice.account_type == BillingAccountType.WATER
    assert invoice.behavior == BillBehavior.RECURRING
    assert invoice.matched_account is None


def test_dmae_every_description_row_becomes_a_line_total_conserving(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE 850/Maio: every DESCRIÇÃO row becomes a ParsedLine; known labels get a category."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    categories = {line.description: line.category for line in invoice.line_items}
    assert _line(invoice, "AGUA").category == "AGUA"
    assert _line(invoice, "ESGOTO").category == "ESGOTO"
    assert _line(invoice, "PARCELAMENTO").category == "PARCELAMENTO"
    assert _line(invoice, "MULTA").category == "MULTA"
    assert _line(invoice, "JUROS").category == "JUROS"
    # 6 positives + 2 offsets = 8 description rows, none dropped.
    assert len(invoice.line_items) == 8
    assert all(category != "PROVISIONAL" for category in categories.values())


def test_dmae_unknown_label_taxa_cobranca_kept_as_generic(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: 'TAXA COBRANCA' (unknown label) -> ParsedLine with category='' (never dropped)."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    taxa = _line(invoice, "TAXA COBRANCA")
    assert taxa.category == ""
    assert taxa.amount == quantize_money("7.52")
    assert taxa.is_offset is False


def test_dmae_desconto_line_is_offset(render_invoice_pdf: RenderFixture) -> None:
    """DMAE: 'DESCONTO …' -> ParsedLine.is_offset=True with a positive (magnitude) amount."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    desconto = _line(invoice, "DESCONTO PONTUALIDADE")
    assert desconto.is_offset is True
    assert desconto.amount == quantize_money("9.61")
    assert desconto.category == "DESCONTO"


def test_dmae_sum_minus_offsets_equals_printed_total(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE 850/Maio: Σ(non-offset) − Σ(offset) == 3157.05 (incl. TAXA COBRANCA); no residual warning."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    positives = sum(
        (line.amount for line in invoice.line_items if not line.is_offset),
        Decimal(0),
    )
    offsets = sum(
        (line.amount for line in invoice.line_items if line.is_offset),
        Decimal(0),
    )
    assert quantize_money(positives - offsets) == quantize_money("3157.05")
    assert not any("ajuste" in warning.lower() for warning in invoice.warnings)
    assert not any("conferir" in warning.lower() for warning in invoice.warnings)


def test_dmae_residual_emits_strong_warning_and_balancing_line(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE whose total does not match the lines -> strong PT warning + 'Outros/Ajuste' line."""
    invoice = _parse(render_invoice_pdf, "dmae_residual")
    adjustment = _line(invoice, "Outros/Ajuste")
    assert adjustment.amount == quantize_money("10.00")
    assert adjustment.is_offset is False
    assert adjustment.category == ""
    assert any("ajuste" in warning.lower() for warning in invoice.warnings)
    # After the balancing line the invariant holds again.
    positives = sum(
        (line.amount for line in invoice.line_items if not line.is_offset),
        Decimal(0),
    )
    offsets = sum(
        (line.amount for line in invoice.line_items if line.is_offset),
        Decimal(0),
    )
    assert quantize_money(positives - offsets) == quantize_money("160.00")


def test_dmae_parcelamento_marker_sets_installment_number(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: 'PARCELAMENTO … PARCELA 3/59' -> installment_number == 3, category='PARCELAMENTO'."""
    invoice = _parse(render_invoice_pdf, "dmae_850_maio")
    parcela = _line(invoice, "PARCELAMENTO")
    assert parcela.installment_number == 3
    assert parcela.category == "PARCELAMENTO"
    assert parcela.amount == quantize_money("530.24")


def test_dmae_statement_readings_and_supply_status(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: statement carries consumo_m3, readings, data_leitura, agua/esgoto status (CORTADO→CUT)."""
    active = _parse(render_invoice_pdf, "dmae_850_maio")
    assert active.statement is not None
    assert active.statement["consumo_m3"] == 28
    assert active.statement["leitura_anterior"] == 1240
    assert active.statement["leitura_atual"] == 1268
    assert active.statement["leitura_dias"] == 30
    assert active.statement["data_leitura"] == date(2026, 5, 20)
    assert active.statement["agua_status"] == SupplyStatus.ACTIVE
    assert active.statement["esgoto_status"] == SupplyStatus.ACTIVE

    cut = _parse(render_invoice_pdf, "dmae_836_cortada")
    assert cut.statement is not None
    assert cut.statement["agua_status"] == SupplyStatus.CUT
    assert cut.statement["esgoto_status"] == SupplyStatus.ACTIVE


def test_dmae_reading_decrease_emits_plausibility_warning(
    render_invoice_pdf: RenderFixture,
) -> None:
    """DMAE: leitura_atual < leitura_anterior (no rollover) -> PT plausibility warning (not an exception)."""
    invoice = _parse(render_invoice_pdf, "dmae_836_cortada")
    assert any("leitura" in warning.lower() for warning in invoice.warnings)
