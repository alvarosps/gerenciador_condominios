"""Tests for the marital_status normalization map (migration 0052, HF-1)."""

import importlib

import pytest

from core.models import Tenant

_migration = importlib.import_module("core.migrations.0052_alter_landlord_marital_status_and_more")


@pytest.mark.unit
class TestMaritalStatusNormalizationMap:
    def test_all_mapped_values_point_to_canonical_choices(self) -> None:
        canonical = {value for value, _ in Tenant.MARITAL_STATUS_CHOICES}
        assert set(_migration.MARITAL_STATUS_NORMALIZATION.values()) <= canonical

    def test_no_mapped_value_is_itself_a_legacy_key(self) -> None:
        mapping = _migration.MARITAL_STATUS_NORMALIZATION
        assert not set(mapping.values()) & set(mapping.keys())

    def test_feminine_forms_map_to_neutral_a_forms(self) -> None:
        mapping = _migration.MARITAL_STATUS_NORMALIZATION
        assert mapping["Solteira"] == "Solteiro(a)"
        assert mapping["Casada"] == "Casado(a)"
        assert mapping["Divorciada"] == "Divorciado(a)"
        assert mapping["Viúva"] == "Viúvo(a)"

    def test_placeholder_dash_is_not_in_the_map(self) -> None:
        """'-' é ambíguo (correção manual via runbook) — a migration não inventa valor."""
        assert "-" not in _migration.MARITAL_STATUS_NORMALIZATION
