"""Unit tests for the CEEE (electricity) invoice parser — net-energy = total − Σ items, 3 layouts."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from finances.models import BillBehavior, BillingAccountType
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


def test_ceee_competence_from_conta_mes_not_due_or_issue(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE: competence_month comes from 'Conta Mês' (not emissão/vencimento), day 1."""
    invoice = _parse(render_invoice_pdf, "ceee_850_solar")
    assert invoice.competence_month == date(2026, 5, 1)
    # emissão (22/05) and vencimento (10/06) must NOT drive competence.
    assert invoice.competence_month != date(2026, 6, 1)


def test_ceee_external_identifier_uc_and_account_type(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE: external_identifier = UC; account_type ELECTRICITY; behavior RECURRING; due_date read."""
    invoice = _parse(render_invoice_pdf, "ceee_850_solar")
    assert invoice.external_identifier == "900126780"
    assert invoice.account_type == BillingAccountType.ELECTRICITY
    assert invoice.behavior == BillBehavior.RECURRING
    assert invoice.due_date == date(2026, 6, 10)
    assert invoice.matched_account is None


def test_ceee_energia_liquida_equals_total_minus_items(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE solar pleno 850: Energia (líquida) == total − Σ(items); Σ all lines == total."""
    invoice = _parse(render_invoice_pdf, "ceee_850_solar")
    energia = _line(invoice, "Energia (líquida)")
    assert energia.category == "ENERGIA"
    assert energia.is_offset is False
    assert energia.amount == quantize_money("317.00")  # 990.80 - (35+5.40+2.10+1.95+629.35)
    total_lines = sum(
        (line.amount if not line.is_offset else -line.amount for line in invoice.line_items),
        Decimal(0),
    )
    assert quantize_money(total_lines) == quantize_money("990.80")


def test_ceee_negative_energia_liquida_becomes_offset_positive_magnitude(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE solar credit: negative net energy -> ParsedLine.is_offset=True, positive magnitude (amount>=0)."""
    invoice = _parse(render_invoice_pdf, "ceee_solar_credito")
    energia = _line(invoice, "Energia (líquida)")
    assert energia.is_offset is True
    assert energia.amount == quantize_money("22.66")  # |12.34 - 35.00|
    assert energia.amount >= Decimal(0)


def test_ceee_solar_statement_fields(render_invoice_pdf: RenderFixture) -> None:
    """CEEE solar pleno: statement with consumo_kwh, energia_injetada_kwh set, readings, classe, bandeira."""
    invoice = _parse(render_invoice_pdf, "ceee_850_solar")
    assert invoice.statement is not None
    assert invoice.statement["consumo_kwh"] == 320
    assert invoice.statement["energia_injetada_kwh"] == 145
    assert invoice.statement["leitura_anterior"] == 9800
    assert invoice.statement["leitura_atual"] == 10120
    assert invoice.statement["leitura_dias"] == 30
    assert invoice.statement["classe"] == "Residencial Pleno"
    assert invoice.statement["bandeira"] == "Verde"


def test_ceee_baixa_renda_statement_no_injection(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE tarifa social 836: energia_injetada_kwh is None; classe='Baixa Renda'; consumo_kwh read."""
    invoice = _parse(render_invoice_pdf, "ceee_836_baixa_renda")
    assert invoice.statement is not None
    assert invoice.statement["energia_injetada_kwh"] is None
    assert invoice.statement["classe"] == "Baixa Renda"
    assert invoice.statement["consumo_kwh"] == 90
    assert invoice.statement["bandeira"] == "Amarela"


def test_ceee_parcela_marker_sets_installment_number(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE 850: 'Parcela 19/24' -> ParsedLine.installment_number == 19, category='PARCELAMENTO'."""
    invoice = _parse(render_invoice_pdf, "ceee_850_solar")
    parcela = _line(invoice, "PARCELA")
    assert parcela.installment_number == 19
    assert parcela.category == "PARCELAMENTO"
    assert parcela.amount == quantize_money("629.35")


def test_ceee_unknown_item_label_kept_as_generic(
    render_invoice_pdf: RenderFixture,
) -> None:
    """CEEE: an unrecognized item label ('CONTRIB ILUMINACAO EXTRA') -> ParsedLine with category=''."""
    invoice = _parse(render_invoice_pdf, "ceee_836_baixa_renda")
    extra = _line(invoice, "CONTRIB ILUMINACAO EXTRA")
    assert extra.category == ""
    assert extra.amount == quantize_money("3.00")
    # Net energy still reconciles the printed total (100,62 - 8,20 - 3,00 = 89,42).
    energia = _line(invoice, "Energia (líquida)")
    assert energia.amount == quantize_money("89.42")


def test_ceee_arrecadada_marker_emits_warning(render_invoice_pdf: RenderFixture) -> None:
    """CEEE with 'FATURA ARRECADADA / NÃO RECEBER' -> PT warning (2nd via already paid); parsing proceeds."""
    invoice = _parse(render_invoice_pdf, "ceee_solar_credito")
    assert any("arrecadada" in warning.lower() for warning in invoice.warnings)
    # Parsing still produced a complete draft.
    assert invoice.account_type == BillingAccountType.ELECTRICITY
    assert invoice.external_identifier == "900127980"
