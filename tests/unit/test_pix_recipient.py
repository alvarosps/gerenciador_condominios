"""Unit tests for PixService.resolve_pix_recipient — recipient/city resolution."""

from decimal import Decimal

import pytest

from core.models import FinancialSettings, Landlord
from core.services.pix_service import _DEFAULT_CITY, resolve_pix_recipient
from tests.factories import make_apartment, make_lease, make_person, make_tenant


def _make_lease_with_apartment(admin_user):
    apartment = make_apartment(number=701, user=admin_user, rental_value=Decimal("1500.00"))
    tenant = make_tenant(user=admin_user)
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        rental_value=Decimal("1500.00"),
    )


def _make_landlord(admin_user, **kwargs):
    defaults = {
        "name": "Locador Teste",
        "marital_status": "Casado(a)",
        "cpf_cnpj": "12345678901",
        "phone": "11999990000",
        "street": "Rua Locador",
        "street_number": "100",
        "neighborhood": "Centro",
        "city": "Porto Alegre",
        "state": "RS",
        "zip_code": "90000-000",
        "is_active": True,
        "created_by": admin_user,
        "updated_by": admin_user,
    }
    defaults.update(kwargs)
    return Landlord.objects.create(**defaults)


@pytest.mark.unit
@pytest.mark.django_db
class TestResolvePixRecipient:
    def test_owner_pix_key_takes_precedence(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        owner = make_person(
            user=admin_user,
            name="André Owner",
            pix_key="andre@apto.com",
            pix_key_type="email",
            is_owner=True,
        )
        lease.apartment.owner = owner
        lease.apartment.save(update_fields=["owner"])

        recipient = resolve_pix_recipient(lease)

        assert recipient["pix_key"] == "andre@apto.com"
        assert recipient["pix_key_type"] == "email"
        assert recipient["merchant_name"] == "André Owner"

    def test_falls_back_to_financialsettings_default_key(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date="2026-01-01",
            default_pix_key="condominio@pix.com",
            default_pix_key_type="email",
        )

        recipient = resolve_pix_recipient(lease)

        assert recipient["pix_key"] == "condominio@pix.com"
        assert recipient["pix_key_type"] == "email"

    def test_merchant_name_from_active_landlord(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        _make_landlord(admin_user, name="Locador Ativo")

        recipient = resolve_pix_recipient(lease)

        assert recipient["merchant_name"] == "Locador Ativo"

    def test_default_merchant_name_when_no_owner_or_landlord(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)

        recipient = resolve_pix_recipient(lease)

        assert recipient["merchant_name"] == "Condomínio"

    def test_city_from_landlord(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        _make_landlord(admin_user, city="Porto Alegre")

        recipient = resolve_pix_recipient(lease)

        assert recipient["city"] == "Porto Alegre"

    def test_city_from_financialsettings_when_no_landlord(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date="2026-01-01",
            default_city="Canoas",
        )

        recipient = resolve_pix_recipient(lease)

        assert recipient["city"] == "Canoas"

    def test_landlord_city_takes_precedence_over_financialsettings(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)
        FinancialSettings.objects.create(
            initial_balance=Decimal("0.00"),
            initial_balance_date="2026-01-01",
            default_city="Canoas",
        )
        _make_landlord(admin_user, city="Porto Alegre")

        recipient = resolve_pix_recipient(lease)

        assert recipient["city"] == "Porto Alegre"

    def test_city_falls_back_to_default_constant(self, admin_user):
        lease = _make_lease_with_apartment(admin_user)

        recipient = resolve_pix_recipient(lease)

        assert recipient["city"] == _DEFAULT_CITY
        assert _DEFAULT_CITY == "Porto Alegre"
