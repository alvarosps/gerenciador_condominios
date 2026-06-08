"""Shared query-param coercion for finances viewsets.

A malformed filter value (``?building_id=abc``, ``?due_date_from=notadate``) must fail closed with
a 400 (PT) instead of an unguarded ValueError escaping get_queryset as a 500. These helpers are the
single source of that coercion, used by every CRUD viewset.
"""

from datetime import date

from django.http import QueryDict
from rest_framework.exceptions import ValidationError


def int_param(params: QueryDict, name: str) -> int | None:
    """A query param coerced to int, or None when absent; 400 (PT) on a non-numeric value."""
    raw = params.get(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: "Deve ser um número inteiro."}) from exc


def date_param(params: QueryDict, name: str) -> date | None:
    """A query param coerced to a date, or None when absent; 400 (PT) on a malformed value."""
    raw = params.get(name)
    if raw is None:
        return None
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: "Data inválida (use AAAA-MM-DD)."}) from exc
