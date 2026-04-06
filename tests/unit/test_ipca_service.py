"""Unit tests for core/services/ipca_service.py."""

import re

import pytest
import responses as responses_lib
from datetime import date
from decimal import Decimal

from core.models import IPCAIndex
from core.services.ipca_service import IPCAService

# Match any URL that hits the IBGE SIDRA endpoint regardless of the period param
_SIDRA_URL_PATTERN = re.compile(r"https://apisidra\.ibge\.gov\.br/values/t/1737/.*")


def _make_sidra_response(entries: list[dict]) -> list[dict]:
    """Build a SIDRA-formatted response: header row + data rows."""
    header = {"D3C": "Período", "V": "Valor"}
    return [header] + entries


@pytest.mark.unit
class TestIPCAServiceFetchLatest:
    @responses_lib.activate
    def test_fetch_saves_new_indices(self):
        responses_lib.add(
            responses_lib.GET,
            _SIDRA_URL_PATTERN,
            json=_make_sidra_response([
                {"D3C": "202301", "V": "5965.53"},
                {"D3C": "202302", "V": "5992.31"},
            ]),
            status=200,
        )

        IPCAIndex.objects.all().delete()
        result = IPCAService.fetch_latest()

        assert result is not None
        assert IPCAIndex.objects.filter(reference_month=date(2023, 2, 1)).exists()

    @responses_lib.activate
    def test_fetch_returns_latest_on_api_error(self):
        # Pre-populate one index so we have something to return
        IPCAIndex.objects.get_or_create(
            reference_month=date(2023, 1, 1),
            defaults={"value": Decimal("5965.53")},
        )

        responses_lib.add(
            responses_lib.GET,
            _SIDRA_URL_PATTERN,
            status=500,
        )

        result = IPCAService.fetch_latest()

        # Should return the existing latest rather than raising
        assert result is not None
        assert result.reference_month >= date(2023, 1, 1)

    @responses_lib.activate
    def test_fetch_handles_empty_response(self):
        responses_lib.add(
            responses_lib.GET,
            _SIDRA_URL_PATTERN,
            json=[],
            status=200,
        )

        result = IPCAService.fetch_latest()

        # No crash — returns whatever is in the DB (may be None)
        assert result is None or isinstance(result, IPCAIndex)

    @responses_lib.activate
    def test_fetch_skips_invalid_rows(self):
        # Ensure there is no index for 2023-04 so we can check it gets created
        IPCAIndex.objects.filter(reference_month=date(2023, 4, 1)).delete()
        initial_count = IPCAIndex.objects.count()

        responses_lib.add(
            responses_lib.GET,
            _SIDRA_URL_PATTERN,
            json=_make_sidra_response([
                {"D3C": "999999", "V": "..."},     # invalid period + placeholder value
                {"D3C": "202303", "V": "-"},        # dash placeholder
                {"D3C": "202304", "V": "6020.00"},  # valid
            ]),
            status=200,
        )

        IPCAService.fetch_latest()

        # Only the valid row should be stored
        assert IPCAIndex.objects.filter(reference_month=date(2023, 4, 1)).exists()
        # Invalid rows must not have increased count beyond the one valid row
        assert IPCAIndex.objects.count() <= initial_count + 1


@pytest.mark.unit
class TestIPCAServiceGetAdjustmentFactor:
    def test_returns_factor_when_indices_exist(self):
        IPCAIndex.objects.get_or_create(
            reference_month=date(2023, 12, 1),
            defaults={"value": Decimal("6000.00")},
        )
        IPCAIndex.objects.get_or_create(
            reference_month=date(2024, 3, 1),
            defaults={"value": Decimal("6180.00")},
        )

        # IBGE methodology: uses index of month BEFORE start_month
        # start_month=2024-01-01 → index_start = 2023-12-01
        # end_month=2024-03-01 → index_end = 2024-03-01
        factor = IPCAService.get_adjustment_factor(
            start_month=date(2024, 1, 1),
            end_month=date(2024, 3, 1),
        )

        assert factor is not None
        expected = Decimal("6180.00") / Decimal("6000.00")
        assert factor == expected

    def test_returns_none_when_start_index_missing(self):
        # Ensure that a start index for this specific month is not in DB
        IPCAIndex.objects.filter(reference_month=date(2020, 5, 1)).delete()

        factor = IPCAService.get_adjustment_factor(
            start_month=date(2020, 6, 1),  # needs 2020-05 index
            end_month=date(2021, 6, 1),
        )

        assert factor is None

    def test_returns_none_when_end_index_missing(self):
        IPCAIndex.objects.get_or_create(
            reference_month=date(2021, 11, 1),
            defaults={"value": Decimal("5800.00")},
        )
        IPCAIndex.objects.filter(reference_month=date(2025, 6, 1)).delete()

        factor = IPCAService.get_adjustment_factor(
            start_month=date(2021, 12, 1),
            end_month=date(2025, 6, 1),
        )

        assert factor is None

    def test_returns_none_when_start_index_is_zero(self):
        IPCAIndex.objects.update_or_create(
            reference_month=date(2022, 5, 1),
            defaults={"value": Decimal("0")},
        )
        IPCAIndex.objects.get_or_create(
            reference_month=date(2022, 8, 1),
            defaults={"value": Decimal("6050.00")},
        )

        factor = IPCAService.get_adjustment_factor(
            start_month=date(2022, 6, 1),  # uses index 2022-05 = 0
            end_month=date(2022, 8, 1),
        )

        assert factor is None


@pytest.mark.unit
class TestIPCAServiceGetAdjustmentPercentage:
    def test_returns_percentage_from_factor(self):
        IPCAIndex.objects.get_or_create(
            reference_month=date(2023, 5, 1),
            defaults={"value": Decimal("6000.00")},
        )
        IPCAIndex.objects.get_or_create(
            reference_month=date(2023, 8, 1),
            defaults={"value": Decimal("6120.00")},
        )

        # factor = 6120/6000 = 1.02 → percentage = 2.00%
        pct = IPCAService.get_adjustment_percentage(
            start_month=date(2023, 6, 1),
            end_month=date(2023, 8, 1),
        )

        assert pct is not None
        assert pct == Decimal("2.00")

    def test_returns_none_when_indices_unavailable(self):
        IPCAIndex.objects.filter(reference_month=date(2018, 1, 1)).delete()

        pct = IPCAService.get_adjustment_percentage(
            start_month=date(2018, 2, 1),
            end_month=date(2018, 6, 1),
        )

        assert pct is None


@pytest.mark.unit
class TestIPCAServiceGetLatestAvailableMonth:
    def test_returns_most_recent_month(self):
        IPCAIndex.objects.get_or_create(
            reference_month=date(2024, 1, 1),
            defaults={"value": Decimal("6200.00")},
        )
        IPCAIndex.objects.get_or_create(
            reference_month=date(2024, 2, 1),
            defaults={"value": Decimal("6215.00")},
        )

        result = IPCAService.get_latest_available_month()

        assert result is not None
        # Must be at least as recent as the ones we just inserted
        assert result >= date(2024, 2, 1)

    def test_returns_none_when_no_indices(self):
        IPCAIndex.objects.all().delete()

        result = IPCAService.get_latest_available_month()

        assert result is None
