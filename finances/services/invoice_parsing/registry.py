"""Issuer detection by CNPJ + delegation to the right parser.

Parse runs entirely in memory (``BytesIO``); the uploaded file is never written to disk
(design §2 decisão #4). Non-PDF bytes and unrecognized issuers raise a PT ``ValueError`` that the
S60 endpoint maps to 400 / 422 respectively.
"""

import io

import pdfplumber
import pdfplumber.pdf
from pdfplumber.utils.exceptions import PdfminerException

from finances.services.invoice_parsing.base import (
    ParsedInvoice,
    PdfPage,
    digits_only,
    page_text,
)
from finances.services.invoice_parsing.ceee import CeeeElectricityParser
from finances.services.invoice_parsing.dmae import DmaeWaterParser

DMAE_CNPJ = "92.924.901/0001-98"
CEEE_CNPJ = "08.467.115/0001-00"

_ERR_NOT_A_PDF = "Arquivo não é um PDF válido."
_ERR_UNKNOWN_ISSUER = "Emissor da fatura não reconhecido (apenas DMAE e CEEE são suportados)."


def _open_first_page(pdf_bytes: bytes) -> tuple[pdfplumber.pdf.PDF, PdfPage]:
    """Abre o PDF em memória e devolve (handle, 1ª página). Bytes inválidos → ValueError PT."""
    try:
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except (PdfminerException, ValueError, OSError) as exc:
        raise ValueError(_ERR_NOT_A_PDF) from exc
    if not pdf.pages:
        pdf.close()
        raise ValueError(_ERR_NOT_A_PDF)
    return pdf, pdf.pages[0]


def detect_and_parse(pdf_bytes: bytes) -> ParsedInvoice:
    """Detecta o emissor por CNPJ e delega ao parser. Parse em MEMÓRIA; arquivo nunca gravado.

    Bytes não-PDF → ``ValueError`` PT (caller S60 → 400); emissor desconhecido → ``ValueError``
    PT (caller S60 → 422). A comparação do CNPJ é por dígitos (tolera espaços/quebras que o
    ``extract_text`` insere); a extração de dados é posicional dentro de cada parser.
    """
    pdf, page = _open_first_page(pdf_bytes)
    try:
        digits = digits_only(page_text(page))
        if digits_only(DMAE_CNPJ) in digits:
            return DmaeWaterParser().parse(page)
        if digits_only(CEEE_CNPJ) in digits:
            return CeeeElectricityParser().parse(page)
        raise ValueError(_ERR_UNKNOWN_ISSUER)
    finally:
        pdf.close()
