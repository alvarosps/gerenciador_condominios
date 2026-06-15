"""Content-based validation for uploaded files (payment proofs).

Validates the *real* content of an upload (magic bytes via Pillow for images, the
``%PDF-`` header for PDFs) plus the file extension and size — never the client-supplied
``content_type``, which is forgeable in a multipart request.
"""

from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

_MAX_PROOF_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
_PDF_HEADER = b"%PDF-"

# Allowed extension -> the image format Pillow must report (None means the PDF header path).
_EXTENSION_TO_FORMAT: dict[str, str | None] = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".pdf": None,
}

_INVALID_TYPE_MSG = "Tipo de arquivo não permitido. Use JPEG, PNG ou PDF."
_MISMATCH_MSG = "Conteúdo do arquivo não corresponde à extensão."
_OVERSIZE_MSG = "Arquivo excede o tamanho máximo de 10MB."


def _detect_image_format(uploaded_file: Any) -> str | None:
    """Return Pillow's format for the upload, or None if it is not a readable image."""
    try:
        with Image.open(uploaded_file) as img:
            return img.format
    except UnidentifiedImageError, OSError:
        return None
    finally:
        uploaded_file.seek(0)


def validate_proof_file(uploaded_file: Any) -> Any:
    """Validate a payment-proof upload by size, extension and real content.

    Args:
        uploaded_file: A Django ``UploadedFile`` (has ``name``, ``size``, ``read``, ``seek``).

    Returns:
        The same ``uploaded_file`` with its read pointer reset to the start.

    Raises:
        serializers.ValidationError: If the file is too large, has a disallowed extension,
            or its content does not match the declared extension.
    """
    if uploaded_file.size > _MAX_PROOF_SIZE_BYTES:
        raise serializers.ValidationError(_OVERSIZE_MSG)

    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in _EXTENSION_TO_FORMAT:
        raise serializers.ValidationError(_INVALID_TYPE_MSG)

    expected_format = _EXTENSION_TO_FORMAT[extension]

    if expected_format is None:
        header = uploaded_file.read(len(_PDF_HEADER))
        uploaded_file.seek(0)
        if not header.startswith(_PDF_HEADER):
            raise serializers.ValidationError(_MISMATCH_MSG)
        return uploaded_file

    if _detect_image_format(uploaded_file) != expected_format:
        raise serializers.ValidationError(_MISMATCH_MSG)

    return uploaded_file
