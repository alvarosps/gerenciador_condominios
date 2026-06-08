"""Session 37 — finance-* cache invalidation (finances signals + cross-app NET-NEW).

Cache is LocMem in tests, so invalidate_pattern does cache.clear(): invalidation is
asserted by a probe key disappearing after the write. The finances/core prefix literals
are locked equal here (design §11 "one char of difference silently fails").
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from finances.cache import (
    FINANCE_CACHE_PREFIXES,
    FINANCE_CASH_FLOW_PREFIX,
    FINANCE_DASHBOARD_PREFIX,
    FINANCE_PROJECTION_PREFIX,
    invalidate_finance_caches,
)
from model_bakery import baker

from core.models import FinancialSettings
from core.signals import _FINANCE_CACHE_PREFIXES as CORE_PREFIXES
from tests.factories import (
    make_apartment,
    make_bill,
    make_bill_line_item,
    make_bill_skip,
    make_billing_account,
    make_finance_category,
    make_lease,
    make_payment,
    make_payment_allocation,
    make_person,
    make_rent_payment,
)

pytestmark = pytest.mark.django_db


def _set_finance_probes() -> None:
    for prefix in FINANCE_CACHE_PREFIXES:
        cache.set(f"{prefix}:probe", "x")


def _finance_probes_cleared() -> bool:
    return all(cache.get(f"{prefix}:probe") is None for prefix in FINANCE_CACHE_PREFIXES)


def test_prefix_literals_match_and_invalidate() -> None:
    assert FINANCE_DASHBOARD_PREFIX == "finance-dashboard"
    assert FINANCE_CASH_FLOW_PREFIX == "finance-cash-flow"
    assert FINANCE_PROJECTION_PREFIX == "finance-projection"
    # core/signals.py keeps a matching literal copy (no finances import) — locked here.
    assert set(CORE_PREFIXES) == set(FINANCE_CACHE_PREFIXES)
    _set_finance_probes()
    invalidate_finance_caches()
    assert _finance_probes_cleared()


def test_finances_model_saves_invalidate() -> None:
    cond = make_finance_category().condominium
    account = make_billing_account(condominium=cond)
    bill = make_bill(condominium=cond)
    line = make_bill_line_item(bill=bill)
    payment = make_payment(condominium=cond)
    allocation = make_payment_allocation(payment=payment, bill=bill)
    skip = make_bill_skip(billing_account=account)
    for obj in (account, bill, line, payment, allocation, skip):
        _set_finance_probes()
        obj.save()
        assert _finance_probes_cleared(), f"{type(obj).__name__}.save did not invalidate"


def test_bill_soft_delete_invalidates() -> None:
    bill = make_bill()
    _set_finance_probes()
    bill.delete()  # soft delete -> post_save
    assert _finance_probes_cleared()


def test_apartment_owner_change_invalidates() -> None:
    apt = make_apartment()
    person = make_person()
    _set_finance_probes()
    apt.owner = person
    apt.save()
    assert _finance_probes_cleared()


def test_apartment_delete_invalidates() -> None:
    apt = make_apartment()
    _set_finance_probes()
    apt.delete()
    assert _finance_probes_cleared()


def test_lease_save_and_delete_invalidate() -> None:
    lease = make_lease()
    _set_finance_probes()
    lease.save()
    assert _finance_probes_cleared()
    _set_finance_probes()
    lease.delete()
    assert _finance_probes_cleared()


def test_rent_adjustment_invalidates() -> None:
    adjustment = baker.make("core.RentAdjustment", lease=make_lease())
    _set_finance_probes()
    adjustment.save()
    assert _finance_probes_cleared()


def test_month_snapshot_invalidates() -> None:
    snapshot = baker.make("core.MonthSnapshot")
    _set_finance_probes()
    snapshot.save()
    assert _finance_probes_cleared()


def test_rent_payment_invalidates_finance_and_late_payment() -> None:
    rent_payment = make_rent_payment()
    cache.set("dashboard-late-payment:probe", "x")
    _set_finance_probes()
    rent_payment.save()
    assert _finance_probes_cleared()
    assert cache.get("dashboard-late-payment:probe") is None  # legacy flow intact


def test_financial_settings_invalidates_legacy_and_finance() -> None:
    settings_obj, _ = FinancialSettings.objects.get_or_create(
        pk=1, defaults={"initial_balance": Decimal(0), "initial_balance_date": date(2026, 3, 1)}
    )
    for legacy in ("daily-control", "cash-flow", "financial-dashboard"):
        cache.set(f"{legacy}:probe", "x")
    _set_finance_probes()
    settings_obj.save()
    assert _finance_probes_cleared()
    for legacy in ("daily-control", "cash-flow", "financial-dashboard"):
        assert cache.get(f"{legacy}:probe") is None  # legacy invalidation intact
