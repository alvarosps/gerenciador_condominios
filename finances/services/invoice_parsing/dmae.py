"""DMAE (water) invoice parser — total-conserving positional extraction.

Every row of the "DESCRIÇÃO DOS SERVIÇOS E TARIFAS" section becomes a ``ParsedLine`` (nothing is
dropped). Known labels map to a canonical EN category; unknown labels stay generic. The printed
total must equal Σ(non-offset) − Σ(offset); any residual yields a strong PT warning plus an
"Outros/Ajuste" balancing line so the draft still reconciles (design §5.3).
"""

from decimal import Decimal

from finances.models import BillBehavior, BillingAccountType, SupplyStatus
from finances.money import quantize_money
from finances.services.invoice_parsing.base import (
    CATEGORY_AGUA,
    CATEGORY_ATUALIZACAO,
    CATEGORY_DESCONTO,
    CATEGORY_ESGOTO,
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

_ANCHOR_FATURA = "FATURA"
_ANCHOR_VENCIMENTO = "VENCIMENTO"
_ANCHOR_INSCRICAO = "INSCRICAO"
_ANCHOR_DESCRIPTION = "DESCRICAO DOS SERVICOS"
_ANCHOR_TOTAL = "TOTAL A PAGAR"
_ANCHOR_CONSUMO = "CONSUMO M3"
_ANCHOR_LEITURA_ANTERIOR = "LEITURA ANTERIOR"
_ANCHOR_LEITURA_ATUAL = "LEITURA ATUAL"
_ANCHOR_LEITURA_DIAS = "LEITURA DIAS"
_ANCHOR_DATA_LEITURA = "DATA LEITURA"
_ANCHOR_AGUA_STATUS = "SITUACAO AGUA"
_ANCHOR_ESGOTO_STATUS = "SITUACAO ESGOTO"
_STATUS_CUT_MARKER = "CORTAD"

# Label keyword -> canonical EN category (water). Matched as a substring of the printed label.
_LABEL_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("DESCONTO", CATEGORY_DESCONTO),
    ("PARCELAMENTO", CATEGORY_PARCELAMENTO),
    ("AGUA", CATEGORY_AGUA),
    ("ESGOTO", CATEGORY_ESGOTO),
    ("MULTA", CATEGORY_MULTA),
    ("JUROS", CATEGORY_JUROS),
    ("ATUALIZACAO", CATEGORY_ATUALIZACAO),
)

_ADJUSTMENT_DESCRIPTION = "Outros/Ajuste"
_ERR_NO_DESCRIPTION = "Seção de descrição da fatura DMAE não encontrada."
_WARN_RESIDUAL = (
    "A soma das linhas não bate com o total impresso — confira os valores. "
    "Adicionada uma linha 'Outros/Ajuste' para reconciliar."
)
_WARN_READING_DECREASE = "Leitura atual menor que a anterior — confira a leitura."


def _categorize(label: str) -> str:
    upper = label.upper()
    for keyword, category in _LABEL_CATEGORIES:
        if keyword in upper:
            return category
    return CATEGORY_GENERIC


def _supply_status(rows: list[PositionedRow], anchor: str) -> SupplyStatus:
    value = value_after(rows, anchor).upper()
    return SupplyStatus.CUT if _STATUS_CUT_MARKER in value else SupplyStatus.ACTIVE


def _description_entries(
    page: PdfPage, rows: list[PositionedRow], total_row: PositionedRow
) -> list[tuple[PositionedRow, Decimal]]:
    """Recorta a banda vertical entre o cabeçalho da tabela e o total e devolve seus lançamentos.

    Extração posicional: o ``words_in_bbox`` isola a seção de DESCRIÇÃO; só as linhas com um
    valor monetário são lançamentos.
    """
    start = find_row(rows, _ANCHOR_DESCRIPTION)
    if start is None:
        raise ValueError(_ERR_NO_DESCRIPTION)
    band = rows_in_bbox(page, (0.0, start.bottom, float(page.width), total_row.top))
    return line_entries(band, _ANCHOR_TOTAL)


def _line_from_entry(row: PositionedRow, raw_value: Decimal) -> ParsedLine:
    label = row.label_before_value()
    category = _categorize(label)
    is_offset = category == CATEGORY_DESCONTO or raw_value < 0
    installment = parse_installment_marker(label) if category == CATEGORY_PARCELAMENTO else None
    return ParsedLine(
        description=label,
        amount=quantize_money(abs(raw_value)),
        is_offset=is_offset,
        installment_number=installment,
        category=category,
    )


def _balancing_line(printed_total: Decimal, lines: list[ParsedLine]) -> ParsedLine | None:
    """Devolve a linha 'Outros/Ajuste' que reconcilia o resíduo (None se a soma já bate)."""
    settled = sum(
        (line.amount if not line.is_offset else -line.amount for line in lines),
        Decimal(0),
    )
    residual = quantize_money(printed_total - settled)
    if residual == Decimal("0.00"):
        return None
    return ParsedLine(
        description=_ADJUSTMENT_DESCRIPTION,
        amount=abs(residual),
        is_offset=residual < 0,
        category=CATEGORY_GENERIC,
    )


def _reading_warning(leitura_anterior: int | None, leitura_atual: int | None) -> str | None:
    if (
        leitura_anterior is not None
        and leitura_atual is not None
        and leitura_atual < leitura_anterior
    ):
        return _WARN_READING_DECREASE
    return None


class DmaeWaterParser:
    """Parser da fatura de água (DMAE). Extração posicional, total-conservadora."""

    def parse(self, page: PdfPage) -> ParsedInvoice:
        rows = extract_rows(page)

        competence_month = parse_competence(value_after(rows, _ANCHOR_FATURA))
        due_date = parse_date(value_after(rows, _ANCHOR_VENCIMENTO))
        external_identifier = value_after(rows, _ANCHOR_INSCRICAO)

        total_row, printed_total = read_total(rows, _ANCHOR_TOTAL, "DMAE")
        line_items = [
            _line_from_entry(row, value)
            for row, value in _description_entries(page, rows, total_row)
        ]

        warnings: list[str] = []
        adjustment = _balancing_line(printed_total, line_items)
        if adjustment is not None:
            line_items.append(adjustment)
            warnings.append(_WARN_RESIDUAL)

        leitura_anterior = int_after(rows, _ANCHOR_LEITURA_ANTERIOR)
        leitura_atual = int_after(rows, _ANCHOR_LEITURA_ATUAL)
        reading_warning = _reading_warning(leitura_anterior, leitura_atual)
        if reading_warning is not None:
            warnings.append(reading_warning)

        data_leitura_row = find_row(rows, _ANCHOR_DATA_LEITURA)
        statement: dict[str, object] = {
            "consumo_m3": int_after(rows, _ANCHOR_CONSUMO),
            "leitura_anterior": leitura_anterior,
            "leitura_atual": leitura_atual,
            "leitura_dias": int_after(rows, _ANCHOR_LEITURA_DIAS),
            "data_leitura": (
                parse_date(value_after(rows, _ANCHOR_DATA_LEITURA))
                if data_leitura_row is not None
                else None
            ),
            "agua_status": _supply_status(rows, _ANCHOR_AGUA_STATUS),
            "esgoto_status": _supply_status(rows, _ANCHOR_ESGOTO_STATUS),
        }

        return ParsedInvoice(
            competence_month=competence_month,
            due_date=due_date,
            external_identifier=external_identifier,
            behavior=BillBehavior.RECURRING,
            account_type=BillingAccountType.WATER,
            line_items=line_items,
            statement=statement,
            warnings=warnings,
        )
