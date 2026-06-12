"""Tests for core.query_params — safe int/date parsing (malformed -> 400, not 500)."""

from datetime import date

import pytest
from rest_framework import serializers

from core.query_params import parse_date_param, parse_int_param


@pytest.mark.unit
class TestParseIntParam:
    def test_none_returns_none(self) -> None:
        assert parse_int_param(None, field="person_id") is None

    def test_empty_returns_none(self) -> None:
        assert parse_int_param("", field="person_id") is None

    def test_valid_returns_int(self) -> None:
        assert parse_int_param("42", field="person_id") == 42

    def test_zero_is_valid(self) -> None:
        assert parse_int_param("0", field="person_id") == 0

    def test_invalid_raises_validation_error(self) -> None:
        with pytest.raises(serializers.ValidationError):
            parse_int_param("abc", field="person_id")


@pytest.mark.unit
class TestParseDateParam:
    def test_none_returns_none(self) -> None:
        assert parse_date_param(None, field="start_date") is None

    def test_valid_iso_returns_date(self) -> None:
        assert parse_date_param("2026-03-15", field="start_date") == date(2026, 3, 15)

    def test_invalid_raises_validation_error(self) -> None:
        with pytest.raises(serializers.ValidationError):
            parse_date_param("15/03/2026", field="start_date")
