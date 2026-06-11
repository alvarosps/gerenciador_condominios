"""Unit tests for ContractService path helpers (SSOT of the contract PDF location)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings

from core.services.contract_service import ContractService
from tests.factories import make_apartment, make_building, make_lease, make_tenant


@pytest.fixture
def building(admin_user):
    return make_building(street_number=836, user=admin_user, name="Edifício SSOT")


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(building=building, number=101, user=admin_user)


@pytest.fixture
def tenant(admin_user):
    return make_tenant(cpf_cnpj="52998224725", user=admin_user, name="Inquilino SSOT")


@pytest.fixture
def lease(apartment, tenant, admin_user):
    return make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date=date(2026, 1, 1),
        validity_months=12,
        rental_value=Decimal("1500.00"),
    )


@pytest.mark.unit
class TestGetContractAbsolutePath:
    def test_caminho_resolvido_pela_ssot(self, lease):
        """get_contract_absolute_path == BASE_DIR/PDF_OUTPUT_DIR/get_contract_relative_path."""
        relative = ContractService.get_contract_relative_path(lease)
        expected = Path(settings.BASE_DIR) / settings.PDF_OUTPUT_DIR / relative

        absolute = ContractService.get_contract_absolute_path(lease)

        assert absolute == expected

    def test_returns_path_object(self, lease):
        assert isinstance(ContractService.get_contract_absolute_path(lease), Path)
