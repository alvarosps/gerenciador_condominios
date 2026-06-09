"""CEEE (electricity) invoice parser — net energy = printed total − Σ(line items).

The energy charge is never printed as a single positive figure; it is derived so that the sum of
all lines equals the printed total. A negative net energy (high solar-credit month) is emitted as
an offset line with positive magnitude (respeita ``CheckConstraint amount>=0``). Competence comes
from the "Conta Mês" label (not emissão/vencimento). A "FATURA ARRECADADA" marker only warns —
the admin decides whether to register the bill as already paid (design §5.4).
"""

from decimal import Decimal

from finances.models import BillBehavior, BillingAccountType
from finances.money import quantize_money
from finances.services.invoice_parsing.base import (
    CATEGORY_ATUALIZACAO,
    CATEGORY_CIP,
    CATEGORY_ENERGIA,
    CATEGORY_GENERIC,
    CATEGORY_JUROS,
    CATEGORY_MULTA,
    CATEGORY_PARCELAMENTO,
    ParsedInvoice,
    ParsedLine,
    PdfPage,
    PositionedRow,
    extract_rows,
    find_row,
    int_after,
    line_entries,
    parse_competence,
    parse_date,
    parse_installment_marker,
    read_total,
    rows_in_bbox,
    value_after,
)

_ANCHOR_CONTA_MES = "CONTA MES"
_ANCHOR_VENCIMENTO = "VENCIMENTO"
_ANCHOR_UC = "UC "
_ANCHOR_CLASSE = "CLASSE"
_ANCHOR_BANDEIRA = "BANDEIRA"
_ANCHOR_CONSUMO = "CONSUMO KWH"
_ANCHOR_INJETADA = "ENERGIA INJETADA"
_ANCHOR_LEITURA_ANTERIOR = "LEITURA ANTERIOR"
_ANCHOR_LEITURA_ATUAL = "LEITURA ATUAL"
_ANCHOR_LEITURA_DIAS = "LEITURA DIAS"
_ANCHOR_DESCRIPTION = "DESCRICAO DOS VALORES"
_ANCHOR_TOTAL = "TOTAL A PAGAR"
_MARKER_ARRECADADA = "ARRECADADA"

_ENERGIA_DESCRIPTION = "Energia (líquida)"
_ERR_NO_ITEMS = "Seção de itens da fatura CEEE não encontrada."
_WARN_ARRECADADA = "Fatura já arrecadada (2ª via) — o admin decide registrá-la como paga."

# Label keyword -> canonical EN category (electricity). Matched as a substring of the printed label.
_LABEL_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("PARCELA", CATEGORY_PARCELAMENTO),
    ("CIP", CATEGORY_CIP),
    ("MULTA", CATEGORY_MULTA),
    ("CORRECAO", CATEGORY_ATUALIZACAO),
    ("JUROS", CATEGORY_JUROS),
)


def _categorize(label: str) -> str:
    upper = label.upper()
    for keyword, category in _LABEL_CATEGORIES:
        if keyword in upper:
            return category
    return CATEGORY_GENERIC


def _item_entries(
    page: PdfPage, rows: list[PositionedRow], total_row: PositionedRow
) -> list[tuple[PositionedRow, Decimal]]:
    """Lançamentos faturados entre o cabeçalho da seção e o total (extração posicional)."""
    start = find_row(rows, _ANCHOR_DESCRIPTION)
    if start is None:
        raise ValueError(_ERR_NO_ITEMS)
    band = rows_in_bbox(page, (0.0, start.bottom, float(page.width), total_row.top))
    return line_entries(band, _ANCHOR_TOTAL)


def _item_line(row: PositionedRow, raw_value: Decimal) -> ParsedLine:
    label = row.label_before_value()
    category = _categorize(label)
    installment = parse_installment_marker(label) if category == CATEGORY_PARCELAMENTO else None
    return ParsedLine(
        description=label,
        amount=quantize_money(abs(raw_value)),
        is_offset=raw_value < 0,
        installment_number=installment,
        category=category,
    )


def _energy_line(printed_total: Decimal, items: list[ParsedLine]) -> ParsedLine:
    """Energia (líquida) = total − Σ(itens). Negativa → offset com magnitude positiva."""
    items_sum = sum(
        (item.amount if not item.is_offset else -item.amount for item in items),
        Decimal(0),
    )
    net = quantize_money(printed_total - items_sum)
    return ParsedLine(
        description=_ENERGIA_DESCRIPTION,
        amount=abs(net),
        is_offset=net < 0,
        category=CATEGORY_ENERGIA,
    )


class CeeeElectricityParser:
    """Parser da fatura de luz (CEEE). Energia líquida derivada; 3 layouts (solar/social/crédito)."""

    def parse(self, page: PdfPage) -> ParsedInvoice:
        rows = extract_rows(page)

        competence_month = parse_competence(value_after(rows, _ANCHOR_CONTA_MES))
        due_date = parse_date(value_after(rows, _ANCHOR_VENCIMENTO))
        external_identifier = value_after(rows, _ANCHOR_UC)

        total_row, printed_total = read_total(rows, _ANCHOR_TOTAL, "CEEE")

        line_items = [_item_line(row, value) for row, value in _item_entries(page, rows, total_row)]
        line_items.insert(0, _energy_line(printed_total, line_items))

        warnings: list[str] = []
        if find_row(rows, _MARKER_ARRECADADA) is not None:
            warnings.append(_WARN_ARRECADADA)

        statement: dict[str, object] = {
            "consumo_kwh": int_after(rows, _ANCHOR_CONSUMO),
            "energia_injetada_kwh": int_after(rows, _ANCHOR_INJETADA),
            "leitura_anterior": int_after(rows, _ANCHOR_LEITURA_ANTERIOR),
            "leitura_atual": int_after(rows, _ANCHOR_LEITURA_ATUAL),
            "leitura_dias": int_after(rows, _ANCHOR_LEITURA_DIAS),
            "classe": value_after(rows, _ANCHOR_CLASSE),
            "bandeira": value_after(rows, _ANCHOR_BANDEIRA),
        }

        return ParsedInvoice(
            competence_month=competence_month,
            due_date=due_date,
            external_identifier=external_identifier,
            behavior=BillBehavior.RECURRING,
            account_type=BillingAccountType.ELECTRICITY,
            line_items=line_items,
            statement=statement,
            warnings=warnings,
        )
