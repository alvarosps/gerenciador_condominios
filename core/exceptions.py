"""Global DRF exception handling.

Converts django.core.exceptions.ValidationError (raised e.g. by full_clean()
inside serializer.update()/model.save()) into a DRF 400 instead of a 500.
Rows holding legacy-invalid data would otherwise turn any partial update into
an unhandled 500 (HF-1). Seed for P4.1 (error-shape unification).
"""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DjangoValidationError):
        detail: Any = (
            exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
        )
        exc = ValidationError(detail)
    return exception_handler(exc, context)
