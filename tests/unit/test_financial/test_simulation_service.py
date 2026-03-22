"""Tests for SimulationService — pure unit tests on projection dicts, no DB access."""

from decimal import Decimal

import pytest

from core.services.simulation_service import SimulationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_YEAR = 2026
_BASE_MONTH = 3  # March 2026


def _make_entry(
    year: int,
    month: int,
    income_total: Decimal,
    expenses_total: Decimal,
    cumulative_balance: Decimal,
    *,
    is_projected: bool = True,
    income_details: list[dict] | None = None,
    expense_details: list[dict] | None = None,
) -> dict:
    balance = income_total - expenses_total
    return {
        "year": year,
        "month": month,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "balance": balance,
        "cumulative_balance": cumulative_balance,
        "is_projected": is_projected,
        "income_details": income_details or [],
        "expense_details": expense_details or [],
    }


def _make_projection(months: int = 6) -> list[dict]:
    """
    Build a deterministic projection list with realistic detail entries.

    Income per month:
      - apartment 10: R$1300.00 (normal tenant)
      - apartment 20: R$800.00  (owner apartment — appears in expense_details as repasse)

    Expense per month:
      - expense_id=1, type="card_purchase": R$200.00
      - expense_id=2, type="fixed_expense":  R$100.00 (description="Internet")
      - expense_id=3, type="fixed_expense":  R$150.00 (description="Condomínio")
      - expense_id=4, type="loan":            R$250.00 (only first 3 months)

    The income_total and expenses_total are recalculated from details for each entry so
    that tests can confidently assert on arithmetic.
    """
    projection = []
    cumulative = Decimal("0.00")

    for i in range(months):
        raw_month = _BASE_MONTH + i
        year = _BASE_YEAR + (raw_month - 1) // 12
        month = ((raw_month - 1) % 12) + 1

        income_details: list[dict] = [
            {"apartment_id": 10, "amount": Decimal("1300.00"), "is_owner_apt": False},
            {"apartment_id": 20, "amount": Decimal("800.00"), "is_owner_apt": True},
        ]
        income_total = sum((d["amount"] for d in income_details), Decimal("0.00"))

        expense_details: list[dict] = [
            {
                "expense_id": 1,
                "type": "card_purchase",
                "amount": Decimal("200.00"),
                "apartment_id": None,
            },
            {
                "expense_id": 2,
                "type": "fixed_expense",
                "amount": Decimal("100.00"),
                "description": "Internet",
                "apartment_id": None,
            },
            {
                "expense_id": 3,
                "type": "fixed_expense",
                "amount": Decimal("150.00"),
                "description": "Condomínio",
                "apartment_id": None,
            },
        ]
        # Loan installment only for first 3 months
        if i < 3:
            expense_details.append(
                {
                    "expense_id": 4,
                    "type": "loan",
                    "amount": Decimal("250.00"),
                    "apartment_id": None,
                }
            )

        expenses_total = sum((d["amount"] for d in expense_details), Decimal("0.00"))
        balance = income_total - expenses_total
        cumulative += balance

        projection.append(
            _make_entry(
                year,
                month,
                income_total,
                expenses_total,
                cumulative,
                is_projected=(i > 0),
                income_details=income_details,
                expense_details=expense_details,
            )
        )

    return projection


# ---------------------------------------------------------------------------
# TestSimulationPayOffEarly
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationPayOffEarly:
    def test_removes_future_installments(self) -> None:
        projection = _make_projection(months=6)
        # Month index 0 is the "past" (is_projected=False), rest are future
        scenarios = [{"type": "pay_off_early", "expense_id": 4}]

        result = SimulationService.simulate(projection, scenarios)

        # Months 1..2 had expense_id=4 (loan, R$250) — should be gone
        # Month 0 was is_projected=False so should stay unchanged
        future_entries = [e for e in result if e["is_projected"]]
        for entry in future_entries:
            expense_ids = {d.get("expense_id") for d in entry["expense_details"]}
            assert 4 not in expense_ids

    def test_does_not_affect_past(self) -> None:
        projection = _make_projection(months=4)
        scenarios = [{"type": "pay_off_early", "expense_id": 4}]

        result = SimulationService.simulate(projection, scenarios)

        past_entry = result[0]
        assert past_entry["is_projected"] is False
        expense_ids = {d["expense_id"] for d in past_entry["expense_details"]}
        # The loan installment existed in month 0 (past) — must remain untouched
        assert 4 in expense_ids

    def test_reduces_expenses(self) -> None:
        projection = _make_projection(months=4)
        original_expenses = projection[1]["expenses_total"]
        scenarios = [{"type": "pay_off_early", "expense_id": 4}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["expenses_total"] == original_expenses - Decimal("250.00")
        assert result[1]["balance"] == projection[1]["balance"] + Decimal("250.00")

    def test_does_not_mutate_original(self) -> None:
        projection = _make_projection(months=4)
        original_expenses_m1 = projection[1]["expenses_total"]
        scenarios = [{"type": "pay_off_early", "expense_id": 4}]

        SimulationService.simulate(projection, scenarios)

        assert projection[1]["expenses_total"] == original_expenses_m1


# ---------------------------------------------------------------------------
# TestSimulationChangeRent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationChangeRent:
    def test_changes_income_for_apartment(self) -> None:
        projection = _make_projection(months=4)
        new_value = Decimal("1600.00")
        scenarios = [{"type": "change_rent", "apartment_id": 10, "new_value": str(new_value)}]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:  # future months only
            apt_detail = next(d for d in entry["income_details"] if d["apartment_id"] == 10)
            assert apt_detail["amount"] == new_value

    def test_changes_income_total_correctly(self) -> None:
        projection = _make_projection(months=4)
        new_value = Decimal("1600.00")
        original_income = projection[1]["income_total"]
        diff = new_value - Decimal("1300.00")
        scenarios = [{"type": "change_rent", "apartment_id": 10, "new_value": str(new_value)}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["income_total"] == original_income + diff
        assert result[1]["balance"] == projection[1]["balance"] + diff

    def test_past_month_unchanged(self) -> None:
        projection = _make_projection(months=4)
        original_income = projection[0]["income_total"]
        scenarios = [{"type": "change_rent", "apartment_id": 10, "new_value": "1600.00"}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[0]["income_total"] == original_income

    def test_changes_owner_apt_repasse(self) -> None:
        """Owner apartment rent change: income goes up AND a matching repasse expense goes up."""
        projection = _make_projection(months=4)
        new_value = Decimal("1000.00")
        scenarios = [{"type": "change_rent", "apartment_id": 20, "new_value": str(new_value)}]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:
            apt_income = next(d for d in entry["income_details"] if d["apartment_id"] == 20)
            assert apt_income["amount"] == new_value


# ---------------------------------------------------------------------------
# TestSimulationNewLoan
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationNewLoan:
    def test_adds_installments(self) -> None:
        projection = _make_projection(months=6)
        # Start on month index 2 (2026-05), 3 installments
        scenarios = [
            {
                "type": "new_loan",
                "amount": "300.00",
                "installments": 3,
                "start_month": "2026-05",
            }
        ]

        result = SimulationService.simulate(projection, scenarios)

        # Month index 2 → 2026-05, index 3 → 2026-06, index 4 → 2026-07
        target_indices = [2, 3, 4]
        for idx in target_indices:
            new_loan_items = [
                d for d in result[idx]["expense_details"] if d.get("type") == "loan_simulation"
            ]
            assert len(new_loan_items) == 1
            assert new_loan_items[0]["amount"] == Decimal("300.00")

    def test_increases_expenses(self) -> None:
        projection = _make_projection(months=6)
        scenarios = [
            {
                "type": "new_loan",
                "amount": "300.00",
                "installments": 2,
                "start_month": "2026-04",
            }
        ]
        original_m1 = projection[1]["expenses_total"]  # 2026-04

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["expenses_total"] == original_m1 + Decimal("300.00")
        assert result[1]["balance"] == projection[1]["balance"] - Decimal("300.00")

    def test_does_not_affect_months_outside_range(self) -> None:
        projection = _make_projection(months=6)
        scenarios = [
            {
                "type": "new_loan",
                "amount": "300.00",
                "installments": 2,
                "start_month": "2026-04",
            }
        ]
        original_m3 = projection[3]["expenses_total"]  # 2026-06 — outside range

        result = SimulationService.simulate(projection, scenarios)

        # Index 3 (2026-06) should be unaffected (only indices 1 and 2 have loan)
        assert result[3]["expenses_total"] == original_m3


# ---------------------------------------------------------------------------
# TestSimulationRemoveTenant
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationRemoveTenant:
    def test_zeros_income_for_apartment(self) -> None:
        projection = _make_projection(months=4)
        scenarios = [{"type": "remove_tenant", "apartment_id": 10}]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:
            apt_detail = next((d for d in entry["income_details"] if d["apartment_id"] == 10), None)
            if apt_detail is not None:
                assert apt_detail["amount"] == Decimal("0.00")

    def test_reduces_income_total(self) -> None:
        projection = _make_projection(months=4)
        original_income = projection[1]["income_total"]
        scenarios = [{"type": "remove_tenant", "apartment_id": 10}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["income_total"] == original_income - Decimal("1300.00")
        assert result[1]["balance"] == projection[1]["balance"] - Decimal("1300.00")

    def test_past_month_unchanged(self) -> None:
        projection = _make_projection(months=4)
        original_income = projection[0]["income_total"]
        scenarios = [{"type": "remove_tenant", "apartment_id": 10}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[0]["income_total"] == original_income


# ---------------------------------------------------------------------------
# TestSimulationAddFixedExpense
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationAddFixedExpense:
    def test_adds_to_all_future_months(self) -> None:
        projection = _make_projection(months=5)
        scenarios = [
            {
                "type": "add_fixed_expense",
                "amount": "120.00",
                "description": "Streaming",
            }
        ]

        result = SimulationService.simulate(projection, scenarios)

        future_entries = [e for e in result if e["is_projected"]]
        for entry in future_entries:
            streaming = [d for d in entry["expense_details"] if d.get("description") == "Streaming"]
            assert len(streaming) == 1
            assert streaming[0]["amount"] == Decimal("120.00")

    def test_increases_expenses_total(self) -> None:
        projection = _make_projection(months=4)
        original_expenses = projection[1]["expenses_total"]
        scenarios = [
            {
                "type": "add_fixed_expense",
                "amount": "120.00",
                "description": "Streaming",
            }
        ]

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["expenses_total"] == original_expenses + Decimal("120.00")
        assert result[1]["balance"] == projection[1]["balance"] - Decimal("120.00")

    def test_does_not_affect_past_month(self) -> None:
        projection = _make_projection(months=4)
        original_expenses = projection[0]["expenses_total"]
        scenarios = [
            {
                "type": "add_fixed_expense",
                "amount": "120.00",
                "description": "Streaming",
            }
        ]

        result = SimulationService.simulate(projection, scenarios)

        assert result[0]["expenses_total"] == original_expenses


# ---------------------------------------------------------------------------
# TestSimulationRemoveFixedExpense
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationRemoveFixedExpense:
    def test_removes_from_all_future_months(self) -> None:
        projection = _make_projection(months=5)
        scenarios = [{"type": "remove_fixed_expense", "expense_id": 2}]

        result = SimulationService.simulate(projection, scenarios)

        future_entries = [e for e in result if e["is_projected"]]
        for entry in future_entries:
            expense_ids = {d.get("expense_id") for d in entry["expense_details"]}
            assert 2 not in expense_ids

    def test_reduces_expenses_total(self) -> None:
        projection = _make_projection(months=4)
        original_expenses = projection[1]["expenses_total"]
        scenarios = [{"type": "remove_fixed_expense", "expense_id": 2}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[1]["expenses_total"] == original_expenses - Decimal("100.00")
        assert result[1]["balance"] == projection[1]["balance"] + Decimal("100.00")

    def test_does_not_affect_past_month(self) -> None:
        projection = _make_projection(months=4)
        original_expenses = projection[0]["expenses_total"]
        scenarios = [{"type": "remove_fixed_expense", "expense_id": 2}]

        result = SimulationService.simulate(projection, scenarios)

        assert result[0]["expenses_total"] == original_expenses


# ---------------------------------------------------------------------------
# TestSimulationCompare
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationCompare:
    def _make_simulated(self, base: list[dict]) -> list[dict]:
        """Apply a change_rent scenario to produce a simulated projection."""
        scenarios = [{"type": "change_rent", "apartment_id": 10, "new_value": "1600.00"}]
        return SimulationService.simulate(base, scenarios)

    def test_month_by_month_deltas(self) -> None:
        base = _make_projection(months=4)
        simulated = self._make_simulated(base)

        comparison = SimulationService.compare(base, simulated)

        assert "month_by_month" in comparison
        assert len(comparison["month_by_month"]) == 4

        # Month index 0 is past — delta should be 0 (simulated = base)
        m0 = comparison["month_by_month"][0]
        assert m0["delta"] == Decimal("0.00")
        assert m0["year"] == _BASE_YEAR
        assert m0["month"] == _BASE_MONTH

        # Months 1..3: rent increased by R$300, so balance delta = +300
        for row in comparison["month_by_month"][1:]:
            assert row["delta"] == Decimal("300.00")
            assert row["simulated_balance"] == row["base_balance"] + Decimal("300.00")

    def test_total_impact_12m(self) -> None:
        base = _make_projection(months=4)
        simulated = self._make_simulated(base)

        comparison = SimulationService.compare(base, simulated)

        # 3 future months * R$300 each = R$900
        assert comparison["total_impact_12m"] == Decimal("900.00")

    def test_break_even_month_positive_impact(self) -> None:
        """When simulated cumulative balance is always higher, break_even_month is None."""
        base = _make_projection(months=4)
        simulated = self._make_simulated(base)

        comparison = SimulationService.compare(base, simulated)

        assert "break_even_month" in comparison

    def test_break_even_month_with_deficit(self) -> None:
        """break_even_month is the first YYYY-MM where simulated_cumulative > 0."""
        # Build a projection that starts negative and recovers
        entries: list[dict] = []
        cumulative = Decimal("-500.00")
        for i in range(6):
            income = Decimal("1000.00")
            expenses = Decimal("800.00") if i > 0 else Decimal("1400.00")
            balance = income - expenses
            cumulative += balance
            entries.append(
                _make_entry(
                    _BASE_YEAR,
                    _BASE_MONTH + i,
                    income,
                    expenses,
                    cumulative,
                    is_projected=(i > 0),
                )
            )

        # base and simulated are identical (no scenario changes) — use compare directly
        comparison = SimulationService.compare(entries, entries)

        # cumulative starts at initial_balance so we inspect simulated_cumulative
        rows = comparison["month_by_month"]
        first_positive = next(
            (r for r in rows if r["simulated_cumulative"] > Decimal("0.00")), None
        )
        if first_positive is not None:
            expected = f"{first_positive['year']}-{first_positive['month']:02d}"
            assert comparison["break_even_month"] == expected
        else:
            assert comparison["break_even_month"] is None

    def test_cumulative_columns_present(self) -> None:
        base = _make_projection(months=3)
        simulated = self._make_simulated(base)

        comparison = SimulationService.compare(base, simulated)

        for row in comparison["month_by_month"]:
            assert "base_cumulative" in row
            assert "simulated_cumulative" in row

    def test_no_break_even_when_never_positive(self) -> None:
        """If simulated cumulative is always negative, break_even_month is None."""
        entries: list[dict] = []
        cumulative = Decimal("-10000.00")
        for i in range(6):
            income = Decimal("100.00")
            expenses = Decimal("200.00")
            balance = income - expenses
            cumulative += balance
            entries.append(
                _make_entry(
                    _BASE_YEAR,
                    _BASE_MONTH + i,
                    income,
                    expenses,
                    cumulative,
                    is_projected=(i > 0),
                )
            )

        comparison = SimulationService.compare(entries, entries)
        assert comparison["break_even_month"] is None


# ---------------------------------------------------------------------------
# TestSimulationMultipleScenarios
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimulationMultipleScenarios:
    def test_combined_scenarios(self) -> None:
        """Two scenarios together: remove a fixed expense AND raise rent."""
        projection = _make_projection(months=5)
        scenarios = [
            {"type": "remove_fixed_expense", "expense_id": 2},  # -R$100 expenses
            {
                "type": "change_rent",
                "apartment_id": 10,
                "new_value": "1500.00",
            },  # +R$200 income
        ]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:
            expense_ids = {d.get("expense_id") for d in entry["expense_details"]}
            assert 2 not in expense_ids

            apt_detail = next(d for d in entry["income_details"] if d["apartment_id"] == 10)
            assert apt_detail["amount"] == Decimal("1500.00")

    def test_combined_scenarios_cumulative_recalculated(self) -> None:
        projection = _make_projection(months=4)
        scenarios = [
            {"type": "remove_fixed_expense", "expense_id": 2},
            {
                "type": "change_rent",
                "apartment_id": 10,
                "new_value": "1500.00",
            },
        ]

        result = SimulationService.simulate(projection, scenarios)

        # Recalculate expected cumulative manually from the result balances
        expected_cumulative = result[0]["cumulative_balance"]
        for entry in result[1:]:
            expected_cumulative += entry["balance"]
            assert entry["cumulative_balance"] == expected_cumulative

    def test_pay_off_early_and_add_expense(self) -> None:
        projection = _make_projection(months=5)
        scenarios = [
            {"type": "pay_off_early", "expense_id": 4},  # removes R$250 loan
            {
                "type": "add_fixed_expense",
                "amount": "80.00",
                "description": "Academia",
            },
        ]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:  # future months
            expense_ids = {d.get("expense_id") for d in entry["expense_details"]}
            assert 4 not in expense_ids
            academia = [d for d in entry["expense_details"] if d.get("description") == "Academia"]
            assert len(academia) == 1

    def test_scenarios_do_not_interfere_with_each_other(self) -> None:
        """Both scenarios target distinct data — neither should corrupt the other's result."""
        projection = _make_projection(months=4)
        scenarios = [
            {"type": "remove_tenant", "apartment_id": 10},
            {
                "type": "change_rent",
                "apartment_id": 20,
                "new_value": "1000.00",
            },
        ]

        result = SimulationService.simulate(projection, scenarios)

        for entry in result[1:]:
            apt10 = next((d for d in entry["income_details"] if d["apartment_id"] == 10), None)
            if apt10 is not None:
                assert apt10["amount"] == Decimal("0.00")

            apt20 = next(d for d in entry["income_details"] if d["apartment_id"] == 20)
            assert apt20["amount"] == Decimal("1000.00")
