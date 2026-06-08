"""Session 47 — finance-cash-flow/{projection,simulate}: shape, validation, cache, permissions."""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import BillingAccount
from freezegun import freeze_time
from rest_framework import status

from tests.factories import make_billing_account, make_lease

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PROJECTION_URL = "/api/finances/finance-cash-flow/projection/"
SIMULATE_URL = "/api/finances/finance-cash-flow/simulate/"


@freeze_time("2026-07-15 12:00:00")
def test_projection_shape(authenticated_api_client):
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_billing_account(expected_amount=Decimal("400.00"))
    resp = authenticated_api_client.get(f"{PROJECTION_URL}?months=12")
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 12
    first = resp.data[0]
    for key in (
        "year",
        "month",
        "income_total",
        "expenses_total",
        "net",
        "cumulative_cash",
        "is_actual",
        "is_closed",
    ):
        assert key in first
    for key in ("income_total", "expenses_total", "net", "cumulative_cash"):
        assert isinstance(first[key], str)
    august = resp.data[1]
    assert august["expenses_total"] == "400.00"  # projected recurring outflow
    assert august["income_total"] == "1000.00"


@freeze_time("2026-07-15 12:00:00")
def test_projection_invalid_params(authenticated_api_client):
    assert (
        authenticated_api_client.get(f"{PROJECTION_URL}?months=abc").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{PROJECTION_URL}?months=0").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{PROJECTION_URL}?months=-3").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{PROJECTION_URL}?months=99").status_code
        == status.HTTP_400_BAD_REQUEST
    )
    assert (
        authenticated_api_client.get(f"{PROJECTION_URL}?building_id=abc").status_code
        == status.HTTP_400_BAD_REQUEST
    )


@freeze_time("2026-07-15 12:00:00")
def test_simulate_returns_base_simulated_comparison(authenticated_api_client):
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_billing_account(expected_amount=Decimal("400.00"))
    resp = authenticated_api_client.post(
        SIMULATE_URL,
        {"scenarios": [{"type": "add_expense", "amount": "100.00"}], "months": 3},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert set(resp.data.keys()) == {"base", "simulated", "comparison"}
    base = resp.data["base"]
    simulated = resp.data["simulated"]
    # Real months (is_actual) are identical between base and simulated.
    for base_row, sim_row in zip(base, simulated, strict=True):
        if base_row["is_actual"]:
            assert base_row == sim_row
    # The future expense delta is applied.
    future_index = next(i for i, row in enumerate(base) if not row["is_actual"])
    assert Decimal(simulated[future_index]["expenses_total"]) == Decimal(
        base[future_index]["expenses_total"]
    ) + Decimal("100.00")


@freeze_time("2026-07-15 12:00:00")
def test_simulate_invalid_scenarios(authenticated_api_client):
    empty = authenticated_api_client.post(SIMULATE_URL, {"scenarios": []}, format="json")
    assert empty.status_code == status.HTTP_400_BAD_REQUEST
    missing = authenticated_api_client.post(SIMULATE_URL, {}, format="json")
    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    bad_type = authenticated_api_client.post(
        SIMULATE_URL, {"scenarios": [{"type": "nope", "amount": "1"}]}, format="json"
    )
    assert bad_type.status_code == status.HTTP_400_BAD_REQUEST
    assert "errors" in bad_type.data


@freeze_time("2026-07-15 12:00:00")
def test_simulate_rejects_non_finite_and_non_dict_scenarios(authenticated_api_client):
    # Non-finite amounts must 400 (not silently corrupt with "NaN", not 500 on Infinity/sNaN).
    for amount in ("NaN", "Infinity", "-Infinity", "sNaN"):
        resp = authenticated_api_client.post(
            SIMULATE_URL, {"scenarios": [{"type": "add_income", "amount": amount}]}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, amount
    # A non-dict scenario element must 400 (not AttributeError → 500).
    non_dict = authenticated_api_client.post(SIMULATE_URL, {"scenarios": ["nope"]}, format="json")
    assert non_dict.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time("2026-07-15 12:00:00")
def test_projection_cached_and_invalidated(authenticated_api_client):
    account = make_billing_account(expected_amount=Decimal("100.00"))
    url = f"{PROJECTION_URL}?months=2"
    first = authenticated_api_client.get(url)
    assert first.data[1]["expenses_total"] == "100.00"  # now cached
    # bulk update bypasses signals → cache NOT invalidated → stale value still served
    BillingAccount.objects.filter(pk=account.pk).update(expected_amount=Decimal("500.00"))
    cached = authenticated_api_client.get(url)
    assert cached.data[1]["expenses_total"] == "100.00"
    # a normal save fires the finance-* signal → cache invalidated → fresh value
    account.refresh_from_db()
    account.save()
    fresh = authenticated_api_client.get(url)
    assert fresh.data[1]["expenses_total"] == "500.00"


@freeze_time("2026-07-15 12:00:00")
def test_simulate_is_never_cached(authenticated_api_client):
    account = make_billing_account(expected_amount=Decimal("100.00"))
    body = {"scenarios": [{"type": "add_income", "amount": "1.00"}], "months": 2}
    first = authenticated_api_client.post(SIMULATE_URL, body, format="json")
    assert first.data["base"][1]["expenses_total"] == "100.00"
    # bulk update bypasses signals; simulate is uncached, so the 2nd POST recomputes fresh anyway
    BillingAccount.objects.filter(pk=account.pk).update(expected_amount=Decimal("700.00"))
    second = authenticated_api_client.post(SIMULATE_URL, body, format="json")
    assert second.data["base"][1]["expenses_total"] == "700.00"


@freeze_time("2026-07-15 12:00:00")
def test_projection_readable_by_non_admin(regular_authenticated_api_client):
    resp = regular_authenticated_api_client.get(f"{PROJECTION_URL}?months=3")
    assert resp.status_code == status.HTTP_200_OK


@freeze_time("2026-07-15 12:00:00")
def test_simulate_blocked_for_non_admin(regular_authenticated_api_client):
    resp = regular_authenticated_api_client.post(
        SIMULATE_URL, {"scenarios": [{"type": "add_expense", "amount": "1"}]}, format="json"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@freeze_time("2026-07-15 12:00:00")
def test_simulate_allowed_for_admin(authenticated_api_client):
    resp = authenticated_api_client.post(
        SIMULATE_URL, {"scenarios": [{"type": "add_expense", "amount": "1"}]}, format="json"
    )
    assert resp.status_code != status.HTTP_403_FORBIDDEN


def test_projection_requires_authentication(api_client):
    resp = api_client.get(f"{PROJECTION_URL}?months=3")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
