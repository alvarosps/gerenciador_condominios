"""Unit tests for payment-proof upload content validation.

The validator must rely on real file content (magic bytes via Pillow / the ``%PDF-``
header) plus the extension, NOT the client-supplied ``content_type`` (which is forgeable).

Mock policy: nothing internal is mocked. Pillow runs against real image bytes generated
in memory; PDF/HTML bytes are crafted directly.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import serializers

from core.validators.upload import validate_proof_file


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(120, 60, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(10, 200, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.mark.unit
class TestProofUploadValidation:
    def test_valid_jpeg_passes(self):
        upload = SimpleUploadedFile("comprovante.jpg", _jpeg_bytes(), content_type="image/jpeg")
        assert validate_proof_file(upload) is upload

    def test_valid_png_passes(self):
        upload = SimpleUploadedFile("comprovante.png", _png_bytes(), content_type="image/png")
        assert validate_proof_file(upload) is upload

    def test_valid_pdf_passes(self):
        upload = SimpleUploadedFile("recibo.pdf", _pdf_bytes(), content_type="application/pdf")
        assert validate_proof_file(upload) is upload

    def test_forged_content_type_pdf_with_html_body_rejected(self):
        # Client claims PDF but the body is HTML/text — must be rejected (the old code passed it).
        upload = SimpleUploadedFile(
            "recibo.pdf",
            b"<html><script>alert(1)</script></html>",
            content_type="application/pdf",
        )
        with pytest.raises(serializers.ValidationError):
            validate_proof_file(upload)

    def test_extension_mismatch_png_bytes_jpg_name_rejected(self):
        upload = SimpleUploadedFile("comprovante.jpg", _png_bytes(), content_type="image/jpeg")
        with pytest.raises(serializers.ValidationError):
            validate_proof_file(upload)

    def test_disallowed_extension_exe_rejected(self):
        # Real image bytes but a forbidden extension — extension allowlist must reject it.
        upload = SimpleUploadedFile("malware.exe", _png_bytes(), content_type="image/png")
        with pytest.raises(serializers.ValidationError):
            validate_proof_file(upload)

    def test_oversize_file_rejected(self):
        big = SimpleUploadedFile("recibo.pdf", _pdf_bytes(), content_type="application/pdf")
        big.size = 10 * 1024 * 1024 + 1
        with pytest.raises(serializers.ValidationError):
            validate_proof_file(big)

    def test_file_pointer_reset_after_validation(self):
        data = _png_bytes()
        upload = SimpleUploadedFile("comprovante.png", data, content_type="image/png")
        validate_proof_file(upload)
        assert upload.read() == data
