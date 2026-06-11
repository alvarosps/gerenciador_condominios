"""Session 45 — reserve / reserve-movement / income-entry API + deposit/withdraw + permissions."""

from datetime import date
from decimal import Decimal

import pytest
from finances.services.condo_balance_service import CondoBalanceService
from freezegun import freeze_time
from rest_framework import status

from core.models import Condominium, FinancialSettings
from tests.factories import (
    make_condominium,
    make_reserve,
    make_reserve_movement,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_reserve_crud_dual_and_balance(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/reserves/",
        {"condominium_id": cond.id, "name": "Poupança"},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["condominium"] == {"id": cond.id, "name": cond.name}
    assert resp.data["balance"] == "0.00"
    assert "condominium_id" not in resp.data
    listing = authenticated_api_client.get("/api/finances/reserves/")
    assert listing.status_code == status.HTTP_200_OK
    assert "results" in listing.data


@freeze_time("2026-07-15")
def test_reserve_deposit_keeps_total_balance(authenticated_api_client):
    FinancialSettings.objects.create(
        pk=1, initial_balance=Decimal("1000.00"), initial_balance_date=date(2026, 6, 1)
    )
    reserve = make_reserve()
    as_of = date(2026, 7, 1)
    before = CondoBalanceService.total_balance(as_of)
    resp = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/deposit/",
        {"amount": "500.00", "movement_date": "2026-06-10"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["balance"] == "500.00"
    assert CondoBalanceService.total_balance(as_of) == before  # cash -500, reserve +500


@freeze_time("2026-07-15")
def test_reserve_withdraw_guard(authenticated_api_client):
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("100.00"), movement_date=date(2026, 6, 1)
    )
    over = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/withdraw/",
        {"amount": "150.00", "movement_date": "2026-06-12"},
        format="json",
    )
    assert over.status_code == status.HTTP_400_BAD_REQUEST
    assert "reserva" in over.data["error"].lower()
    non_positive = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/withdraw/",
        {"amount": "0", "movement_date": "2026-06-12"},
        format="json",
    )
    assert non_positive.status_code == status.HTTP_400_BAD_REQUEST
    ok = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/withdraw/",
        {"amount": "80.00", "movement_date": "2026-06-12"},
        format="json",
    )
    assert ok.status_code == status.HTTP_200_OK
    assert ok.data["balance"] == "20.00"


def test_reserve_create_defaults_singleton_condominium(authenticated_api_client):
    """POST without condominium_id falls back to the singleton (design §15 — no UI selector)."""
    default = Condominium.get_default()
    assert default is not None
    resp = authenticated_api_client.post(
        "/api/finances/reserves/", {"name": "Reserva"}, format="json"
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["condominium"] == {"id": default.id, "name": default.name}


def test_income_entry_defaults_singleton_condominium(authenticated_api_client):
    """POST without condominium_id falls back to the singleton (design §15)."""
    default = Condominium.get_default()
    assert default is not None
    resp = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "description": "Doação",
            "amount": "100.00",
            "income_date": "2026-06-20",
            "is_received": False,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["condominium"] == {"id": default.id, "name": default.name}


def test_income_entry_update_keeps_condominium(authenticated_api_client):
    """Updating without condominium_id keeps the existing condominium (no default injection)."""
    cond = make_condominium()
    created = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "condominium_id": cond.id,
            "description": "Original",
            "amount": "10.00",
            "income_date": "2026-06-20",
            "is_received": False,
        },
        format="json",
    )
    income_id = created.data["id"]
    resp = authenticated_api_client.patch(
        f"/api/finances/income-entries/{income_id}/",
        {"description": "Editado"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["description"] == "Editado"
    assert resp.data["condominium"]["id"] == cond.id


def test_reserve_create_errors_when_no_condominium(authenticated_api_client):
    """With no condominium configured at all, the create surfaces a PT validation error."""
    Condominium.all_objects.all().delete()
    resp = authenticated_api_client.post(
        "/api/finances/reserves/", {"name": "Reserva"}, format="json"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "condomínio" in str(resp.data).lower()


def test_reserve_deposit_requires_amount(authenticated_api_client):
    reserve = make_reserve()
    resp = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/deposit/", {}, format="json"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_reserve_movement_list_and_filters(authenticated_api_client):
    reserve = make_reserve()
    make_reserve_movement(
        reserve=reserve, kind="deposit", amount=Decimal("10.00"), movement_date=date(2026, 6, 1)
    )
    make_reserve_movement(
        reserve=reserve,
        kind="withdrawal",
        amount=Decimal("5.00"),
        movement_date=date(2026, 6, 5),
        bill=None,
    )
    resp = authenticated_api_client.get(
        f"/api/finances/reserve-movements/?reserve_id={reserve.id}&kind=deposit"
    )
    assert resp.status_code == status.HTTP_200_OK
    assert all(m["kind"] == "deposit" for m in resp.data["results"])
    assert resp.data["results"][0]["bill"] is None


def test_income_entry_crud_and_filters(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "condominium_id": cond.id,
            "description": "Provento",
            "amount": "750.00",
            "income_date": "2026-06-20",
            "is_received": True,
            "received_date": "2026-06-21",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["amount"] == "750.00"
    assert resp.data["income_date"] == "2026-06-20"
    received = authenticated_api_client.get("/api/finances/income-entries/?is_received=true")
    assert received.status_code == status.HTTP_200_OK
    assert all(e["is_received"] for e in received.data["results"])


def test_income_entry_received_date_validation(authenticated_api_client):
    cond = make_condominium()
    resp = authenticated_api_client.post(
        "/api/finances/income-entries/",
        {
            "condominium_id": cond.id,
            "description": "Sem data",
            "amount": "10.00",
            "income_date": "2026-06-20",
            "is_received": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- IsAdminUser matrix (admin-only after P1.2) ---

_READ_ENDPOINTS = [
    "/api/finances/reserves/",
    "/api/finances/reserve-movements/",
    "/api/finances/income-entries/",
    "/api/finances/condo-month-closes/",
]


def test_non_admin_cannot_read(regular_authenticated_api_client):
    for url in _READ_ENDPOINTS:
        assert regular_authenticated_api_client.get(url).status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_read(authenticated_api_client):
    for url in _READ_ENDPOINTS:
        assert authenticated_api_client.get(url).status_code == status.HTTP_200_OK


def test_non_admin_cannot_write(regular_authenticated_api_client):
    reserve = make_reserve()
    cond_id = reserve.condominium_id
    forbidden = [
        ("/api/finances/reserves/", {"condominium_id": cond_id, "name": "X"}),
        (f"/api/finances/reserves/{reserve.id}/deposit/", {"amount": "1"}),
        (f"/api/finances/reserves/{reserve.id}/withdraw/", {"amount": "1"}),
        (
            "/api/finances/income-entries/",
            {
                "condominium_id": cond_id,
                "description": "x",
                "amount": "1",
                "income_date": "2026-06-01",
            },
        ),
        ("/api/finances/condo-month-closes/close/", {"year": 2026, "month": 6}),
        ("/api/finances/condo-month-closes/reopen/", {"year": 2026, "month": 6}),
    ]
    for url, payload in forbidden:
        resp = regular_authenticated_api_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN, url


def test_admin_passes_the_permission_gate(authenticated_api_client):
    reserve = make_reserve()
    # deposit as admin is allowed (not a 403); it succeeds here.
    resp = authenticated_api_client.post(
        f"/api/finances/reserves/{reserve.id}/deposit/", {"amount": "5"}, format="json"
    )
    assert resp.status_code != status.HTTP_403_FORBIDDEN


def test_unauthenticated_is_401(api_client):
    for url in _READ_ENDPOINTS:
        assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED
