"""Single source of truth for "today / current month" in São Paulo local time.

Django's ``settings.TIME_ZONE`` is ``"UTC"``, so ``timezone.now().date()`` yields
the UTC date and is wrong around the month boundary in São Paulo (UTC-3). Every
finances service routes "today / current month" through these helpers (DRY) so the
month boundary is computed once, consistently.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def now_sp() -> datetime:
    """Current instant in São Paulo time (converts the UTC-aware ``now()``)."""
    return timezone.now().astimezone(SAO_PAULO_TZ)


def today_sp() -> date:
    """Today's date in São Paulo time (NOT ``timezone.now().date()``, which is UTC)."""
    return now_sp().date()


def current_month_sp() -> date:
    """First day of the current month in São Paulo time (day=1)."""
    return today_sp().replace(day=1)
