"""Condominium simulation service (Phase 5, Session 47, design §8/§15).

100% ephemeral what-if analysis over a base projection (CondoProjectionService.project output).
simulate() deepcopies the base, applies scenario deltas ONLY to future months (is_actual=False —
real/closed/current months are settled facts and stay untouched), then re-folds net and
cumulative_cash from the anchored baseline. Nothing is persisted; the base list is never mutated.

Money stays a quantized string at every boundary (quantize_money / money_str), so a simulated row
never differs from the projection by a cent.
"""

import copy
from decimal import Decimal, InvalidOperation
from typing import Any

from finances.money import money_str, quantize_money

ADD_EXPENSE = "add_expense"
REMOVE_EXPENSE = "remove_expense"
CHANGE_RENT = "change_rent"
ADD_INCOME = "add_income"

VALID_SCENARIO_TYPES = frozenset([ADD_EXPENSE, REMOVE_EXPENSE, CHANGE_RENT, ADD_INCOME])

ZERO_MONEY = Decimal("0.00")

# A money value must fit DecimalField(max_digits=12, decimal_places=2): |value| < 10**10. This also
# keeps quantize_money safely under the Decimal context precision, so a finite-but-huge input like
# "1e1000" is rejected in validation (400) instead of raising InvalidOperation later (500).
_MAX_MONEY_MAGNITUDE = Decimal(10) ** 10

_ERR_NOT_OBJECT = "Cenário {index}: cada cenário deve ser um objeto."
_ERR_TYPE_REQUIRED = "Cenário {index}: o campo 'type' é obrigatório."
_ERR_TYPE_INVALID = "Cenário {index}: tipo '{type}' inválido. Tipos válidos: {valid}."
_ERR_FIELD_REQUIRED = "Cenário {index}: o campo '{field}' é obrigatório e deve ser um número."
_ERR_MONTHS_INVALID = "Cenário {index}: o campo 'months' deve ser um inteiro não negativo."


def _scenario_value_field(scenario_type: str) -> str:
    """The numeric field a scenario carries: change_rent uses 'delta', the rest use 'amount'."""
    return "delta" if scenario_type == CHANGE_RENT else "amount"


def _decimal_or_none(value: object) -> Decimal | None:
    """Finite, in-range money Decimal of a scalar, or None when missing / not a number / out of range.

    ``Decimal('NaN')`` / ``Decimal('Infinity')`` parse WITHOUT raising, so a non-finite value would
    otherwise slip past validation and corrupt the projection or blow up ``_apply``. A finite but
    huge value (e.g. ``"1e1000"``) is also rejected: quantizing it later would raise InvalidOperation
    (HTTP 500). Both are caught here at the single entry point so validate_scenarios returns a clean
    400 instead.
    """
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation, ValueError, TypeError:
        return None
    if not result.is_finite() or abs(result) >= _MAX_MONEY_MAGNITUDE:
        return None
    return result


def _is_valid_months(scenario: dict[str, Any]) -> bool:
    """A present ``months`` window must be a non-negative int (a JSON bool is NOT an int here)."""
    if "months" not in scenario:
        return True
    months = scenario["months"]
    return isinstance(months, int) and not isinstance(months, bool) and months >= 0


class CondoSimulationService:
    """Stateless ephemeral simulation: deltas in memory, deltas only on the future, zero DB."""

    @staticmethod
    def validate_scenarios(scenarios: list[Any]) -> list[str]:
        """PT messages for invalid scenarios (untrusted JSON: non-object, missing/invalid type,
        missing/non-finite value, invalid months window)."""
        errors: list[str] = []
        for index, scenario in enumerate(scenarios):
            if not isinstance(scenario, dict):
                errors.append(_ERR_NOT_OBJECT.format(index=index))
                continue
            scenario_type = scenario.get("type")
            if not scenario_type:
                errors.append(_ERR_TYPE_REQUIRED.format(index=index))
                continue
            if scenario_type not in VALID_SCENARIO_TYPES:
                errors.append(
                    _ERR_TYPE_INVALID.format(
                        index=index,
                        type=scenario_type,
                        valid=", ".join(sorted(VALID_SCENARIO_TYPES)),
                    )
                )
                continue
            field = _scenario_value_field(scenario_type)
            if _decimal_or_none(scenario.get(field)) is None:
                errors.append(_ERR_FIELD_REQUIRED.format(index=index, field=field))
                continue
            if not _is_valid_months(scenario):
                errors.append(_ERR_MONTHS_INVALID.format(index=index))
        return errors

    @staticmethod
    def simulate(
        base: list[dict[str, Any]], scenarios: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply scenarios to a deepcopy of ``base`` (future months only), then re-fold the cash.

        Ephemeral: no DB write, and ``base`` is never mutated. Real/closed/current months
        (is_actual=True) keep their figures; future months get their income/expense deltas and a
        recomputed net + cumulative_cash folded from the baseline.
        """
        simulated = copy.deepcopy(base)
        if not simulated:
            return simulated
        for scenario in scenarios:
            CondoSimulationService._apply(simulated, scenario)
        CondoSimulationService._refold(simulated)
        return simulated

    @staticmethod
    def compare(base: list[dict[str, Any]], simulated: list[dict[str, Any]]) -> dict[str, Any]:
        """Side-by-side base × simulated per month + Δ net per month + Δ final cumulative cash."""
        months: list[dict[str, Any]] = []
        total_net_delta = ZERO_MONEY
        for base_row, sim_row in zip(base, simulated, strict=True):
            base_net = Decimal(base_row["net"])
            sim_net = Decimal(sim_row["net"])
            base_cash = Decimal(base_row["cumulative_cash"])
            sim_cash = Decimal(sim_row["cumulative_cash"])
            total_net_delta += sim_net - base_net
            months.append(
                {
                    "year": base_row["year"],
                    "month": base_row["month"],
                    "base_net": money_str(base_net),
                    "simulated_net": money_str(sim_net),
                    "net_delta": money_str(sim_net - base_net),
                    "base_cumulative_cash": money_str(base_cash),
                    "simulated_cumulative_cash": money_str(sim_cash),
                    "cumulative_delta": money_str(sim_cash - base_cash),
                }
            )
        final_base = Decimal(base[-1]["cumulative_cash"]) if base else ZERO_MONEY
        final_sim = Decimal(simulated[-1]["cumulative_cash"]) if simulated else ZERO_MONEY
        return {
            "months": months,
            "final_cumulative_delta": money_str(final_sim - final_base),
            "total_net_delta": money_str(total_net_delta),
        }

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _apply(simulated: list[dict[str, Any]], scenario: dict[str, Any]) -> None:
        """Apply one scenario's delta to the future (is_actual=False) months in place."""
        future = [row for row in simulated if not row["is_actual"]]
        months_limit = scenario.get("months")
        if _is_valid_months(scenario) and months_limit is not None:
            future = future[:months_limit]
        scenario_type = scenario["type"]
        value = _decimal_or_none(scenario.get(_scenario_value_field(scenario_type)))
        if value is None:  # already rejected by validate_scenarios; defensive no-op
            return
        amount = quantize_money(value)
        for row in future:
            if scenario_type in (ADD_INCOME, CHANGE_RENT):
                row["income_total"] = money_str(Decimal(row["income_total"]) + amount)
            elif scenario_type == ADD_EXPENSE:
                row["expenses_total"] = money_str(Decimal(row["expenses_total"]) + amount)
            elif scenario_type == REMOVE_EXPENSE:
                reduced = max(ZERO_MONEY, Decimal(row["expenses_total"]) - amount)
                row["expenses_total"] = money_str(reduced)

    @staticmethod
    def _refold(simulated: list[dict[str, Any]]) -> None:
        """Recompute net + cumulative_cash for future months, anchored on the baseline cash.

        Real/closed/current months keep their figures and re-anchor the running cash to their
        frozen cumulative; future months recompute net from the (possibly delta'd) pontas and fold
        the running cash forward.
        """
        # The projection's first row is always the current (actual) month, so the first iteration
        # re-anchors `running` to that frozen cumulative before any future row is folded — this
        # initial value is just a definite starting point, never the anchor itself.
        running = ZERO_MONEY
        for row in simulated:
            if row["is_actual"]:
                running = Decimal(row["cumulative_cash"])
                continue
            net = quantize_money(Decimal(row["income_total"]) - Decimal(row["expenses_total"]))
            running = quantize_money(running + net)
            row["net"] = money_str(net)
            row["cumulative_cash"] = money_str(running)
