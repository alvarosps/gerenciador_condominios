"""P5.1: the bill list + overdue endpoints resolve line_items.category and account_type
without N+1.

Gold-standard N+1 assertion: the query count must be IDENTICAL for a small and a larger
set of bills. If line_items__category or installment__plan__billing_account were not
prefetched/select_related, each extra bill would add per-row queries and the counts would
diverge — independent of any unrelated query the endpoint may run.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from freezegun import freeze_time
from model_bakery import baker

from finances.models import BillingAccountType
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_condominium,
    make_installment,
    make_installment_plan,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"
BILLS_URL = "/api/finances/bills/"
OVERDUE_URL = "/api/finances/finance-dashboard/overdue/"


def _make_iptu_parcela_bill(condominium, *, index: int) -> None:
    """An overdue IPTU parcela bill: billing_account=None (reaches the type via
    installment→plan→billing_account) + a categorized line item."""
    account = make_billing_account(
        condominium=condominium,
        account_type=BillingAccountType.IPTU,
        external_identifier=f"iptu-{index}",
        name=f"IPTU {index}",
    )
    plan = make_installment_plan(condominium=condominium, billing_account=account, embedded=False)
    installment = make_installment(plan=plan, number=1, due_date=date(2026, 6, 10))
    category = baker.make("finances.Category", name=f"Cat {index}")
    bill = make_bill(
        condominium=condominium,
        installment=installment,
        due_date=date(2026, 6, 10),
        competence_month=date(2026, 6, 1),
        behavior="installment",
        description=f"IPTU parcela {index}",
    )
    make_bill_line_item(bill=bill, amount=Decimal("250.00"), category=category)


def _count_queries(client, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx)


@freeze_time(FROZEN)
def test_bill_list_no_n_plus_one(authenticated_api_client):
    condo = make_condominium()
    for i in range(2):
        _make_iptu_parcela_bill(condo, index=i)
    small = _count_queries(authenticated_api_client, BILLS_URL)

    for i in range(2, 6):
        _make_iptu_parcela_bill(condo, index=i)
    large = _count_queries(authenticated_api_client, BILLS_URL)

    assert small == large, (
        f"bill list scales with N: {small} -> {large} queries (N+1 on line_items/account_type)"
    )


@freeze_time(FROZEN)
def test_overdue_no_n_plus_one(authenticated_api_client):
    condo = make_condominium()
    for i in range(2):
        _make_iptu_parcela_bill(condo, index=i)
    small = _count_queries(authenticated_api_client, OVERDUE_URL)

    for i in range(2, 6):
        _make_iptu_parcela_bill(condo, index=i)
    large = _count_queries(authenticated_api_client, OVERDUE_URL)

    assert small == large, (
        f"overdue scales with N: {small} -> {large} queries (N+1 on line_items/account_type)"
    )
