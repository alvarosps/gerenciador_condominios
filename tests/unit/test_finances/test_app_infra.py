"""Session 34 — infrastructure tests for the `finances` app + `core.Condominium`.

Covers: app installed + FinancesConfig + ready() importing signals; the new
core.Condominium model (mixins, dual managers, __str__); the migration-created
default record; and RLS enabled on core_condominium.
"""

import importlib
import sys

import pytest
from django.apps import apps
from django.conf import settings
from django.db import connection, models
from finances.apps import FinancesConfig

from core.models import (
    DEFAULT_CONDOMINIUM_NAME,
    AuditMixin,
    Condominium,
    SoftDeleteManager,
    SoftDeleteMixin,
)


def test_finances_app_installed() -> None:
    assert "finances" in settings.INSTALLED_APPS


def test_finances_app_config() -> None:
    config = apps.get_app_config("finances")
    assert isinstance(config, FinancesConfig)
    assert config.name == "finances"


def test_ready_imports_signals() -> None:
    """FinancesConfig.ready() imports finances.signals (no error)."""
    module = importlib.import_module("finances.signals")
    assert module is not None
    assert "finances.signals" in sys.modules


def test_condominium_inherits_mixins() -> None:
    field_names = {f.name for f in Condominium._meta.get_fields()}
    assert {"created_at", "updated_at", "is_deleted"} <= field_names
    assert issubclass(Condominium, AuditMixin)
    assert issubclass(Condominium, SoftDeleteMixin)


def test_condominium_dual_managers() -> None:
    assert isinstance(Condominium.objects, SoftDeleteManager)
    assert type(Condominium.all_objects) is models.Manager


def test_condominium_str() -> None:
    cond = Condominium(name="Meu Condomínio")
    assert str(cond) == "Meu Condomínio"


@pytest.mark.django_db
def test_default_condominium_record_created_by_migration() -> None:
    """The data-migration creates exactly one default Condominium."""
    assert Condominium.objects.filter(name=DEFAULT_CONDOMINIUM_NAME).count() == 1


@pytest.mark.django_db
def test_get_default_resolves_singleton() -> None:
    """get_default() returns the migration-created singleton (lowest id)."""
    default = Condominium.get_default()
    assert default is not None
    assert default.name == DEFAULT_CONDOMINIUM_NAME
    assert default == Condominium.objects.order_by("id").first()


@pytest.mark.django_db
def test_get_default_returns_none_when_no_condominium() -> None:
    """With no condominium at all, get_default() is None (callers raise a PT error)."""
    Condominium.all_objects.all().delete()
    assert Condominium.get_default() is None


@pytest.mark.django_db
def test_condominium_table_has_rls_enabled() -> None:
    """core_condominium must have Row Level Security enabled (Supabase rule)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity FROM pg_class WHERE relname = %s",
            ["core_condominium"],
        )
        row = cursor.fetchone()
    assert row is not None
    assert row[0] is True
