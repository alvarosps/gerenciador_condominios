"""P4.2: a Redis outage must degrade to a cache miss (serve from DB), never a 500.

django-redis ``IGNORE_EXCEPTIONS=True`` swallows connection errors on ``cache.get``/``cache.set``
so both ``@cache_result`` and the DRF throttle (which share the default cache via the dynamic
``django.core.cache.cache`` proxy) fail open. These tests point the default cache at a dead Redis
port (connection refused) to exercise that path end-to-end — the LocMem test cache cannot, because
it never raises. This guards the P4.2 acceptance criterion that the ``IGNORE_EXCEPTIONS`` setting
actually degrades gracefully.
"""

import pytest
from django.test import override_settings
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

# Mirrors settings.py's prod RedisCache OPTIONS but points at a port with nothing listening, so the
# first connection attempt is refused. IGNORE_EXCEPTIONS turns that refusal into a cache miss.
_DEAD_REDIS_CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6399/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 1,
            "SOCKET_TIMEOUT": 1,
        },
        "KEY_PREFIX": "condominios",
        "TIMEOUT": 300,
    }
}


@pytest.mark.integration
@pytest.mark.django_db
class TestCacheResilienceRedisDown:
    def setup_method(self) -> None:
        self.client = APIClient()
        self.client.force_authenticate(
            user=baker.make("auth.User", is_staff=True, is_superuser=True)
        )

    @override_settings(CACHES=_DEAD_REDIS_CACHES, DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS=True)
    def test_cached_endpoint_serves_from_db_when_redis_down(self) -> None:
        # The @cache_result on the rent-adjustment-alerts endpoint calls cache.get (connection
        # refused) -> IGNORE_EXCEPTIONS swallows it -> miss -> recompute from DB -> 200, not 500.
        response = self.client.get("/api/dashboard/rent_adjustment_alerts/")

        assert response.status_code == status.HTTP_200_OK

    @override_settings(CACHES=_DEAD_REDIS_CACHES, DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS=True)
    def test_throttle_does_not_500_when_redis_down(self) -> None:
        # AnonRateThrottle (DEFAULT_THROTTLE_CLASSES) shares the default cache; with Redis down its
        # cache.get/set are swallowed, so it fails open (allows the request) instead of 500ing.
        # Bad credentials make this an anonymous, throttled request — the assertion is only that the
        # broken cache did not turn it into a 500.
        response = self.client.post(
            "/api/auth/token/", {"username": "nobody", "password": "wrong"}, format="json"
        )

        assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR
