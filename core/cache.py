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
    CacheManager.invalidate_model('Lease', lease_id)
"""
from __future__ import annotations

import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from django.core.cache import cache
from django.db.models import Model

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
        >>> get_cache_key('lease', 1, prefix='detail')
        'detail:lease:1'
        >>> get_cache_key(building_id=5, apartment=10, prefix='apt')
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
    if len(cache_key) > 200:
        cache_key = f"{prefix}:hash:{hashlib.md5(cache_key.encode()).hexdigest()}"

    return cache_key


def get_model_cache_key(model_name: str, pk: Optional[int] = None, action: str = "") -> str:
    """
    Generate cache key for model instances or lists.

    Args:
        model_name: Name of the model (e.g., 'Lease', 'Apartment')
        pk: Primary key of the instance (None for lists)
        action: Optional action suffix (e.g., 'list', 'detail', 'count')

    Returns:
        Cache key string

    Examples:
        >>> get_model_cache_key('Lease', pk=1, action='detail')
        'model:Lease:1:detail'
        >>> get_model_cache_key('Apartment', action='list')
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
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_value

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cache SET: {cache_key} (timeout={timeout}s)")

            return result

        # Attach cache key generator to function for manual invalidation
        wrapper.get_cache_key = lambda *args, **kwargs: get_cache_key(
            *args, prefix=key_prefix or func.__name__, **kwargs
        )

        return wrapper

    return decorator


class CacheManager:
    """
    Centralized cache management with pattern-based invalidation.

    Provides methods for invalidating caches by model, by pattern, or entirely.

    Examples:
        # Invalidate all caches for a specific Lease
        CacheManager.invalidate_model('Lease', pk=1)

        # Invalidate all Lease caches
        CacheManager.invalidate_model('Lease')

        # Invalidate by pattern
        CacheManager.invalidate_pattern('lease_list:*')

        # Clear all caches
        CacheManager.clear_all()
    """

    @staticmethod
    def invalidate_model(model_name: str, pk: Optional[int] = None) -> int:
        """
        Invalidate all cache keys for a model or specific instance.

        Args:
            model_name: Name of the model
            pk: Primary key of specific instance (None to invalidate all)

        Returns:
            Number of keys invalidated

        Examples:
            >>> CacheManager.invalidate_model('Lease', pk=1)
            3
            >>> CacheManager.invalidate_model('Apartment')
            15
        """
        if pk is not None:
            # Invalidate specific instance caches
            pattern = f"*{model_name}:{pk}*"
        else:
            # Invalidate all model caches
            pattern = f"*{model_name}*"

        return CacheManager.invalidate_pattern(pattern)

    @staticmethod
    def invalidate_pattern(pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.

        Args:
            pattern: Pattern to match (supports wildcards)

        Returns:
            Number of keys invalidated

        Examples:
            >>> CacheManager.invalidate_pattern('lease:*')
            10
            >>> CacheManager.invalidate_pattern('*building*')
            5
        """
        try:
            # Get Redis client from django-redis
            from django_redis import get_redis_connection

            redis_client = get_redis_connection("default")

            # Find all keys matching pattern
            # Add key prefix from settings
            from django.conf import settings

            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "condominios")
            full_pattern = f"{key_prefix}:1:{pattern}"

            keys = redis_client.keys(full_pattern)

            if keys:
                # Delete all matching keys
                count = redis_client.delete(*keys)
                logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
                return count
            else:
                logger.debug(f"No cache keys found matching pattern: {pattern}")
                return 0

        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

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
            return True
        except Exception as e:
            logger.error(f"Error clearing all caches: {e}")
            return False

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
            from django_redis import get_redis_connection

            redis_client = get_redis_connection("default")

            info = redis_client.info("stats")
            from django.conf import settings

            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "condominios")

            # Count keys with our prefix
            pattern = f"{key_prefix}:1:*"
            keys_count = len(redis_client.keys(pattern))

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
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "total_keys": 0,
                "keyspace_hits": 0,
                "keyspace_misses": 0,
                "hit_rate": 0.0,
            }


def invalidate_related_caches(model_instance: Model, related_models: list[str]) -> None:
    """
    Invalidate caches for a model instance and its related models.

    Args:
        model_instance: Model instance that was modified
        related_models: List of related model names to invalidate

    Examples:
        # When a Lease is updated, invalidate Apartment and Tenant caches too
        invalidate_related_caches(lease, ['Apartment', 'Tenant'])
    """
    model_name = model_instance.__class__.__name__
    pk = model_instance.pk

    # Invalidate the instance itself
    CacheManager.invalidate_model(model_name, pk)

    # Invalidate related models
    for related_model in related_models:
        CacheManager.invalidate_model(related_model)

    logger.info(f"Invalidated caches for {model_name}:{pk} and related models: {related_models}")
