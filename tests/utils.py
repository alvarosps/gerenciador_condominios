"""Shared test-only helper functions (not fixtures — importable directly by any test module)."""

from django.core.cache import cache
from django.db import connections
from django.test import TestCase

import core.cache


def flush_on_commit_callbacks(using: str = "default") -> None:
    """Run every currently-queued transaction.on_commit callback immediately.

    CacheManager.invalidate_pattern defers its real deletion to transaction.on_commit (P4.2
    item (d)) so a concurrent read cannot re-populate the cache with pre-commit data.
    pytest-django wraps each test in an outer atomic transaction that is rolled back at the
    end, so those callbacks never fire on their own — a "write, then assert the cache was
    invalidated" test must flush them explicitly.

    Unlike calling ``TestCase.captureOnCommitCallbacks`` directly (also exposed as the
    ``django_capture_on_commit_callbacks`` pytest-django fixture) — which only replays
    callbacks registered from its own ``with`` block onward — this drains whatever is ALREADY
    queued: the common case for a test that calls ``obj.save()`` first and only then wants to
    assert the side effect. The already-queued callbacks are moved out of the way and handed
    back to the connection from inside the ``with`` block, so captureOnCommitCallbacks sees
    them as newly added and replays them (execute=True) with its own robust-callback handling
    — avoiding a direct, stub-mistyped unpack of connection.run_on_commit's 3-tuple entries
    (django-stubs still types it as a 2-tuple; Django 5.0+ added the "robust" flag).
    """
    connection = connections[using]
    pending, connection.run_on_commit = connection.run_on_commit, []
    with TestCase.captureOnCommitCallbacks(using=using, execute=True):
        connection.run_on_commit = pending


def set_tracked_cache_probe(key: str, value: str = "x") -> None:
    """Set a cache key AND register it exactly like @cache_result does (core.cache._TRACKED_CACHE_KEYS).

    P4.2 item (e): CacheManager's LocMem fallback only deletes keys it knows it created (the
    registry populated by @cache_result), so it can never touch a raw cache.set() key —
    otherwise unrelated keys (DRF throttle counters, etc.) could be wiped too. A "probe" key
    that simulates a warm @cache_result cache entry for an invalidation test must therefore be
    registered the same way, or invalidate_pattern() will correctly (but confusingly, for the
    test) never clear it.
    """
    cache.set(key, value)
    core.cache._TRACKED_CACHE_KEYS.add(key)
