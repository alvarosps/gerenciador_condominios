"""Session 47 — CondoSimulationService tests (Phase 5 backend).

100% ephemeral what-if: deepcopy of the base projection, deltas applied ONLY to future
(is_actual=False) months, net + cumulative_cash re-folded from the point of change, zero
persistence, base never mutated. Money stays a quantized string at every boundary.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone
from freezegun import freeze_time

from finances.models import Bill
from finances.services.condo_projection_service import CondoProjectionService
from finances.services.condo_simulation_service import CondoSimulationService
from tests.factories import make_billing_account, make_condo_month_close, make_lease

pytestmark = pytest.mark.django_db


def _base() -> list[dict[str, Any]]:
    """A 3-month base: July is real (is_actual), Aug/Sep are projected. Baseline cash = 0."""
    return [
        {
            "year": 2026,
            "month": 7,
            "income_total": "1000.00",
            "expenses_total": "400.00",
            "net": "600.00",
            "cumulative_cash": "600.00",
            "is_actual": True,
            "is_closed": False,
        },
        {
            "year": 2026,
            "month": 8,
            "income_total": "1000.00",
            "expenses_total": "400.00",
            "net": "600.00",
            "cumulative_cash": "1200.00",
            "is_actual": False,
            "is_closed": False,
        },
        {
            "year": 2026,
            "month": 9,
            "income_total": "1000.00",
            "expenses_total": "400.00",
            "net": "600.00",
            "cumulative_cash": "1800.00",
            "is_actual": False,
            "is_closed": False,
        },
    ]


# --------------------------------------------------------------------------- validation


def test_validate_scenarios_missing_type() -> None:
    errors = CondoSimulationService.validate_scenarios([{"amount": "100.00"}])
    assert len(errors) == 1
    assert "type" in errors[0]


def test_validate_scenarios_invalid_type() -> None:
    errors = CondoSimulationService.validate_scenarios([{"type": "pay_off_early", "amount": "100"}])
    assert len(errors) == 1
    assert "pay_off_early" in errors[0]


def test_validate_scenarios_missing_amount() -> None:
    errors = CondoSimulationService.validate_scenarios([{"type": "add_expense"}])
    assert len(errors) == 1
    assert "amount" in errors[0]


def test_validate_scenarios_change_rent_missing_delta() -> None:
    errors = CondoSimulationService.validate_scenarios([{"type": "change_rent", "amount": "10"}])
    assert len(errors) == 1
    assert "delta" in errors[0]


def test_validate_scenarios_non_decimal_amount() -> None:
    errors = CondoSimulationService.validate_scenarios([{"type": "add_income", "amount": "abc"}])
    assert len(errors) == 1


def test_validate_scenarios_all_valid() -> None:
    scenarios = [
        {"type": "add_expense", "amount": "100.00"},
        {"type": "change_rent", "delta": "-50.00"},
        {"type": "add_income", "amount": "200"},
        {"type": "remove_expense", "amount": "30"},
    ]
    assert CondoSimulationService.validate_scenarios(scenarios) == []


def test_validate_scenarios_rejects_non_finite_amount() -> None:
    for bad in ("NaN", "Infinity", "-Infinity", "sNaN"):
        errors = CondoSimulationService.validate_scenarios([{"type": "add_expense", "amount": bad}])
        assert len(errors) == 1, bad


def test_validate_scenarios_rejects_finite_but_out_of_range_amount() -> None:
    # finite yet huge: passes is_finite() but quantizing it later would raise InvalidOperation (500),
    # so it must be rejected at validation (400) — both the string and the bare-float forms.
    for bad in ("1e1000", "1e30", 1e30, "10000000000"):
        errors = CondoSimulationService.validate_scenarios([{"type": "add_expense", "amount": bad}])
        assert len(errors) == 1, bad
    # a normal large condo value is still accepted
    assert (
        CondoSimulationService.validate_scenarios([{"type": "add_expense", "amount": "5000.00"}])
        == []
    )


def test_validate_scenarios_rejects_non_dict_element() -> None:
    scenarios: list[Any] = ["nope", 123, None]
    assert len(CondoSimulationService.validate_scenarios(scenarios)) == 3


def test_validate_scenarios_rejects_invalid_months() -> None:
    for bad_months in (True, -1, "2", 2.5):
        errors = CondoSimulationService.validate_scenarios(
            [{"type": "add_expense", "amount": "10", "months": bad_months}]
        )
        assert len(errors) == 1, bad_months
    assert (
        CondoSimulationService.validate_scenarios(
            [{"type": "add_expense", "amount": "10", "months": 2}]
        )
        == []
    )


def test_simulate_drops_non_finite_scenario_without_corruption() -> None:
    # Defensive: even if a NaN slips past validation, _apply no-ops it (never emits "NaN").
    base = _base()
    simulated = CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "NaN"}])
    for row in simulated:
        for key in ("income_total", "expenses_total", "net", "cumulative_cash"):
            assert "NaN" not in row[key]
    assert simulated == base  # no-op scenario leaves the projection unchanged


# --------------------------------------------------------------------------- simulate


def test_simulate_does_not_mutate_base_or_touch_db() -> None:
    base = _base()
    snapshot = [dict(row) for row in base]
    before = Bill.objects.count()
    CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "100.00"}])
    assert base == snapshot  # base untouched (deepcopy)
    assert Bill.objects.count() == before  # zero persistence


def test_simulate_add_expense_only_future() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "100.00"}])
    # Real month (July) is identical to base.
    assert simulated[0] == base[0]
    # Future months: expense +100, net -100, cumulative re-folded.
    assert simulated[1]["expenses_total"] == "500.00"
    assert simulated[1]["net"] == "500.00"
    assert simulated[1]["cumulative_cash"] == "1100.00"  # 600 (July end) + 500
    assert simulated[2]["expenses_total"] == "500.00"
    assert simulated[2]["net"] == "500.00"
    assert simulated[2]["cumulative_cash"] == "1600.00"  # 1100 + 500


def test_simulate_change_rent_adds_to_income() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(base, [{"type": "change_rent", "delta": "-200.00"}])
    assert simulated[0] == base[0]  # current month unchanged
    assert simulated[1]["income_total"] == "800.00"
    assert simulated[1]["net"] == "400.00"
    assert simulated[1]["cumulative_cash"] == "1000.00"  # 600 + 400


def test_simulate_add_income_and_remove_expense() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(
        base,
        [{"type": "add_income", "amount": "100.00"}, {"type": "remove_expense", "amount": "50.00"}],
    )
    assert simulated[1]["income_total"] == "1100.00"
    assert simulated[1]["expenses_total"] == "350.00"
    assert simulated[1]["net"] == "750.00"


def test_simulate_remove_expense_floors_at_zero() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(
        base, [{"type": "remove_expense", "amount": "999.00"}]
    )
    assert simulated[1]["expenses_total"] == "0.00"  # never negative
    assert simulated[1]["net"] == "1000.00"


def test_simulate_months_window_limits_application() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(
        base, [{"type": "add_expense", "amount": "100.00", "months": 1}]
    )
    assert simulated[1]["expenses_total"] == "500.00"  # first future month only
    assert simulated[2]["expenses_total"] == "400.00"  # second future month untouched


def test_simulate_multiple_scenarios_compose() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(
        base,
        [{"type": "change_rent", "delta": "200.00"}, {"type": "add_expense", "amount": "100.00"}],
    )
    assert simulated[1]["income_total"] == "1200.00"
    assert simulated[1]["expenses_total"] == "500.00"
    assert simulated[1]["net"] == "700.00"


def test_simulate_empty_base_returns_empty() -> None:
    assert CondoSimulationService.simulate([], [{"type": "add_expense", "amount": "10"}]) == []


def test_compare_empty_base_is_zeroed() -> None:
    comparison = CondoSimulationService.compare([], [])
    assert comparison["months"] == []
    assert comparison["final_cumulative_delta"] == "0.00"
    assert comparison["total_net_delta"] == "0.00"


@freeze_time("2026-07-15 12:00:00")
def test_simulate_end_to_end_with_real_projection() -> None:
    make_lease(rental_value=Decimal("1000.00"), start_date=date(2026, 1, 1))
    make_billing_account(expected_amount=Decimal("400.00"))
    base = CondoProjectionService.project(months=3)
    simulated = CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "100.00"}])
    assert base[0]["is_actual"] is True
    assert simulated[0] == base[0]  # current month frozen against simulation
    assert Decimal(simulated[1]["expenses_total"]) == Decimal(base[1]["expenses_total"]) + Decimal(
        "100.00"
    )


@freeze_time("2026-07-15 12:00:00")
def test_simulate_reanchors_on_closed_future_month() -> None:
    # August (a FUTURE month) is closed → is_actual=True; the re-fold must re-anchor onto its
    # frozen cash and leave it byte-identical, while September folds onto that frozen end.
    make_condo_month_close(
        reference_month=date(2026, 8, 1),
        status="closed",
        closed_at=timezone.now(),
        net_result=Decimal("100.00"),
        cash_balance_end=Decimal("5000.00"),
    )
    base = CondoProjectionService.project(months=3)
    august = next(row for row in base if row["month"] == 8)
    assert august["is_actual"] is True
    assert august["is_closed"] is True

    simulated = CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "200.00"}])
    sim_august = next(row for row in simulated if row["month"] == 8)
    sim_september = next(row for row in simulated if row["month"] == 9)
    base_september = next(row for row in base if row["month"] == 9)
    assert sim_august == august  # closed future month untouched (frozen)
    assert Decimal(sim_september["net"]) == Decimal(base_september["net"]) - Decimal("200.00")
    # September re-anchors onto August's frozen cash_balance_end (5000) + its delta'd net.
    assert Decimal(sim_september["cumulative_cash"]) == Decimal("5000.00") + Decimal(
        sim_september["net"]
    )


# --------------------------------------------------------------------------- compare


def test_compare_side_by_side_and_deltas() -> None:
    base = _base()
    simulated = CondoSimulationService.simulate(base, [{"type": "add_expense", "amount": "100.00"}])
    comparison = CondoSimulationService.compare(base, simulated)
    assert len(comparison["months"]) == 3
    july = comparison["months"][0]
    assert july["net_delta"] == "0.00"  # current month unchanged
    august = comparison["months"][1]
    assert august["base_net"] == "600.00"
    assert august["simulated_net"] == "500.00"
    assert august["net_delta"] == "-100.00"
    assert august["cumulative_delta"] == "-100.00"
    # September cumulative drifts by two months of -100.
    assert comparison["months"][2]["cumulative_delta"] == "-200.00"
    assert comparison["final_cumulative_delta"] == "-200.00"
    assert comparison["total_net_delta"] == "-200.00"
    for month in comparison["months"]:
        for key in ("base_net", "simulated_net", "net_delta", "cumulative_delta"):
            assert isinstance(month[key], str)
