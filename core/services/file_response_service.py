"""File-streaming service for authenticated downloads.

Keeps filesystem I/O (opening the stored FileField) on the service boundary, while the
ownership/authorization checks stay in the viewsets (HTTP layer).
"""

from pathlib import Path

from django.http import FileResponse

from core.models import PaymentProof


def proof_file_response(proof: PaymentProof) -> FileResponse:
    """Stream a payment proof's stored file as a download (defense in depth).

    The content type is inferred by Django from the file extension; uploads are restricted to
    JPEG/PNG/PDF at the serializer level. Callers must verify ownership before calling this.

    The response is served ``as_attachment`` with ``X-Content-Type-Options: nosniff`` so a
    browser never renders an uploaded proof inline nor MIME-sniffs it into an active type.

    Args:
        proof: The PaymentProof whose ``file`` is to be streamed (must be non-empty).

    Returns:
        A download FileResponse for the stored file with ``nosniff``.
    """
    response = FileResponse(
        proof.file.open("rb"),
        as_attachment=True,
        filename=Path(proof.file.name).name,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response
