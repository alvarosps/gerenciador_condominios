"""Fixture helpers for the invoice-parser tests (session 59).

The real DMAE/CEEE PDFs carry CPF / barcode / personal data and must NEVER be
versioned (design 5.5). Instead, each fixture is a SANITIZED ``.txt`` layout
(``<x> <y> <text>`` per line) with synthetic values and the public issuer CNPJ.
This helper renders that layout into a small positional PDF with reportlab, so the
parser can exercise its real ``pdfplumber`` ``extract_words`` / ``crop`` path
end-to-end against a deterministic artifact.
"""

import io
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "invoices"


def _render_layout_pdf(layout_text: str) -> bytes:
    """Render a ``<x> <y> <text>`` layout into a positional single-page PDF (A4)."""
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    pdf_canvas.setFont("Helvetica", 9)
    for raw_line in layout_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        x_text, y_text, text = line.split(maxsplit=2)
        pdf_canvas.drawString(float(x_text), float(y_text), text)
    pdf_canvas.save()
    return buffer.getvalue()


def invoice_pdf_bytes(fixture_name: str) -> bytes:
    """Return the rendered PDF bytes for a sanitized ``.txt`` invoice fixture.

    Also writes the ``.pdf`` artifact next to the ``.txt`` so the rendered fixture
    is versioned alongside its sanitized source.
    """
    txt_path = FIXTURES_DIR / f"{fixture_name}.txt"
    pdf_bytes = _render_layout_pdf(txt_path.read_text(encoding="utf-8"))
    (FIXTURES_DIR / f"{fixture_name}.pdf").write_bytes(pdf_bytes)
    return pdf_bytes


@pytest.fixture
def render_invoice_pdf() -> object:
    """Expose ``invoice_pdf_bytes`` as a fixture callable to the parser tests."""
    return invoice_pdf_bytes
