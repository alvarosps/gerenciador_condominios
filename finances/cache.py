"""Single source of the finance-* cache prefixes (design §11).

Prefixes are hyphen-prefixed (not ":"), like the rest of the project
(core/signals.py:295-296). invalidate_pattern builds f"{key_prefix}:1:{prefix}*",
so a one-character difference silently fails to invalidate — these constants are the
one place the prefixes are defined for the finances app. core/signals.py keeps a
matching literal copy (it must NOT import finances — that would invert the
finances -> core dependency); the match is locked by
tests/unit/test_finances/test_finance_cache_signals.py.
"""

from core.cache import CacheManager

FINANCE_DASHBOARD_PREFIX = "finance-dashboard"
FINANCE_CASH_FLOW_PREFIX = "finance-cash-flow"
FINANCE_PROJECTION_PREFIX = "finance-projection"

FINANCE_CACHE_PREFIXES = (
    FINANCE_DASHBOARD_PREFIX,
    FINANCE_CASH_FLOW_PREFIX,
    FINANCE_PROJECTION_PREFIX,
)


def invalidate_finance_caches() -> None:
    """Invalidate every finance-* dashboard / cash-flow / projection cache."""
    for prefix in FINANCE_CACHE_PREFIXES:
        CacheManager.invalidate_pattern(f"{prefix}*")
