"""P5.1: the rent-adjustment alerts endpoint is cached and invalidated via signals.

The endpoint (`GET /api/dashboard/rent_adjustment_alerts/`) used to run a synchronous
IBGE fetch + a full eligibility recompute on every load. It is now wrapped in
@cache_result(key_prefix="dashboard-rent-adjustment-alerts") and invalidated whenever a
Lease, RentAdjustment or Landlord is written (those feed the alert payload). The cache
key is the bare prefix because the action calls the cached function with no positional
args (default alert_months=2).
"""

from decimal import Decimal

import pytest
from django.core.cache import cache
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient

from core.models import IPCAIndex, Landlord
from core.signals import _CORE_MODEL_CACHE_PREFIXES, _PROPERTY_CACHE_PREFIXES

_ALERTS_KEY = "dashboard-rent-adjustment-alerts"
_ALERTS_URL = "/api/dashboard/rent_adjustment_alerts/"


@pytest.mark.integration
@pytest.mark.django_db
class TestRentAdjustmentAlertsCache:
    def setup_method(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.admin = baker.make("auth.User", is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=self.admin)

    def test_endpoint_caches_result(self) -> None:
        assert cache.get(_ALERTS_KEY) is None

        response = self.client.get(_ALERTS_URL)

        assert response.status_code == status.HTTP_200_OK
        # The payload is now in the cache — a second load is served without recomputing.
        assert cache.get(_ALERTS_KEY) is not None

    def test_landlord_save_invalidates_cache(self) -> None:
        # Discriminating: Landlord had NO signal receiver before P5.1, so without the new
        # receiver this save would leave the cache populated.
        self.client.get(_ALERTS_URL)
        assert cache.get(_ALERTS_KEY) is not None

        baker.make(Landlord, is_active=True, rent_adjustment_percentage=Decimal("4.50"))

        assert cache.get(_ALERTS_KEY) is None

    def test_ipca_index_save_invalidates_cache(self) -> None:
        # Discriminating: IPCAIndex had NO signal receiver at all before this fix, so without the
        # new receiver persisting a new index month (what the daily cron's fetch_latest does) would
        # leave the stale alert percentages cached until the 300s TTL. The alert payload derives
        # ipca_12m / suggested values from the latest IPCAIndex, so a new index must drop it.
        self.client.get(_ALERTS_URL)
        assert cache.get(_ALERTS_KEY) is not None

        baker.make(IPCAIndex)

        assert cache.get(_ALERTS_KEY) is None

    def test_alerts_prefix_wired_in_cache_maps(self) -> None:
        # The invalidation must be wired through the P4.2 model->prefix map, not a hand-rolled
        # invalidate_pattern call. On the LocMem test cache invalidate_pattern clears everything,
        # so a behavioural test alone can't prove the prefix is registered (a Tenant write already
        # clears every key via its other prefixes) — assert membership directly. Tenant carries the
        # prefix because the alert card embeds lease.responsible_tenant.name; IPCAIndex because the
        # suggested percentage derives from the latest index.
        assert _ALERTS_KEY in _PROPERTY_CACHE_PREFIXES
        for model_name in ("Lease", "RentAdjustment", "Landlord", "Tenant", "IPCAIndex"):
            assert _ALERTS_KEY in _CORE_MODEL_CACHE_PREFIXES[model_name]
