"""
Caching utilities for Condomínios Manager.

Phase 4 Infrastructure: Redis caching layer with invalidation strategies.

Provides:
- cache_result: Decorator for caching function results
- invalidate_cache: Invalidate cache keys
- get_model_cache_key: Generate consistent cache keys for models
- CacheManager: Centralized cache management

Usage:
    from core.cache import cache_result, CacheManager

    @cache_result(timeout=300)
    def get_active_leases():
        return Lease.objects.filter(contract_generated=True)

    # Invalidate cache
    CacheManager.invalidate_pattern('lease_list*')
"""

import fnmatch
import hashlib
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Model
from django_redis import get_redis_connection


def _is_redis_backend() -> bool:
    """Check if the default cache backend is Redis (not LocMemCache or other)."""
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    return "redis" in backend.lower()


logger = logging.getLogger(__name__)

T = TypeVar("T")

_SENTINEL = object()

_CACHE_KEY_MAX_LENGTH = 200

# Registry of bare (pre-versioning) cache keys created by @cache_result — the ONLY place this
# module ever writes application cache entries. On the in-process LocMemCache backend (no
# key-scan API), this registry lets CacheManager.invalidate_pattern() delete exactly the keys it
# created, without touching unrelated keys such as DRF throttle counters (which are written
# directly by rest_framework.throttling, never through cache_result, and therefore never appear
# here). Real Redis deployments use SCAN instead — see CacheManager._invalidate_pattern_now.
_TRACKED_CACHE_KEYS: set[str] = set()


def get_cache_key(*args: Any, prefix: str = "", **kwargs: Any) -> str:
    """
    Generate a consistent cache key from arguments.

    Args:
        *args: Positional arguments to include in key
        prefix: Prefix for the cache key
        **kwargs: Keyword arguments to include in key

    Returns:
        Cache key string

    Examples:
        >>> get_cache_key("lease", 1, prefix="detail")
        'detail:lease:1'
        >>> get_cache_key(building_id=5, apartment=10, prefix="apt")
        'apt:building_id=5:apartment=10'
    """
    # Convert args and kwargs to a stable string representation
    key_parts = [prefix] if prefix else []

    # Add positional arguments
    for arg in args:
        if isinstance(arg, Model):
            # For model instances, use model name and pk
            key_parts.append(f"{arg.__class__.__name__}:{arg.pk}")
        else:
            key_parts.append(str(arg))

    # Add keyword arguments (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, Model):
            key_parts.append(f"{k}={v.__class__.__name__}:{v.pk}")
        else:
            key_parts.append(f"{k}={v}")

    # Join parts with ':'
    cache_key = ":".join(key_parts)

    # If key is too long, hash it
    if len(cache_key) > _CACHE_KEY_MAX_LENGTH:
        cache_key = f"{prefix}:hash:{hashlib.sha256(cache_key.encode()).hexdigest()}"

    return cache_key


def get_model_cache_key(model_name: str, pk: int | None = None, action: str = "") -> str:
    """
    Generate cache key for model instances or lists.

    Args:
        model_name: Name of the model (e.g., 'Lease', 'Apartment')
        pk: Primary key of the instance (None for lists)
        action: Optional action suffix (e.g., 'list', 'detail', 'count')

    Returns:
        Cache key string

    Examples:
        >>> get_model_cache_key("Lease", pk=1, action="detail")
        'model:Lease:1:detail'
        >>> get_model_cache_key("Apartment", action="list")
        'model:Apartment:list'
    """
    parts = ["model", model_name]

    if pk is not None:
        parts.append(str(pk))

    if action:
        parts.append(action)

    return ":".join(parts)


def cache_result(timeout: int = 300, key_prefix: str = "") -> Callable:
    """
    Decorator to cache function results in Redis.

    Args:
        timeout: Cache timeout in seconds (default: 300 = 5 minutes)
        key_prefix: Prefix for cache key

    Returns:
        Decorated function

    Examples:
        @cache_result(timeout=600, key_prefix='lease_list')
        def get_active_leases(building_id: int):
            return Lease.objects.filter(
                apartment__building_id=building_id,
                contract_generated=True
            )
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            cache_key = get_cache_key(*args, prefix=key_prefix or func.__name__, **kwargs)

            # Try to get from cache
            cached_value = cache.get(cache_key, _SENTINEL)
            if cached_value is not _SENTINEL:
                logger.debug(f"Cache HIT: {cache_key}")
                return cast(T, cached_value)

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, timeout)
            _TRACKED_CACHE_KEYS.add(cache_key)
            logger.debug(f"Cache SET: {cache_key} (timeout={timeout}s)")

            return result

        return wrapper

    return decorator


class CacheManager:
    """
    Centralized cache management with pattern-based invalidation.

    Provides methods for invalidating caches by real key prefix, or entirely.

    Examples:
        # Invalidate by prefix (keys are hyphenated; use "<prefix>*")
        CacheManager.invalidate_pattern('dashboard-lease-metrics*')

        # Clear all caches
        CacheManager.clear_all()
    """

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern, deferred to transaction commit.

        Runs the actual deletion in ``transaction.on_commit`` so a concurrent read cannot
        re-populate the cache with pre-commit data (the invalidation would otherwise race
        the write inside the same transaction). Outside an atomic block, ``on_commit``
        fires immediately, so behaviour is unchanged there.

        Args:
            pattern: Pattern to match (supports wildcards)

        Returns:
            Number of keys invalidated synchronously (0 when deferred to on_commit, since
            the count is not yet known at call time)

        Examples:
            >>> CacheManager.invalidate_pattern("lease:*")
            10
            >>> CacheManager.invalidate_pattern("*building*")
            5
        """
        transaction.on_commit(lambda: CacheManager._invalidate_pattern_now(pattern))
        return 0

    @staticmethod
    def _invalidate_pattern_now(pattern: str) -> int:
        """Perform the actual pattern invalidation (called via on_commit)."""
        if not _is_redis_backend():
            return CacheManager._invalidate_pattern_locmem(pattern)
        try:
            redis_client = get_redis_connection("default")
            # Derive the real on-wire key (KEY_PREFIX + VERSION) via Django's own key
            # construction rather than hardcoding ":1:" — matches whatever KEY_FUNCTION /
            # VERSION the cache backend is actually configured with.
            full_pattern = cache.make_key(pattern)
            count = 0
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    count += len(keys)
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            logger.exception(f"Error invalidating cache pattern {pattern}")
            return 0
        else:
            if count > 0:
                logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
            return count

    @staticmethod
    def _invalidate_pattern_locmem(pattern: str) -> int:
        """Selective invalidation for in-process backends (LocMemCache, used in tests/dev).

        LocMemCache (and other in-process backends) expose no key-scan API, and their
        internal key store is a private implementation detail (not part of the public
        ``BaseCache``/django-stubs surface). Instead, this deletes only the bare cache keys
        that ``@cache_result`` itself registered in ``_TRACKED_CACHE_KEYS`` — the only place
        this module ever writes application cache entries — and that match ``pattern``. DRF
        throttle counters (and any other key not created via ``cache_result``) are never
        registered, so they can never be touched here. This must NOT fall back to
        ``cache.clear()``: that would wipe every key regardless of origin.
        """
        matching_keys = [key for key in _TRACKED_CACHE_KEYS if fnmatch.fnmatchcase(key, pattern)]
        for key in matching_keys:
            cache.delete(key)
            _TRACKED_CACHE_KEYS.discard(key)
        if matching_keys:
            logger.info(f"Invalidated {len(matching_keys)} cache keys matching pattern: {pattern}")
        return len(matching_keys)

    @staticmethod
    def clear_all() -> bool:
        """
        Clear all caches (use with caution!).

        Returns:
            True if successful, False otherwise

        Examples:
            >>> CacheManager.clear_all()
            True
        """
        try:
            cache.clear()
            logger.warning("Cleared ALL cache keys")
        except Exception:
            logger.exception("Error clearing all caches")
            return False
        else:
            return True

    @staticmethod
    def get_cache_stats() -> dict:
        """
        Get cache statistics (if available).

        Returns:
            Dictionary with cache stats

        Examples:
            >>> stats = CacheManager.get_cache_stats()
            >>> print(f"Cache keys: {stats['keys']}")
        """
        try:
            if not _is_redis_backend():
                return {
                    "total_keys": 0,
                    "keyspace_hits": 0,
                    "keyspace_misses": 0,
                    "hit_rate": 0.0,
                }

            redis_client = get_redis_connection("default")

            info = redis_client.info("stats")
            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "condominios")

            # Count keys with our prefix via non-blocking scan (KEYS is O(N) and blocks prod).
            pattern = f"{key_prefix}:1:*"
            keys_count = sum(1 for _ in redis_client.scan_iter(match=pattern, count=100))

            return {
                "total_keys": keys_count,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                    * 100
                ),
            }
        except Exception:
            logger.exception("Error getting cache stats")
            return {
                "total_keys": 0,
                "keyspace_hits": 0,
                "keyspace_misses": 0,
                "hit_rate": 0.0,
            }


# Canonical condominium-finance (`finances` app) cache prefixes, defined ONCE core-side. core must
# NOT import finances (that would invert the finances -> core dependency), so these literals are
# duplicated from finances.cache.FINANCE_CACHE_PREFIXES; the match is locked by
# tests/unit/test_finances/test_finance_cache_signals.py. core.signals reuses this same tuple, and
# _LEGACY_FINANCIAL_CACHE_PREFIXES derives from it (no third hardcoded copy).
FINANCE_MODULE_CACHE_PREFIXES = ("finance-dashboard", "finance-projection")

# Legacy personal-finance prefixes (cash-flow / financial-dashboard) plus the condominium-finance
# prefixes that legacy money changes also affect. Keys are hyphenated -> glob "<prefix>*".
_LEGACY_FINANCIAL_CACHE_PREFIXES = (
    "cash-flow",
    "financial-dashboard",
    *FINANCE_MODULE_CACHE_PREFIXES,
)


def invalidate_legacy_financial_caches() -> None:
    """Invalidate the legacy financial + condominium-finance dashboard caches.

    Lives here (not in signals) so services can call it after a bulk ``.update()`` that
    bypasses ``post_save`` — keeping the Service -> Signals dependency from existing.
    """
    for prefix in _LEGACY_FINANCIAL_CACHE_PREFIXES:
        CacheManager.invalidate_pattern(f"{prefix}*")
