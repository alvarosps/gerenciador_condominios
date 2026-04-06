"""Unit tests for core/cache.py — CacheManager, cache_result decorator, and key helpers."""

import pytest
from django.test import override_settings

from core.cache import (
    CacheManager,
    cache_result,
    get_cache_key,
    get_model_cache_key,
    invalidate_related_caches,
)

LOCMEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "cache-unit-tests",
    }
}


@pytest.mark.unit
class TestGetCacheKey:
    def test_positional_args(self):
        key = get_cache_key("lease", 1, prefix="detail")
        assert key == "detail:lease:1"

    def test_no_prefix(self):
        key = get_cache_key("building", 5)
        assert key == "building:5"

    def test_keyword_args_sorted(self):
        key = get_cache_key(prefix="apt", building_id=5, apartment=10)
        assert "apt" in key
        assert "apartment=10" in key
        assert "building_id=5" in key

    def test_long_key_gets_hashed(self):
        long_parts = ["x" * 50] * 10
        key = get_cache_key(*long_parts, prefix="prefix")
        assert "hash" in key

    def test_model_name_in_args_via_string(self):
        key = get_cache_key("Building", 1, prefix="obj")
        assert "Building" in key
        assert "1" in key

    def test_empty_prefix_omitted(self):
        key = get_cache_key("item", prefix="")
        assert key == "item"

    def test_multiple_positional_args(self):
        key = get_cache_key("a", "b", "c")
        assert key == "a:b:c"


@pytest.mark.unit
class TestGetModelCacheKey:
    def test_with_pk_and_action(self):
        key = get_model_cache_key("Lease", pk=1, action="detail")
        assert key == "model:Lease:1:detail"

    def test_without_pk(self):
        key = get_model_cache_key("Apartment", action="list")
        assert key == "model:Apartment:list"

    def test_without_action(self):
        key = get_model_cache_key("Tenant", pk=5)
        assert key == "model:Tenant:5"

    def test_model_name_only(self):
        key = get_model_cache_key("Building")
        assert key == "model:Building"


@pytest.mark.unit
class TestCacheResult:
    @override_settings(CACHES=LOCMEM_CACHE)
    def test_caches_return_value(self):
        call_count = {"n": 0}

        @cache_result(timeout=60)
        def expensive_func(x):
            call_count["n"] += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count["n"] == 1

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_different_args_cached_separately(self):
        call_count = {"n": 0}

        @cache_result(timeout=60)
        def separate_func(x):
            call_count["n"] += 1
            return x * 2

        separate_func(5)
        separate_func(10)

        assert call_count["n"] == 2

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_key_prefix_used(self):
        from django.core.cache import cache

        @cache_result(timeout=60, key_prefix="myprefix")
        def my_func(x):
            return x + 1

        result = my_func(3)
        assert result == 4

        cached = cache.get("myprefix:3")
        assert cached == 4

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_function_name_used_as_prefix_when_no_prefix(self):
        from django.core.cache import cache

        @cache_result(timeout=60)
        def named_unique_func(x):
            return x + 100

        named_unique_func(7)
        cached = cache.get("named_unique_func:7")
        assert cached == 107

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_cache_miss_executes_function(self):
        call_count = {"n": 0}

        @cache_result(timeout=60)
        def miss_fn(x):
            call_count["n"] += 1
            return x

        miss_fn(99)
        assert call_count["n"] == 1

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_cached_none_not_returned_from_cache(self):
        """If function returns None, cache.get returns None on both hit and miss, so re-executes."""
        call_count = {"n": 0}

        @cache_result(timeout=60)
        def returns_none():
            call_count["n"] += 1
            return None

        returns_none()
        returns_none()
        assert call_count["n"] == 2


@pytest.mark.unit
class TestCacheManager:
    @override_settings(CACHES=LOCMEM_CACHE)
    def test_clear_all_returns_true(self):
        from django.core.cache import cache

        cache.set("some_key", "some_value")
        result = CacheManager.clear_all()
        assert result is True
        assert cache.get("some_key") is None

    def test_invalidate_pattern_without_redis_returns_zero(self):
        # Tests run without Redis; HAS_DJANGO_REDIS may be True but connection fails gracefully
        count = CacheManager.invalidate_pattern("*Building*")
        # Either 0 (no Redis) or exception caught and returns 0
        assert count == 0

    def test_invalidate_model_without_redis_returns_zero(self):
        count = CacheManager.invalidate_model("Building", pk=1)
        assert count == 0

    def test_invalidate_model_all_without_redis_returns_zero(self):
        count = CacheManager.invalidate_model("Building")
        assert count == 0

    def test_get_cache_stats_without_redis(self):
        stats = CacheManager.get_cache_stats()
        assert "total_keys" in stats
        assert "keyspace_hits" in stats
        assert "keyspace_misses" in stats
        assert "hit_rate" in stats


@pytest.mark.unit
class TestInvalidateRelatedCaches:
    def test_runs_without_error(self, mocker):
        mock_instance = mocker.MagicMock()
        mock_instance.__class__.__name__ = "Building"
        mock_instance.pk = 9903
        # Should not raise — invalidate_pattern handles Redis errors gracefully
        invalidate_related_caches(mock_instance, ["Apartment", "Lease"])


@pytest.mark.unit
class TestGetCacheKeyWithModelInstance:
    """Covers lines 72, 79: Model instance handling in get_cache_key."""

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_model_instance_in_positional_args(self):
        """Covers line 72: model instance mapped to 'ClassName:pk' in positional args."""
        from django.contrib.auth.models import User

        class FakeModel:
            pk = 42

            class __class__:
                __name__ = "FakeModel"

        # Use a real Django model instance to exercise the isinstance(arg, Model) branch
        user = User(pk=99)
        key = get_cache_key(user, prefix="test")
        assert "User:99" in key

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_model_instance_in_keyword_args(self):
        """Covers line 79: model instance in keyword args."""
        from django.contrib.auth.models import User

        user = User(pk=77)
        key = get_cache_key(prefix="kw", obj=user)
        assert "User:77" in key

    def test_long_key_has_prefix_and_hash(self):
        """Covers line 88: long key fallback with explicit prefix."""
        many_parts = ["z" * 25] * 10
        key = get_cache_key(*many_parts, prefix="myprefix")
        assert key.startswith("myprefix:hash:")


@pytest.mark.unit
class TestCacheManagerInvalidateWithRedis:
    """Covers the HAS_DJANGO_REDIS=True path in invalidate_pattern by simulating it."""

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_invalidate_pattern_with_redis_exception_returns_zero(self, mocker):
        """Covers lines 232-237: get_redis_connection raises, exception caught → returns 0."""
        mocker.patch("core.cache.HAS_DJANGO_REDIS", True)
        mocker.patch(
            "core.cache.get_redis_connection",
            side_effect=Exception("Redis connection refused"),
        )
        count = CacheManager.invalidate_pattern("*anything*")
        assert count == 0

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_invalidate_pattern_with_redis_no_matching_keys(self, mocker):
        """Covers lines 239-244: keys found is empty → returns 0."""
        mock_redis = mocker.MagicMock()
        mock_redis.keys.return_value = []
        mocker.patch("core.cache.HAS_DJANGO_REDIS", True)
        mocker.patch("core.cache.get_redis_connection", return_value=mock_redis)
        count = CacheManager.invalidate_pattern("*no_match*")
        assert count == 0

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_invalidate_pattern_with_redis_deletes_matching_keys(self, mocker):
        """Covers lines 239-242: keys found and deleted."""
        mock_redis = mocker.MagicMock()
        mock_redis.keys.return_value = [b"condominios:1:SomeModel:1"]
        mock_redis.delete.return_value = 1
        mocker.patch("core.cache.HAS_DJANGO_REDIS", True)
        mocker.patch("core.cache.get_redis_connection", return_value=mock_redis)
        count = CacheManager.invalidate_pattern("*SomeModel*")
        assert count == 1

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_clear_all_exception_returns_false(self, mocker):
        """Covers lines 261-263: cache.clear() raises → returns False."""
        mock_cache = mocker.MagicMock()
        mock_cache.clear.side_effect = Exception("clear failed")
        mocker.patch("core.cache.cache", mock_cache)
        result = CacheManager.clear_all()
        assert result is False

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_get_cache_stats_without_redis_returns_zeros(self, mocker):
        """Covers line 281: HAS_DJANGO_REDIS=False branch returns zero stats."""
        mocker.patch("core.cache.HAS_DJANGO_REDIS", False)
        stats = CacheManager.get_cache_stats()
        assert stats["total_keys"] == 0
        assert stats["keyspace_hits"] == 0
        assert stats["keyspace_misses"] == 0
        assert stats["hit_rate"] == 0.0

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_get_cache_stats_with_redis(self, mocker):
        """Covers lines 288-306: HAS_DJANGO_REDIS=True, get_redis_connection used."""
        mock_redis = mocker.MagicMock()
        mock_redis.info.return_value = {"keyspace_hits": 100, "keyspace_misses": 20}
        mock_redis.keys.return_value = [b"key1", b"key2"]
        mocker.patch("core.cache.HAS_DJANGO_REDIS", True)
        mocker.patch("core.cache.get_redis_connection", return_value=mock_redis)
        stats = CacheManager.get_cache_stats()
        assert stats["total_keys"] == 2
        assert stats["keyspace_hits"] == 100
        assert stats["keyspace_misses"] == 20
        assert stats["hit_rate"] > 0

    @override_settings(CACHES=LOCMEM_CACHE)
    def test_get_cache_stats_exception_returns_zeros(self, mocker):
        """Covers lines 307-314: get_redis_connection raises in get_cache_stats → zeros."""
        mocker.patch("core.cache.HAS_DJANGO_REDIS", True)
        mocker.patch(
            "core.cache.get_redis_connection",
            side_effect=Exception("Redis down"),
        )
        stats = CacheManager.get_cache_stats()
        assert stats["total_keys"] == 0
