"""File-streaming service for authenticated downloads.

Keeps filesystem I/O (opening the stored FileField) on the service boundary, while the
ownership/authorization checks stay in the viewsets (HTTP layer).
"""

from pathlib import Path

from django.http import FileResponse

from core.models import PaymentProof


def proof_file_response(proof: PaymentProof) -> FileResponse:
    """Stream a payment proof's stored file as an inline FileResponse.

    The content type is inferred by Django from the file extension; uploads are restricted to
    JPEG/PNG/PDF at the serializer level. Callers must verify ownership before calling this.

    Args:
        proof: The PaymentProof whose ``file`` is to be streamed (must be non-empty).

    Returns:
        An inline FileResponse for the stored file.
    """
    return FileResponse(
        proof.file.open("rb"),
        as_attachment=False,
        filename=Path(proof.file.name).name,
    )
