"""Simulation service for financial "what-if" scenario analysis.

Provides two simulation modes:
- `simulate()`: pure dict-based, operates on projections with income_details/expense_details
- `simulate_from_db()`: resolves scenario parameters from the database, applies deltas to totals

Both modes use deepcopy to avoid mutating the original projection.
"""

import copy
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from core.models import Apartment, Expense, ExpenseInstallment

VALID_SCENARIO_TYPES = frozenset(
    [
        "pay_off_early",
        "change_rent",
        "new_loan",
        "remove_tenant",
        "add_fixed_expense",
        "remove_fixed_expense",
    ]
)

MONTHS_IN_YEAR = 12


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_scenarios(scenarios: list[dict[str, Any]]) -> list[str]:
    """Return a list of error messages for invalid scenarios."""
    errors = []
    for i, scenario in enumerate(scenarios):
        scenario_type = scenario.get("type")
        if not scenario_type:
            errors.append(f"Cenário {i}: campo 'type' é obrigatório.")
        elif scenario_type not in VALID_SCENARIO_TYPES:
            errors.append(
                f"Cenário {i}: tipo '{scenario_type}' inválido. "
                f"Tipos válidos: {sorted(VALID_SCENARIO_TYPES)}."
            )
    return errors


# ---------------------------------------------------------------------------
# Pure dict-based scenario handlers (for simulate)
# ---------------------------------------------------------------------------


def _apply_pay_off_early(entry: dict[str, Any], expense_id: int) -> None:
    """Remove expense_details items matching expense_id from a single month entry."""
    details = entry.get("expense_details", [])
    entry["expense_details"] = [d for d in details if d.get("expense_id") != expense_id]


def _apply_change_rent(entry: dict[str, Any], apartment_id: int, new_value: Decimal) -> None:
    """Update income amount for a specific apartment in a single month entry."""
    for detail in entry.get("income_details", []):
        if detail.get("apartment_id") == apartment_id:
            detail["amount"] = new_value


def _apply_new_loan(
    entry: dict[str, Any],
    installment_amount: Decimal,
    loan_months: set[tuple[int, int]],
) -> None:
    """Add a loan installment to expense_details if the month matches."""
    key = (entry["year"], entry["month"])
    if key in loan_months:
        details = entry.get("expense_details", [])
        details.append(
            {
                "type": "loan_simulation",
                "amount": installment_amount,
                "description": "Novo empréstimo (simulação)",
            }
        )
        entry["expense_details"] = details


def _apply_remove_tenant(entry: dict[str, Any], apartment_id: int) -> None:
    """Zero out income for a specific apartment in a single month entry."""
    for detail in entry.get("income_details", []):
        if detail.get("apartment_id") == apartment_id:
            detail["amount"] = Decimal("0.00")


def _apply_add_fixed_expense(entry: dict[str, Any], amount: Decimal, description: str) -> None:
    """Add a fixed expense to expense_details for a single month entry."""
    details = entry.get("expense_details", [])
    details.append(
        {
            "type": "fixed_expense_simulation",
            "amount": amount,
            "description": description,
        }
    )
    entry["expense_details"] = details


def _apply_remove_fixed_expense(entry: dict[str, Any], expense_id: int) -> None:
    """Remove expense_details items matching expense_id from a single month entry."""
    details = entry.get("expense_details", [])
    entry["expense_details"] = [d for d in details if d.get("expense_id") != expense_id]


def _recalculate_totals(projection: list[dict[str, Any]]) -> None:
    """Recalculate income_total, expenses_total, balance, and cumulative_balance."""
    cumulative = Decimal("0.00")
    first_past_found = False

    for entry in projection:
        if not entry.get("is_projected", True) and not first_past_found:
            first_past_found = True
            cumulative = entry["cumulative_balance"]
            continue

        income_details = entry.get("income_details", [])
        expense_details = entry.get("expense_details", [])

        if income_details:
            entry["income_total"] = sum((d["amount"] for d in income_details), Decimal("0.00"))
        if expense_details:
            entry["expenses_total"] = sum((d["amount"] for d in expense_details), Decimal("0.00"))

        entry["balance"] = entry["income_total"] - entry["expenses_total"]
        cumulative += entry["balance"]
        entry["cumulative_balance"] = cumulative


def _build_loan_months(start_month: str, installments: int) -> set[tuple[int, int]]:
    """Parse start_month 'YYYY-MM' and return set of (year, month) tuples."""
    parts = start_month.split("-")
    year = int(parts[0])
    month = int(parts[1])

    months: set[tuple[int, int]] = set()
    for _ in range(installments):
        months.add((year, month))
        month += 1
        if month > MONTHS_IN_YEAR:
            month = 1
            year += 1
    return months


def _pure_pay_off_early(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    expense_id = int(scenario["expense_id"])
    for entry in entries:
        _apply_pay_off_early(entry, expense_id)


def _pure_change_rent(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    apartment_id = int(scenario["apartment_id"])
    new_value = Decimal(str(scenario["new_value"]))
    for entry in entries:
        _apply_change_rent(entry, apartment_id, new_value)


def _pure_new_loan(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    amount = Decimal(str(scenario["amount"]))
    installments = int(scenario["installments"])
    start_month = str(scenario["start_month"])
    loan_months = _build_loan_months(start_month, installments)
    for entry in entries:
        _apply_new_loan(entry, amount, loan_months)


def _pure_remove_tenant(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    apartment_id = int(scenario["apartment_id"])
    for entry in entries:
        _apply_remove_tenant(entry, apartment_id)


def _pure_add_fixed_expense(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    amount = Decimal(str(scenario["amount"]))
    description = scenario.get("description", "Despesa fixa (simulação)")
    for entry in entries:
        _apply_add_fixed_expense(entry, amount, description)


def _pure_remove_fixed_expense(entries: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    expense_id = int(scenario["expense_id"])
    for entry in entries:
        _apply_remove_fixed_expense(entry, expense_id)


_PURE_SCENARIO_HANDLERS: dict[str, Any] = {
    "pay_off_early": _pure_pay_off_early,
    "change_rent": _pure_change_rent,
    "new_loan": _pure_new_loan,
    "remove_tenant": _pure_remove_tenant,
    "add_fixed_expense": _pure_add_fixed_expense,
    "remove_fixed_expense": _pure_remove_fixed_expense,
}


# ---------------------------------------------------------------------------
# DB-aware scenario handlers (for simulate_from_db)
# ---------------------------------------------------------------------------


def _db_pay_off_early(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Remove future installment amounts from the projection using DB data."""
    expense_id = int(scenario["expense_id"])
    try:
        expense = Expense.objects.get(pk=expense_id)
    except Expense.DoesNotExist:
        return
    unpaid = ExpenseInstallment.objects.filter(expense=expense, is_paid=False).values(
        "due_date", "amount"
    )
    relief: dict[tuple[int, int], Decimal] = {}
    for inst in unpaid:
        key = (inst["due_date"].year, inst["due_date"].month)
        relief[key] = relief.get(key, Decimal("0.00")) + inst["amount"]
    for entry in projection:
        saving = relief.get((entry["year"], entry["month"]), Decimal("0.00"))
        if saving > Decimal("0.00"):
            entry["expenses_total"] -= saving
            entry["balance"] = entry["income_total"] - entry["expenses_total"]


def _db_change_rent(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Change rent for an apartment using current DB value as baseline."""
    apartment_id = int(scenario["apartment_id"])
    new_value = Decimal(str(scenario["new_value"]))
    try:
        apartment = Apartment.objects.get(pk=apartment_id)
        current_value = apartment.rental_value
    except ObjectDoesNotExist:
        return
    delta = new_value - current_value
    for entry in projection:
        entry["income_total"] += delta
        entry["balance"] = entry["income_total"] - entry["expenses_total"]


def _db_new_loan(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Add new loan installments to the projection."""
    amount = Decimal(str(scenario["amount"]))
    installments = int(scenario["installments"])
    start_month = str(scenario["start_month"])
    loan_months = _build_loan_months(start_month, installments)
    for entry in projection:
        if (entry["year"], entry["month"]) in loan_months:
            entry["expenses_total"] += amount
            entry["balance"] = entry["income_total"] - entry["expenses_total"]


def _db_remove_tenant(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Remove rental income for an apartment using DB data."""
    apartment_id = int(scenario["apartment_id"])
    try:
        apartment = Apartment.objects.get(pk=apartment_id)
        rental_value = apartment.rental_value
    except ObjectDoesNotExist:
        return
    for entry in projection:
        entry["income_total"] -= rental_value
        entry["balance"] = entry["income_total"] - entry["expenses_total"]


def _db_add_fixed_expense(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Add a fixed monthly expense to every month."""
    amount = Decimal(str(scenario["amount"]))
    for entry in projection:
        entry["expenses_total"] += amount
        entry["balance"] = entry["income_total"] - entry["expenses_total"]


def _db_remove_fixed_expense(projection: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
    """Remove a recurring fixed expense using DB data."""
    expense_id = int(scenario["expense_id"])
    try:
        expense = Expense.objects.get(pk=expense_id)
    except Expense.DoesNotExist:
        return
    monthly_amount = expense.expected_monthly_amount or Decimal("0.00")
    if monthly_amount == Decimal("0.00"):
        return
    for entry in projection:
        entry["expenses_total"] -= monthly_amount
        entry["balance"] = entry["income_total"] - entry["expenses_total"]


_DB_SCENARIO_HANDLERS: dict[str, Any] = {
    "pay_off_early": _db_pay_off_early,
    "change_rent": _db_change_rent,
    "new_loan": _db_new_loan,
    "remove_tenant": _db_remove_tenant,
    "add_fixed_expense": _db_add_fixed_expense,
    "remove_fixed_expense": _db_remove_fixed_expense,
}


def _recalculate_cumulative(projection: list[dict[str, Any]]) -> None:
    """Recalculate cumulative_balance across all entries."""
    cumulative = Decimal("0.00")
    for i, entry in enumerate(projection):
        if i == 0 and not entry.get("is_projected", True):
            cumulative = entry.get("cumulative_balance", Decimal("0.00"))
            continue
        cumulative += entry["balance"]
        entry["cumulative_balance"] = cumulative


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class SimulationService:
    """Service for cash flow simulation — applies what-if scenarios to a base projection."""

    @staticmethod
    def validate_scenarios(scenarios: list[dict[str, Any]]) -> list[str]:
        """Return validation errors for scenarios, empty list if all valid."""
        return _validate_scenarios(scenarios)

    @staticmethod
    def simulate(
        base_projection: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply scenarios to a deepcopy of base_projection (pure dict-based).

        Only projected (future) months are modified; past months are preserved as-is.
        Requires projection entries to contain income_details and expense_details.
        """
        projection = copy.deepcopy(base_projection)

        for scenario in scenarios:
            future_entries = [e for e in projection if e.get("is_projected", True)]
            handler = _PURE_SCENARIO_HANDLERS.get(scenario["type"])
            if handler:
                handler(future_entries, scenario)

        _recalculate_totals(projection)
        return projection

    @staticmethod
    def simulate_from_db(
        base_projection: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """DB-aware simulation — resolves scenario parameters from the database.

        For scenarios that reference expense_id or apartment_id, queries the DB
        to determine amounts, then applies deltas directly to totals.
        Does NOT mutate the original projection (uses deepcopy).
        """
        projection = copy.deepcopy(base_projection)

        for scenario in scenarios:
            handler = _DB_SCENARIO_HANDLERS.get(scenario["type"])
            if handler:
                handler(projection, scenario)

        _recalculate_cumulative(projection)
        return projection

    @staticmethod
    def compare(
        base: list[dict[str, Any]],
        simulated: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a month-by-month comparison between base and simulated projections."""
        month_by_month = []
        total_impact = Decimal("0.00")
        break_even_month: str | None = None

        for base_month, sim_month in zip(base, simulated, strict=True):
            base_balance = base_month["balance"]
            sim_balance = sim_month["balance"]
            delta = sim_balance - base_balance
            total_impact += delta

            base_cumulative = base_month["cumulative_balance"]
            simulated_cumulative = sim_month["cumulative_balance"]

            if break_even_month is None and simulated_cumulative > Decimal("0.00"):
                break_even_month = f"{sim_month['year']}-{sim_month['month']:02d}"

            month_by_month.append(
                {
                    "year": base_month["year"],
                    "month": base_month["month"],
                    "base_balance": base_balance,
                    "simulated_balance": sim_balance,
                    "delta": delta,
                    "base_cumulative": base_cumulative,
                    "simulated_cumulative": simulated_cumulative,
                }
            )

        return {
            "month_by_month": month_by_month,
            "total_impact_12m": total_impact,
            "break_even_month": break_even_month,
        }
