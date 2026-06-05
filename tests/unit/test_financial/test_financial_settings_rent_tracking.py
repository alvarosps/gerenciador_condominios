"""Unit tests for FinancialSettings.rent_tracking_start_date field."""

from datetime import date
from decimal import Decimal

import pytest

from core.models import FinancialSettings
from core.serializers import FinancialSettingsSerializer


@pytest.mark.unit
class TestFinancialSettingsRentTrackingStartDate:
    def test_default_is_none(self):
        settings = FinancialSettings(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        assert settings.rent_tracking_start_date is None

    def test_value_round_trips_through_db(self):
        tracking_date = date(2026, 6, 1)
        obj = FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=tracking_date,
        )
        refreshed = FinancialSettings.objects.get(pk=obj.pk)
        assert refreshed.rent_tracking_start_date == tracking_date


@pytest.mark.unit
class TestFinancialSettingsSerializerRentTracking:
    def test_field_present_in_output_when_null(self):
        obj = FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        serializer = FinancialSettingsSerializer(obj)
        assert "rent_tracking_start_date" in serializer.data
        assert serializer.data["rent_tracking_start_date"] is None

    def test_field_present_in_output_when_set(self):
        tracking_date = date(2026, 6, 1)
        obj = FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=tracking_date,
        )
        serializer = FinancialSettingsSerializer(obj)
        assert serializer.data["rent_tracking_start_date"] == "2026-06-01"

    def test_write_accepts_rent_tracking_start_date(self):
        obj = FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
        )
        serializer = FinancialSettingsSerializer(
            obj,
            data={
                "initial_balance": "0.00",
                "initial_balance_date": "2026-01-01",
                "rent_tracking_start_date": "2026-06-01",
            },
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.rent_tracking_start_date == date(2026, 6, 1)

    def test_write_accepts_null_rent_tracking_start_date(self):
        obj = FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date=date(2026, 1, 1),
            rent_tracking_start_date=date(2026, 6, 1),
        )
        serializer = FinancialSettingsSerializer(
            obj,
            data={
                "initial_balance": "0.00",
                "initial_balance_date": "2026-01-01",
                "rent_tracking_start_date": None,
            },
        )
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.rent_tracking_start_date is None
