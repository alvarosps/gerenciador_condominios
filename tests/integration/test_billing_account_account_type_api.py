"""Session 56 — BillingAccount account_type + identity API tests.

The serializer exposes/accepts the 5 new fields; validate() mirrors the model rule
(rejecting a blank external_identifier for water/electricity/IPTU, in PT, on create and
update); the viewset filters ?account_type=. Real DRF stack, real DB.
"""

import pytest
from finances.models import BillingAccountType

from tests.factories import make_billing_account, make_building, make_condominium

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

ACCOUNTS_URL = "/api/finances/billing-accounts/"


def test_serializer_exposes_new_fields(authenticated_api_client) -> None:
    account = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier="UC-EXPOSE",
        holder_name="Titular",
        registered_address="Rua X, 1",
        secondary_identifier="MED-1",
    )
    response = authenticated_api_client.get(f"{ACCOUNTS_URL}{account.id}/")
    assert response.status_code == 200
    for field in (
        "account_type",
        "holder_name",
        "registered_address",
        "secondary_identifier",
        "supply_status",
    ):
        assert field in response.data
    assert response.data["account_type"] == "water"
    assert response.data["holder_name"] == "Titular"
    assert response.data["supply_status"] == "active"


def test_create_with_account_type_and_identity(authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "name": "Água 836",
        "account_type": "water",
        "external_identifier": "650.847.010-16",
        "holder_name": "Maria",
        "default_due_day": 10,
        "expected_amount": "120.00",
    }
    response = authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["account_type"] == "water"
    assert response.data["external_identifier"] == "650.847.010-16"
    assert response.data["holder_name"] == "Maria"


def test_create_blank_identifier_for_typed_account_rejected(authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "name": "IPTU sem inscrição",
        "account_type": "iptu",
        "external_identifier": "",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 400
    assert "external_identifier" in response.data
    assert "Informe a inscrição/UC" in str(response.data["external_identifier"][0])


def test_update_to_typed_without_identifier_rejected(authenticated_api_client) -> None:
    account = make_billing_account(account_type=BillingAccountType.GENERIC, external_identifier="")
    response = authenticated_api_client.patch(
        f"{ACCOUNTS_URL}{account.id}/", {"account_type": "electricity"}, format="json"
    )
    assert response.status_code == 400
    assert "external_identifier" in response.data


def test_update_clearing_identifier_on_typed_account_rejected(authenticated_api_client) -> None:
    """PATCH that omits account_type but blanks external_identifier: validate() resolves the
    type from the existing (WATER) instance and rejects the blank identifier."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-KEEP"
    )
    response = authenticated_api_client.patch(
        f"{ACCOUNTS_URL}{account.id}/", {"external_identifier": ""}, format="json"
    )
    assert response.status_code == 400
    assert "external_identifier" in response.data


def test_create_generic_blank_identifier_ok(authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "name": "Conta genérica",
        "account_type": "generic",
        "external_identifier": "",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["account_type"] == "generic"


def test_create_duplicate_active_identity_returns_400_not_500(authenticated_api_client) -> None:
    """A duplicate active (building, account_type, external_identifier) is caught by the serializer
    (app-level guard mirroring the partial DB unique) → clean PT 400, never an IntegrityError 500."""
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-DUP",
    )
    payload = {
        "condominium_id": condo.id,
        "building_id": building.id,
        "name": "Água duplicada",
        "account_type": "water",
        "external_identifier": "UC-DUP",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 400
    assert "external_identifier" in response.data
    assert "Já existe uma conta ativa" in str(response.data["external_identifier"][0])


def test_create_duplicate_identity_after_soft_delete_allowed(authenticated_api_client) -> None:
    """A soft-deleted account frees the partial-unique slot — recreating the same identity is OK
    (the guard uses the default manager, which excludes soft-deleted rows)."""
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    first = make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="UC-REVIVE",
    )
    first.delete()  # soft delete
    payload = {
        "condominium_id": condo.id,
        "building_id": building.id,
        "name": "Água recriada",
        "account_type": "water",
        "external_identifier": "UC-REVIVE",
        "default_due_day": 10,
    }
    response = authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 201
    assert response.data["external_identifier"] == "UC-REVIVE"


def test_update_keeping_own_identity_allowed(authenticated_api_client) -> None:
    """A PATCH editing other fields must not flag the row's own identity as a duplicate (self is
    excluded from the uniqueness guard)."""
    account = make_billing_account(
        account_type=BillingAccountType.WATER, external_identifier="UC-SELF"
    )
    response = authenticated_api_client.patch(
        f"{ACCOUNTS_URL}{account.id}/", {"name": "Novo nome"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["name"] == "Novo nome"


def test_filter_by_account_type(authenticated_api_client) -> None:
    # Scope to a dedicated building so the assertion is deterministic regardless of any other
    # accounts (and exercises building_id + account_type together).
    condo = make_condominium()
    building = make_building(street_number=836, condominium=condo)
    iptu = make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.IPTU,
        external_identifier="IPTU-FILTER",
    )
    water = make_billing_account(
        condominium=condo,
        building=building,
        account_type=BillingAccountType.WATER,
        external_identifier="WATER-FILTER",
    )

    iptu_resp = authenticated_api_client.get(
        ACCOUNTS_URL, {"account_type": "iptu", "building_id": building.id}
    )
    assert iptu_resp.status_code == 200
    iptu_ids = {row["id"] for row in iptu_resp.data["results"]}
    assert iptu_ids == {iptu.id}

    water_resp = authenticated_api_client.get(
        ACCOUNTS_URL, {"account_type": "water", "building_id": building.id}
    )
    water_ids = {row["id"] for row in water_resp.data["results"]}
    assert water_ids == {water.id}


def test_non_admin_cannot_write_account_type(regular_authenticated_api_client) -> None:
    condo = make_condominium()
    payload = {
        "condominium_id": condo.id,
        "name": "Negado",
        "account_type": "water",
        "external_identifier": "UC-DENY",
        "default_due_day": 10,
    }
    response = regular_authenticated_api_client.post(ACCOUNTS_URL, payload, format="json")
    assert response.status_code == 403
