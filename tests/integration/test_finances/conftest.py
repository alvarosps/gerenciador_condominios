"""Shared fixtures for the finances API integration tests."""

import pytest
from django.conf import settings
from django.test import override_settings

# DRF binds SimpleRateThrottle.timer = time.time as a class attribute, so under freezegun
# it is called as a bound method and raises. Throttling is infra, not application logic.
_REST_FRAMEWORK_NO_THROTTLE = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}


@pytest.fixture(autouse=True)
def _disable_throttling():
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_NO_THROTTLE):
        yield
