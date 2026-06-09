"""finances.Category — serializer condominium default + seed starter categories.

CategorySerializer defaults the singleton condominium on create (no client-side selector) and
keeps the existing one on update; seed_condo_utilities seeds a starter root set. ORM is real.
"""

import json
from pathlib import Path

import pytest
from django.core.management import call_command
from finances.models import Category
from finances.serializers import CategorySerializer

from core.models import Condominium
from tests.factories import make_condominium

pytestmark = pytest.mark.django_db


def test_serializer_defaults_condominium_when_omitted() -> None:
    make_condominium()
    serializer = CategorySerializer(data={"name": "Impostos"})
    assert serializer.is_valid(), serializer.errors
    category = serializer.save()
    assert category.condominium == Condominium.get_default()
    assert category.name == "Impostos"


def test_serializer_keeps_condominium_on_update() -> None:
    condo = make_condominium()
    existing = Category.objects.create(condominium=condo, name="Impostos")
    serializer = CategorySerializer(existing, data={"name": "Tributos"}, partial=True)
    assert serializer.is_valid(), serializer.errors
    updated = serializer.save()
    assert updated.condominium == condo
    assert updated.name == "Tributos"


def test_seed_creates_starter_categories(tmp_path: Path) -> None:
    make_condominium()
    fixture = {
        "categorias": [
            {"name": "Serviços/Utilidades", "sort_order": 1},
            {"name": "Impostos", "sort_order": 2},
            {"name": "Outros", "sort_order": 5},
        ]
    }
    path = tmp_path / "categorias.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")

    call_command("seed_condo_utilities", "--file", str(path))

    names = set(Category.objects.values_list("name", flat=True))
    assert {"Serviços/Utilidades", "Impostos", "Outros"} <= names

    # Idempotent: a second run does not duplicate.
    call_command("seed_condo_utilities", "--file", str(path))
    assert Category.objects.filter(name="Impostos").count() == 1
