"""Session 34 — tests for Building.condominium FK + the phased backfill.

The FK is non-null with on_delete=PROTECT and related_name="buildings". The
factories give make_building a default condominium so every building always has
one (no null column after the migration backfill).
"""

import pytest
from django.db import transaction
from django.db.models import ProtectedError

from core.models import DEFAULT_CONDOMINIUM_NAME, Building, Condominium
from tests.factories import make_building, make_condominium


@pytest.mark.django_db
def test_make_building_default_condominium_not_null() -> None:
    building = make_building()
    assert building.condominium is not None
    assert isinstance(building.condominium, Condominium)


@pytest.mark.django_db
def test_make_building_respects_passed_condominium() -> None:
    cond = make_condominium()
    building = make_building(condominium=cond)
    assert building.condominium_id == cond.id


@pytest.mark.django_db
def test_condominium_is_protected_on_hard_delete() -> None:
    cond = make_condominium()
    make_building(condominium=cond)
    with pytest.raises(ProtectedError), transaction.atomic():
        cond.delete(hard_delete=True)


@pytest.mark.django_db
def test_related_name_buildings() -> None:
    cond = make_condominium()
    building = make_building(condominium=cond)
    assert list(cond.buildings.all()) == [building]


@pytest.mark.django_db
def test_no_building_has_null_condominium() -> None:
    make_building()
    make_building(street_number=200)
    assert not Building.objects.filter(condominium__isnull=True).exists()


@pytest.mark.django_db
def test_building_save_defaults_to_singleton_condominium() -> None:
    """Building.objects.create without a condominium falls back to the default."""
    building = Building.objects.create(
        street_number=999, name="Sem Condomínio", address="Rua X, 999"
    )
    assert building.condominium is not None
    assert building.condominium.name == DEFAULT_CONDOMINIUM_NAME
