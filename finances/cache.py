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
FINANCE_PROJECTION_PREFIX = "finance-projection"

# Only prefixes a @cache_result actually keys on (dashboard/by_owner + the cash-flow projection,
# which caches under FINANCE_PROJECTION_PREFIX-cashflow). The cash-flow viewset has no cache of its
# own, so there is no finance-cash-flow* key to invalidate.
FINANCE_CACHE_PREFIXES = (
    FINANCE_DASHBOARD_PREFIX,
    FINANCE_PROJECTION_PREFIX,
)


def invalidate_finance_caches() -> None:
    """Invalidate every finance-* dashboard / cash-flow / projection cache."""
    for prefix in FINANCE_CACHE_PREFIXES:
        CacheManager.invalidate_pattern(f"{prefix}*")
