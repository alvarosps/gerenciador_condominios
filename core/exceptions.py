"""Global DRF exception handling.

Maps framework-agnostic exceptions that would otherwise surface as unhandled 500s onto
the correct DRF status:
- ``django.core.exceptions.ValidationError`` (e.g. from ``full_clean()`` inside
  ``serializer.update()`` / ``model.save()`` over legacy-invalid rows) -> 400 (HF-1).
- ``ObjectDoesNotExist`` (a raw ``Model.objects.get(pk=...)`` miss, e.g. the locked
  ``select_for_update().get()`` in the financial mark-paid actions) -> 404 (P4.1).

``KeyError`` is intentionally NOT mapped here: a missing key is a programming error that
should stay a 500. Endpoints that read request keys directly validate them up front
instead (e.g. ``TransferLeaseSerializer``).
"""

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class Conflict(APIException):
    """409 — the request conflicts with the resource's current state."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflito com o estado atual do recurso."
    default_code = "conflict"


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DjangoValidationError):
        detail: Any = (
            exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        )
        exc = ValidationError(detail)
    elif isinstance(exc, ObjectDoesNotExist):
        exc = NotFound()
    return exception_handler(exc, context)
