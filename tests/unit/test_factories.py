"""P6.1 — the factory CPF generator must yield valid, unique CPFs with no global order dependency.

The old module-global itertools.cycle over a finite list recycled values into Tenant.full_clean
under the parallel suite (cross-test flakiness). The counter-based _generate_valid_cpf replaces it.
"""

import pytest

from core.validators.brazilian import validate_cpf
from tests.factories import CPF_VALID_PRIMARY, _generate_valid_cpf, make_tenant

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("seed", [1, 2, 7, 42, 999, 123456])
def test_generate_valid_cpf_passes_validator(seed: int) -> None:
    cpf = _generate_valid_cpf(seed)
    assert len(cpf) == 11
    assert cpf.isdigit()
    validate_cpf(cpf)  # raises ValidationError if the check digits are wrong


def test_generate_valid_cpf_is_deterministic_and_unique_per_seed() -> None:
    assert _generate_valid_cpf(5) == _generate_valid_cpf(5)
    cpfs = {_generate_valid_cpf(n) for n in range(1, 200)}
    assert len(cpfs) == 199  # every seed maps to a distinct CPF


def test_cpf_valid_primary_passes_validator() -> None:
    validate_cpf(CPF_VALID_PRIMARY)


@pytest.mark.django_db
def test_make_tenant_cpfs_are_unique() -> None:
    cpfs = {make_tenant().cpf_cnpj for _ in range(10)}
    assert len(cpfs) == 10
