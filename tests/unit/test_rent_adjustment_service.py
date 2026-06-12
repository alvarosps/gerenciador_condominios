"""Unit tests for core/services/rent_adjustment_service.py."""

import re
from decimal import Decimal

import pytest
import responses as responses_lib
from model_bakery import baker

from core.models import IPCAIndex, Landlord
from core.services.rent_adjustment_service import RentAdjustmentService

# Match any URL that hits the IBGE SIDRA endpoint regardless of the period param
_SIDRA_URL_PATTERN = re.compile(r"https://apisidra\.ibge\.gov\.br/values/t/1737/.*")


@pytest.mark.unit
class TestGetEligibleLeasesNoExternalApi:
    @responses_lib.activate
    def test_get_eligible_leases_does_not_hit_external_api(self):
        # Regression (P5.1): the rent-adjustment alert dashboard must not make a
        # synchronous IBGE/SIDRA call in the request path. The cron does the fetch.
        responses_lib.add(responses_lib.GET, _SIDRA_URL_PATTERN, json=[], status=200)
        IPCAIndex.objects.all().delete()

        result = RentAdjustmentService.get_eligible_leases()

        assert len(responses_lib.calls) == 0
        assert isinstance(result, dict)
        assert "alerts" in result

    @responses_lib.activate
    def test_get_eligible_leases_uses_fallback_when_db_empty(self):
        # With no IPCA index, the percentage falls back to the active Landlord's
        # configured rate — no external call, no regression.
        responses_lib.add(responses_lib.GET, _SIDRA_URL_PATTERN, json=[], status=200)
        IPCAIndex.objects.all().delete()
        Landlord.objects.update(is_active=False)
        baker.make(Landlord, is_active=True, rent_adjustment_percentage=Decimal("4.50"))

        result = RentAdjustmentService.get_eligible_leases()

        assert len(responses_lib.calls) == 0
        assert result["ipca_latest_month"] is None
        # No IPCA → effective percentage falls back to the landlord's rate.
        assert result["ipca_percentage"] == "4.50"
        assert result["fallback_percentage"] == "4.50"
