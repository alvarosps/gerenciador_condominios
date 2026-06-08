"""Session 57 — FieldError guard for the renamed select_related string literals (design §4).

These three query paths reference ``billing_account`` via string literals that no type-checker
validates; a stale field name would only blow up at runtime with a FieldError. Each test
EXECUTES one path with a real embedded plan so the rename is proven end to end (ORM/services/API
exercised, nothing mocked — tests/CLAUDE.md mock policy).
"""

from datetime import date
from decimal import Decimal

import pytest
from finances.models import Bill, BillingAccountType, BillLineItem
from finances.services.bill_generation_service import BillGenerationService
from finances.services.condo_projection_service import CondoProjectionService

from tests.factories import (
    make_billing_account,
    make_installment,
    make_installment_plan,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

PLANS_URL = "/api/finances/installment-plans/"


def _embedded_plan_on_water_account():
    account = make_billing_account(
        account_type=BillingAccountType.WATER,
        external_identifier="UC-57",
        expected_amount=Decimal("600.00"),
        default_due_day=10,
    )
    plan = make_installment_plan(
        condominium=account.condominium,
        embedded=True,
        billing_account=account,
        installment_count=1,
    )
    make_installment(plan=plan, number=1, due_date=date(2026, 7, 10), amount=Decimal("400.00"))
    return account, plan


def test_condo_projection_service_executes_embedded_select_related() -> None:
    """CondoProjectionService._projected_expenses executa select_related('plan__billing_account')
    com um plano embutido real → sem FieldError; total reflete a parcela embutida."""
    account, _plan = _embedded_plan_on_water_account()
    total = CondoProjectionService._projected_expenses(2026, 7)
    # 600 consumo (expected_amount) + 400 parcela embutida, sem FieldError.
    assert total == Decimal("1000.00")
    assert account.account_type == BillingAccountType.WATER


def test_bill_generation_service_executes_embedded_select_related() -> None:
    """BillGenerationService.ensure_month_bills (ramo embutido) executa
    select_related('plan__billing_account') materializando a parcela no Bill da conta → sem FieldError."""
    account, _plan = _embedded_plan_on_water_account()
    BillGenerationService.ensure_month_bills(2026, 7)
    bill = Bill.all_objects.get(billing_account=account, competence_month=date(2026, 7, 1))
    # consumo 600 + parcela embutida 400 = 2 linhas.
    assert BillLineItem.objects.filter(bill=bill).count() == 2
    annotated = Bill.objects.with_amounts(date(2026, 8, 1)).get(pk=bill.pk)
    assert annotated.amount_total == Decimal("1000.00")


def test_installment_plan_viewset_executes_select_related(authenticated_api_client) -> None:
    """GET /api/finances/installment-plans/ executa o queryset com select_related('billing_account')
    → 200, sem FieldError; o item traz billing_account nested."""
    account, plan = _embedded_plan_on_water_account()
    response = authenticated_api_client.get(PLANS_URL)
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.data["results"]}
    assert plan.id in rows
    assert rows[plan.id]["billing_account"]["id"] == account.id
