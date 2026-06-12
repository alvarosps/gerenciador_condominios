"""Safe query/body param parsing helpers that turn malformed input into DRF 400s.

Without these, ``int()`` / ``date.fromisoformat()`` on raw request params raise
ValueError/TypeError and surface as unhandled 500s; here they become field-scoped
``ValidationError`` (400) responses. An absent or empty value parses to ``None`` so
callers can apply their own default.
"""

from datetime import date

from rest_framework import serializers


def parse_int_param(value: str | None, *, field: str) -> int | None:
    """Parse an optional integer param, raising a 400 on malformed input."""
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            {field: ["Valor inválido; informe um número inteiro."]}
        ) from exc


def parse_date_param(value: str | None, *, field: str) -> date | None:
    """Parse an optional ISO (AAAA-MM-DD) date param, raising a 400 on malformed input."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            {field: ["Data inválida; use o formato AAAA-MM-DD."]}
        ) from exc
