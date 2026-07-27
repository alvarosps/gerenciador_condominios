"""Session 67 — GET billing-accounts/{id}/statement (uncached) + open_balance on list."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from tests.factories import make_bill, make_bill_line_item, make_billing_account

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"


def _statement_url(account_id: object) -> str:
    return f"/api/finances/billing-accounts/{account_id}/statement/"


@freeze_time(FROZEN)
def test_statement_returns_full_shape(authenticated_api_client):
    account = make_billing_account()
    bill = make_bill(condominium=account.condominium, billing_account=account)
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))

    resp = authenticated_api_client.get(_statement_url(account.id))

    assert resp.status_code == status.HTTP_200_OK
    assert set(resp.data.keys()) == {"account", "stats", "months", "plans"}
    assert set(resp.data["stats"].keys()) == {
        "open_balance",
        "open_bills_count",
        "avg_delay_days",
    }
    assert resp.data["account"]["id"] == account.id


@freeze_time(FROZEN)
def test_statement_404_for_unknown_or_deleted_account(authenticated_api_client):
    resp_unknown = authenticated_api_client.get(_statement_url(999999))
    assert resp_unknown.status_code == status.HTTP_404_NOT_FOUND

    account = make_billing_account()
    account.is_deleted = True
    account.save(update_fields=["is_deleted"])

    resp_deleted = authenticated_api_client.get(_statement_url(account.id))
    assert resp_deleted.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(FROZEN)
def test_statement_forbidden_for_non_admin(regular_authenticated_api_client):
    account = make_billing_account()

    resp = regular_authenticated_api_client.get(_statement_url(account.id))

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@freeze_time(FROZEN)
def test_statement_requires_authentication(api_client):
    account = make_billing_account()

    resp = api_client.get(_statement_url(account.id))

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@freeze_time(FROZEN)
def test_statement_uncached_reflects_payment(authenticated_api_client):
    account = make_billing_account()
    bill = make_bill(
        condominium=account.condominium,
        billing_account=account,
        competence_month=date(2026, 6, 1),
        due_date=date(2026, 6, 10),
    )
    make_bill_line_item(bill=bill, amount=Decimal("500.00"))

    first = authenticated_api_client.get(_statement_url(account.id))
    assert first.data["stats"]["open_balance"] == "500.00"

    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-05"}, format="json"
    )

    second = authenticated_api_client.get(_statement_url(account.id))
    assert second.data["stats"]["open_balance"] == "0.00"


@freeze_time(FROZEN)
def test_billing_accounts_list_includes_open_balance(authenticated_api_client):
    account = make_billing_account()
    bill = make_bill(condominium=account.condominium, billing_account=account)
    make_bill_line_item(bill=bill, amount=Decimal("77.00"))

    resp = authenticated_api_client.get("/api/finances/billing-accounts/")

    assert resp.status_code == status.HTTP_200_OK
    row = next(r for r in resp.data["results"] if r["id"] == account.id)
    assert row["open_balance"] == "77.00"
