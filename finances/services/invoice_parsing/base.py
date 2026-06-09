"""Typed draft dataclasses, the parser protocol, and shared positional-extraction helpers.

Pure parsing (zero ORM): the package imports only the ``finances`` enums (to type the draft)
and ``quantize_money`` (the single money boundary). Money is read as raw ``Decimal`` here and
quantized once when a ``ParsedLine.amount`` / total is assembled. Every parser ancora rótulos
estáveis e recorta a região do valor (``extract_words`` / ``crop``) — nunca regex sobre o
``extract_text()`` plano (o texto reflui em layout multi-coluna → bind errado, design §5.1).
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

import pdfplumber.page

from finances.models import BillBehavior, BillingAccountType

# A word as returned by pdfplumber ``extract_words`` — the untyped boundary stays contained
# in the few helpers below; the rest of the package is fully annotated.
type Word = dict[str, object]
type BBox = tuple[float, float, float, float]
type PdfPage = pdfplumber.page.Page


@dataclass
class ParsedLine:
    """Uma linha de DESCRIÇÃO da fatura → futura BillLineItem.

    ``amount`` é sempre POSITIVO (stored-positive); ``is_offset=True`` para descontos/créditos
    (subtraídos do total). ``installment_number`` = X de 'PARCELA X/N' (None quando a linha não é
    parcela). ``category`` = rótulo canônico EN (AGUA/ESGOTO/PARCELAMENTO/...) ou '' (genérica).
    """

    description: str
    amount: Decimal
    is_offset: bool = False
    installment_number: int | None = None
    category: str = ""


@dataclass
class ParsedInvoice:
    """Rascunho tipado de uma fatura parseada (parsing PURO — sem ORM).

    O caller (S60) serializa isto e abre o modal pré-preenchido. ``matched_account`` é SEMPRE
    ``None`` aqui — a busca da ``BillingAccount`` ativa por ``account_type`` + ``external_identifier``
    no banco é da S60 (precisa de ORM); o parser só expõe o identificador lido em
    ``external_identifier``. As chaves de ``statement`` espelham os campos de
    ``WaterBillStatement`` / ``ElectricityBillStatement`` (S58) — sem renomear.
    """

    competence_month: date
    due_date: date
    external_identifier: str
    behavior: str = BillBehavior.RECURRING
    account_type: str = BillingAccountType.GENERIC
    line_items: list[ParsedLine] = field(default_factory=list)
    statement: dict[str, object] | None = None
    matched_account: None = None
    warnings: list[str] = field(default_factory=list)


class InvoiceParser(Protocol):
    """Contrato de um parser por concessionária: recebe a 1ª página do PDF e devolve o rascunho."""

    def parse(self, page: PdfPage) -> ParsedInvoice: ...


# --- Canonical line categories (EN) -------------------------------------------------------------

CATEGORY_AGUA = "AGUA"
CATEGORY_ESGOTO = "ESGOTO"
CATEGORY_PARCELAMENTO = "PARCELAMENTO"
CATEGORY_MULTA = "MULTA"
CATEGORY_JUROS = "JUROS"
CATEGORY_ATUALIZACAO = "ATUALIZACAO"
CATEGORY_CIP = "CIP"
CATEGORY_ENERGIA = "ENERGIA"
CATEGORY_DESCONTO = "DESCONTO"
CATEGORY_GENERIC = ""


# --- Error messages (named constants — PT, EM/TRY003 friendly) ----------------------------------

_ERR_INVALID_BRL = "Valor monetário inválido na fatura."
_ERR_COMPETENCE_MISSING = "Competência (MM/AAAA) não encontrada na fatura."
_ERR_DATE_MISSING = "Data (DD/MM/AAAA) não encontrada na fatura."
_ERR_ANCHOR_MISSING = "Rótulo esperado não encontrado na fatura."
_ERR_TOTAL_MISSING = "Total da fatura {issuer} não encontrado."


# --- Shared parse helpers (DRY — used by both parsers) ------------------------------------------

# A BRL money token is digits with an optional thousands '.' and a decimal ','. It NEVER contains
# '/' (that is an installment marker like '3/59' or a date) — so reject any token carrying one.
_BRL_TOKEN = re.compile(r"^-?\d{1,3}(\.\d{3})*,\d{2}$")
_BRL_CLEANUP = re.compile(r"[^\d,\-]")
_COMPETENCE = re.compile(r"(\d{2})/(\d{4})")
_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_INSTALLMENT = re.compile(r"\b(\d{1,3})/(\d{1,3})\b")
_DIGITS = re.compile(r"\d")


def parse_brl(text: str) -> Decimal:
    """Converte '1.800,07' / 'R$ 9,61' / '-0,42' em ``Decimal`` (não quantizado).

    Remove R$/espaços, exige o formato monetário BR (``-?#.###,##``) — assim '3/59' (marcador de
    parcela) e '05/2026' (competência) NÃO são confundidos com valores. Preserva o sinal (o caller
    decide ``is_offset`` a partir do sinal) e quantiza depois via ``quantize_money``.
    """
    token = text.replace("R$", "").replace(" ", "").strip()
    if not _BRL_TOKEN.match(token):
        raise ValueError(_ERR_INVALID_BRL)
    normalized = _BRL_CLEANUP.sub("", token).replace(".", "").replace(",", ".")
    return Decimal(normalized)


def parse_competence(label: str) -> date:
    """Extrai MM/AAAA de um rótulo e devolve ``date(AAAA, MM, 1)`` (1º dia do mês)."""
    match = _COMPETENCE.search(label)
    if match is None:
        raise ValueError(_ERR_COMPETENCE_MISSING)
    return date(int(match.group(2)), int(match.group(1)), 1)


def parse_date(text: str) -> date:
    """Extrai DD/MM/AAAA de um texto e devolve a ``date`` correspondente."""
    match = _DATE.search(text)
    if match is None:
        raise ValueError(_ERR_DATE_MISSING)
    return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))


def parse_installment_marker(text: str) -> int | None:
    """De '… PARCELA 24/46' / 'Parcela 19/24' devolve 24/19; sem marcador → None."""
    match = _INSTALLMENT.search(text)
    if match is None:
        return None
    return int(match.group(1))


def digits_only(text: str) -> str:
    """Mantém apenas os dígitos (tolera espaços/quebras inseridos pelo ``extract_text``)."""
    return "".join(_DIGITS.findall(text))


# --- Positional extraction (the contained pdfplumber boundary) ----------------------------------


@dataclass
class PositionedRow:
    """Uma linha visual da página: as palavras (ordenadas por x) com suas coordenadas verticais."""

    top: float
    bottom: float
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(str(word["text"]) for word in self.words)

    @property
    def value(self) -> Decimal | None:
        """O último token numérico da linha como ``Decimal`` cru (None se a linha não tem valor)."""
        for word in reversed(self.words):
            try:
                return parse_brl(str(word["text"]))
            except ValueError:
                continue
        return None

    def label_before_value(self) -> str:
        """O texto à esquerda do valor (a descrição impressa da linha)."""
        labels: list[str] = []
        for word in self.words:
            try:
                parse_brl(str(word["text"]))
            except ValueError:
                labels.append(str(word["text"]))
            else:
                break
        return " ".join(labels)


def _coord(value: object) -> float:
    """Converte uma coordenada do dict (untyped) do pdfplumber em ``float`` com segurança."""
    return float(str(value))


def _group_into_rows(words: list[Word]) -> list[PositionedRow]:
    """Agrupa palavras por coordenada ``top`` em linhas visuais (DRY — único agrupador)."""
    by_top: dict[int, list[Word]] = {}
    for word in words:
        by_top.setdefault(round(_coord(word["top"])), []).append(word)
    rows: list[PositionedRow] = []
    for top in sorted(by_top):
        ordered = sorted(by_top[top], key=lambda item: _coord(item["x0"]))
        bottom = max(_coord(item["bottom"]) for item in ordered)
        rows.append(PositionedRow(top=float(top), bottom=bottom, words=ordered))
    return rows


def words_in_bbox(page: PdfPage, bbox: BBox) -> list[Word]:
    """Wrapper fino sobre ``page.crop(bbox).extract_words()`` — fronteira untyped contida e anotada."""
    words: list[Word] = page.crop(bbox).extract_words()
    return words


def rows_in_bbox(page: PdfPage, bbox: BBox) -> list[PositionedRow]:
    """Linhas visuais dentro de uma região recortada (banda da tabela de descrição)."""
    return _group_into_rows(words_in_bbox(page, bbox))


def extract_rows(page: PdfPage) -> list[PositionedRow]:
    """Agrupa TODAS as palavras da página em linhas visuais, de cima para baixo.

    Extração POSICIONAL: cada linha mantém as palavras ordenadas por x, permitindo ancorar
    rótulos e ler o valor à direita sem regex sobre o ``extract_text()`` plano.
    """
    words: list[Word] = page.extract_words()
    return _group_into_rows(words)


def page_text(page: PdfPage) -> str:
    """Texto plano da página — usado APENAS para detecção de emissor por CNPJ (não para dados)."""
    text: str = page.extract_text() or ""
    return text


def find_row(rows: list[PositionedRow], anchor: str) -> PositionedRow | None:
    """A primeira linha cujo texto contém ``anchor`` (rótulo estável), ou None."""
    for row in rows:
        if anchor in row.text:
            return row
    return None


def value_after(rows: list[PositionedRow], anchor: str) -> str:
    """O texto à direita do ``anchor`` na linha que o contém (o valor impresso do campo)."""
    row = find_row(rows, anchor)
    if row is None:
        raise ValueError(_ERR_ANCHOR_MISSING)
    full = row.text
    return full.split(anchor, 1)[1].strip()


def int_after(rows: list[PositionedRow], anchor: str) -> int | None:
    """O 1º inteiro à direita do ``anchor`` (None se o rótulo existe mas sem número)."""
    row = find_row(rows, anchor)
    if row is None:
        return None
    match = re.search(r"-?\d+", row.text.split(anchor, 1)[1])
    return int(match.group()) if match else None


def read_total(
    rows: list[PositionedRow], anchor: str, issuer: str
) -> tuple[PositionedRow, Decimal]:
    """A linha do total + seu valor; rótulo/valor ausente → ``ValueError`` PT (fatura malformada)."""
    row = find_row(rows, anchor)
    if row is None or row.value is None:
        message = _ERR_TOTAL_MISSING.format(issuer=issuer)
        raise ValueError(message)
    return row, row.value


def line_entries(
    band: list[PositionedRow], total_anchor: str
) -> list[tuple[PositionedRow, Decimal]]:
    """As linhas de lançamento de uma banda: (row, valor cru). Exclui linhas sem valor e o total.

    Devolve o valor já narrowed (não-None) para os builders de ``ParsedLine`` — evita re-checar
    ``row.value`` (mantém o narrowing tipado sem ``assert``).
    """
    entries: list[tuple[PositionedRow, Decimal]] = []
    for row in band:
        value = row.value
        if value is not None and total_anchor not in row.text:
            entries.append((row, value))
    return entries
