"""Session 61 — GET /api/finances/finance-dashboard/iptu_alerts (UNCACHED, design §9/§11).

Exercises the real path View -> IptuAlertService -> Model against the test DB (no
internal mocking). Asserts the non-paginated shape {alerts, warning_count, critical_count},
that it reflects payment without stale cache (uncached), and the IsAdminUser access
policy (admin-only after P1.2). Only freezegun (today) and DRF throttling (infra) are neutralized.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import override_settings
from finances.models import BillingAccountType, InstallmentPlanState
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APIClient

from tests.constants import TEST_PASSWORD
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_building,
    make_installment,
    make_installment_plan,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"
IPTU_ALERTS_URL = "/api/finances/finance-dashboard/iptu_alerts/"

# DRF binds SimpleRateThrottle.timer = time.time as a class attribute, so under freezegun
# it is called as a bound method and raises. Throttling is infra, not application logic.
_REST_FRAMEWORK_NO_THROTTLE = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}


@pytest.fixture(autouse=True)
def _disable_throttling():
    with override_settings(REST_FRAMEWORK=_REST_FRAMEWORK_NO_THROTTLE):
        yield


def _iptu_plan(external_identifier: str = "516481", *, building=None, condominium=None):
    account = make_billing_account(
        condominium=condominium,
        building=building,
        account_type=BillingAccountType.IPTU,
        external_identifier=external_identifier,
        name=f"IPTU {external_identifier}",
    )
    return make_installment_plan(
        condominium=account.condominium,
        building=account.building,
        billing_account=account,
        embedded=False,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        installment_count=10,
    )


def _parcela_bill(plan, *, number: int, due_date: date, amount: str = "100.00"):
    installment = make_installment(
        plan=plan, number=number, due_date=due_date, amount=Decimal(amount)
    )
    bill = make_bill(
        condominium=plan.condominium,
        building=plan.building,
        installment=installment,
        due_date=due_date,
        competence_month=due_date.replace(day=1),
        description=f"IPTU parcela {number}",
        behavior="installment",
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


@freeze_time(FROZEN)
def test_iptu_alerts_returns_alerts_shape(authenticated_api_client) -> None:
    """GET iptu_alerts → 200 {alerts:[...], warning_count, critical_count}; NÃO {results, count}."""
    plan = _iptu_plan()
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    resp = authenticated_api_client.get(IPTU_ALERTS_URL)

    assert resp.status_code == status.HTTP_200_OK
    assert set(resp.data.keys()) == {"alerts", "warning_count", "critical_count"}
    assert "results" not in resp.data
    assert "count" not in resp.data
    assert resp.data["warning_count"] == 1
    assert resp.data["critical_count"] == 0
    assert len(resp.data["alerts"]) == 1


@freeze_time(FROZEN)
def test_iptu_alerts_warning_row_fields(authenticated_api_client) -> None:
    """Linha WARNING tem todos os campos; deadline em ISO (date|null)."""
    building = make_building(street_number=321)
    plan = _iptu_plan("516503", building=building, condominium=building.condominium)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))  # overdue
    _parcela_bill(plan, number=2, due_date=date(2026, 7, 20))  # deadline

    resp = authenticated_api_client.get(IPTU_ALERTS_URL)

    # Assert on the rendered JSON (what the client sees): DRF serializes date -> ISO string.
    alert = resp.json()["alerts"][0]
    assert set(alert.keys()) == {
        "plan_id",
        "external_identifier",
        "building_label",
        "level",
        "overdue_count",
        "deadline",
        "overdue_due_dates",
        "message",
    }
    assert alert["plan_id"] == plan.pk
    assert alert["external_identifier"] == "516503"
    assert alert["building_label"] == "321"
    assert alert["level"] == "warning"
    assert alert["overdue_count"] == 1
    assert alert["deadline"] == "2026-07-20"
    assert alert["overdue_due_dates"] == ["2026-06-10"]
    assert "516503" in alert["message"]


@freeze_time(FROZEN)
def test_iptu_alerts_reflects_payment_without_stale_cache(authenticated_api_client) -> None:
    """Pagar a parcela vencida e re-GET → o alerta some (uncached, sem stale)."""
    plan = _iptu_plan("516449")
    bill = _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))

    # Assert on THIS plan's alert (delta), not the condo-wide count — the endpoint is condo-wide
    # and the reused test DB may carry unrelated IPTU rows; what we prove here is the uncached
    # behavior: paying the parcela removes the alert immediately, with no stale cache.
    first = authenticated_api_client.get(IPTU_ALERTS_URL)
    assert any(a["plan_id"] == plan.pk for a in first.data["alerts"])

    authenticated_api_client.post(
        f"/api/finances/bills/{bill.id}/pay/", {"payment_date": "2026-06-12"}, format="json"
    )

    second = authenticated_api_client.get(IPTU_ALERTS_URL)
    assert all(a["plan_id"] != plan.pk for a in second.data["alerts"])


@freeze_time(FROZEN)
def test_iptu_alerts_requires_authentication(api_client) -> None:
    """Sem auth → 401."""
    resp = api_client.get(IPTU_ALERTS_URL)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@freeze_time(FROZEN)
def test_iptu_alerts_blocked_for_authenticated_non_staff() -> None:
    """Usuário autenticado não-staff → 403 (financeiro é admin-only após P1.2)."""
    non_staff = User.objects.create_user(
        username="reader", email="reader@test.com", password=TEST_PASSWORD, is_staff=False
    )
    client = APIClient()
    client.force_authenticate(user=non_staff)

    resp = client.get(IPTU_ALERTS_URL)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
