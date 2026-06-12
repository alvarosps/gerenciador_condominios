"""Tests for the CPF/CNPJ normalization data migration (0055).

Exercise the ``normalize_documents`` forward function directly against the real ORM (the
migration uses ``apps.get_model`` + ``_base_manager``, so passing the live ``apps`` registry runs
the same code path). Mock policy: nothing external — real DB in an atomic block.
"""

import importlib

import pytest
from django.apps import apps as global_apps

from core.models import Tenant
from tests.factories import make_tenant

_migration = importlib.import_module("core.migrations.0055_normalize_cpf_cnpj")


@pytest.mark.unit
class TestCpfNormalizationMigration:
    def test_normalize_helper_strips_formatting(self) -> None:
        assert _migration._normalize("529.982.247-25") == "52998224725"
        assert _migration._normalize("11.222.333/0001-81") == "11222333000181"
        assert _migration._normalize("") == ""

    def test_normalizes_existing_formatted_tenant(self) -> None:
        # Bypass the model's clean()-time normalization to seed a formatted value, mimicking
        # the legacy rows the migration must fix.
        tenant = make_tenant(cpf_cnpj="52998224725")
        Tenant.all_objects.filter(pk=tenant.pk).update(cpf_cnpj="529.982.247-25")

        _migration.normalize_documents(global_apps, None)

        tenant.refresh_from_db()
        assert tenant.cpf_cnpj == "52998224725"

    def test_is_idempotent_on_already_normalized(self) -> None:
        tenant = make_tenant(cpf_cnpj="52998224725")
        _migration.normalize_documents(global_apps, None)
        tenant.refresh_from_db()
        assert tenant.cpf_cnpj == "52998224725"

    def test_aborts_on_active_collision(self) -> None:
        t1 = make_tenant(cpf_cnpj="52998224725")
        t2 = make_tenant(cpf_cnpj="11144477735")
        # Force two ACTIVE tenants that normalize to the same digits (formatted vs raw).
        Tenant.all_objects.filter(pk=t1.pk).update(cpf_cnpj="529.982.247-25")
        Tenant.all_objects.filter(pk=t2.pk).update(cpf_cnpj="52998224725")

        with pytest.raises(RuntimeError, match="collide"):
            _migration.normalize_documents(global_apps, None)

        # Nothing was written: the formatted row is untouched (no arbitrary pick).
        t1.refresh_from_db()
        assert t1.cpf_cnpj == "529.982.247-25"

    def test_tolerates_active_vs_deleted_collision(self) -> None:
        active = make_tenant(cpf_cnpj="52998224725")
        deleted = make_tenant(cpf_cnpj="11144477735")
        deleted.delete()  # soft delete
        # Both normalize to the same digits, but only one is active → constraint allows it.
        Tenant.all_objects.filter(pk=active.pk).update(cpf_cnpj="529.982.247-25")
        Tenant.all_objects.filter(pk=deleted.pk).update(cpf_cnpj="52998224725")

        _migration.normalize_documents(global_apps, None)  # must not raise

        active.refresh_from_db()
        assert active.cpf_cnpj == "52998224725"
