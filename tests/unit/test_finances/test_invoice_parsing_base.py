"""Unit tests for the shared parsing helpers in ``invoice_parsing.base`` (pure, no PDF)."""

from datetime import date
from decimal import Decimal

import pytest

from finances.services.invoice_parsing.base import (
    PositionedRow,
    Word,
    digits_only,
    find_row,
    int_after,
    parse_brl,
    parse_competence,
    parse_date,
    parse_installment_marker,
    value_after,
)


def _word(text: str, x0: float) -> Word:
    return {"text": text, "x0": x0, "top": 0.0, "bottom": 10.0}


def _row(*tokens: tuple[str, float]) -> PositionedRow:
    return PositionedRow(top=0.0, bottom=10.0, words=[_word(t, x) for t, x in tokens])


def test_parse_brl_handles_currency_symbol_thousands_and_sign() -> None:
    assert parse_brl("1.800,07") == Decimal("1800.07")
    assert parse_brl("R$ 9,61") == Decimal("9.61")
    assert parse_brl("-0,42") == Decimal("-0.42")


def test_parse_brl_rejects_installment_marker_and_competence() -> None:
    """'3/59' and '05/2026' are NOT money — they must raise (so they stay as label text)."""
    with pytest.raises(ValueError, match="inválido"):
        parse_brl("3/59")
    with pytest.raises(ValueError, match="inválido"):
        parse_brl("05/2026")
    with pytest.raises(ValueError, match="inválido"):
        parse_brl("LIGADA")


def test_parse_competence_raises_when_missing() -> None:
    assert parse_competence("FATURA 05/2026") == date(2026, 5, 1)
    with pytest.raises(ValueError, match="Competência"):
        parse_competence("FATURA SEM MES")


def test_parse_date_raises_when_missing() -> None:
    assert parse_date("VENCIMENTO 04/06/2026") == date(2026, 6, 4)
    with pytest.raises(ValueError, match="Data"):
        parse_date("VENCIMENTO INDISPONIVEL")


def test_parse_installment_marker_returns_none_without_marker() -> None:
    assert parse_installment_marker("PARCELAMENTO PARCELA 24/46") == 24
    assert parse_installment_marker("AGUA") is None


def test_digits_only_strips_non_digits() -> None:
    assert digits_only("92.924.901 / 0001-98") == "92924901000198"


def test_positioned_row_value_and_label_split() -> None:
    row = _row(("PARCELAMENTO", 50.0), ("PARCELA", 120.0), ("3/59", 180.0), ("530,24", 360.0))
    assert row.value == Decimal("530.24")  # raw (un-quantized) Decimal
    assert row.label_before_value() == "PARCELAMENTO PARCELA 3/59"


def test_positioned_row_without_value_returns_none_and_full_label() -> None:
    """A row with no monetary token: value is None and the whole row is the label."""
    row = _row(("SITUACAO", 50.0), ("AGUA", 120.0), ("LIGADA", 180.0))
    assert row.value is None
    assert row.label_before_value() == "SITUACAO AGUA LIGADA"


def test_value_after_raises_when_anchor_absent() -> None:
    rows = [_row(("INSCRICAO", 50.0), ("117.111", 200.0))]
    assert value_after(rows, "INSCRICAO") == "117.111"
    with pytest.raises(ValueError, match="não encontrado"):
        value_after(rows, "VENCIMENTO")


def test_int_after_returns_none_when_anchor_absent() -> None:
    rows = [_row(("CONSUMO", 50.0), ("M3", 120.0), ("28", 200.0))]
    assert int_after(rows, "CONSUMO M3") == 28
    assert int_after(rows, "LEITURA DIAS") is None


def test_find_row_returns_none_when_absent() -> None:
    rows = [_row(("AGUA", 50.0))]
    assert find_row(rows, "AGUA") is rows[0]
    assert find_row(rows, "ESGOTO") is None
