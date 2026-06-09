"""IPTU parcelamento-loss risk evaluation (design §9.1, Apêndice B Fase 5).

A standalone IPTU installment plan loses its prefeitura discount if the taxpayer
falls behind: 1 overdue parcela is a WARNING (pay it this month alongside the next
one), 2+ overdue is CRITICAL (the parcelamento is effectively lost — reparcelar).

Read-only: overdue status comes from ``Bill.objects.with_amounts(today).is_overdue``
(``due_date < today ∧ amount_remaining > 0 ∧ lifecycle ACTIVE``) — never recomputed in
Python. ``evaluate`` is ALWAYS called with ``today_sp()`` (settings is UTC). It has no
side effects; the ``send_finance_alerts`` command is what persists Notifications.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, cast

from finances.models import (
    Bill,
    BillingAccountType,
    InstallmentPlan,
    InstallmentPlanState,
)

_CONDOMINIUM_LABEL = "Condomínio"


class _OverdueBill(Protocol):
    # Bill.objects.with_amounts(today) annotates these; django-stubs does not propagate
    # dynamic annotations onto the model instance, so we read them via this cast.
    due_date: date
    is_overdue: bool


@dataclass(frozen=True)
class IptuRiskRow:
    """Uma linha de risco por plano de IPTU ativo. level ∈ {WARNING, CRITICAL}."""

    plan_id: int
    external_identifier: str  # inscrição (billing_account.external_identifier)
    building_label: str  # prédio (street_number) ou "Condomínio" se sem prédio
    level: str  # IptuAlertService.LEVEL_WARNING / LEVEL_CRITICAL
    overdue_count: int  # nº de parcela-bills vencidas não pagas
    deadline: date | None  # due_date da 1ª parcela AINDA NÃO vencida (None se nenhuma)
    overdue_due_dates: list[date] = field(default_factory=list)  # vencimentos em atraso
    message: str = ""  # texto PT pronto p/ banner/push


class IptuAlertService:
    LEVEL_WARNING = "warning"
    LEVEL_CRITICAL = "critical"

    # CRITICAL rows sort before WARNING ones; ties broken by external_identifier (determinístico).
    _LEVEL_ORDER = {LEVEL_CRITICAL: 0, LEVEL_WARNING: 1}

    @staticmethod
    def evaluate(today: date) -> list[IptuRiskRow]:
        """Risco de perda de parcelamento de IPTU. 1 parcela vencida = WARNING; >=2 = CRITICAL.

        Read-only via ``Bill.with_amounts(today).is_overdue`` — sem N+1, sem soma em Python.
        SEMPRE chamar com ``today_sp()`` (settings é UTC).
        """
        plans = InstallmentPlan.objects.filter(
            lifecycle_state=InstallmentPlanState.ACTIVE,
            embedded=False,
            billing_account__account_type=BillingAccountType.IPTU,
        ).select_related("billing_account", "building")

        rows: list[IptuRiskRow] = []
        for plan in plans:
            row = IptuAlertService._evaluate_plan(plan, today)
            if row is not None:
                rows.append(row)

        rows.sort(key=lambda r: (IptuAlertService._LEVEL_ORDER[r.level], r.external_identifier))
        return rows

    @staticmethod
    def _evaluate_plan(plan: InstallmentPlan, today: date) -> IptuRiskRow | None:
        bills = list(Bill.objects.with_amounts(today).filter(installment__plan=plan))
        annotated = [cast(_OverdueBill, bill) for bill in bills]

        overdue_due_dates = sorted(b.due_date for b in annotated if b.is_overdue)
        overdue_count = len(overdue_due_dates)
        if overdue_count == 0:
            return None

        deadline = IptuAlertService._earliest_open_due_date(annotated, today)
        external_identifier = (
            plan.billing_account.external_identifier if plan.billing_account else ""
        )
        building_label = (
            str(plan.building.street_number) if plan.building is not None else _CONDOMINIUM_LABEL
        )
        level = (
            IptuAlertService.LEVEL_WARNING
            if overdue_count == 1
            else IptuAlertService.LEVEL_CRITICAL
        )
        message = IptuAlertService._build_message(
            level=level,
            external_identifier=external_identifier,
            building_label=building_label,
            overdue_due_dates=overdue_due_dates,
            deadline=deadline,
        )
        return IptuRiskRow(
            plan_id=plan.pk,
            external_identifier=external_identifier,
            building_label=building_label,
            level=level,
            overdue_count=overdue_count,
            deadline=deadline,
            overdue_due_dates=overdue_due_dates,
            message=message,
        )

    @staticmethod
    def _earliest_open_due_date(bills: list[_OverdueBill], today: date) -> date | None:
        """The smallest due_date >= today among the plan's not-yet-overdue bills (1ª em aberto)."""
        open_due_dates = [b.due_date for b in bills if not b.is_overdue and b.due_date >= today]
        return min(open_due_dates) if open_due_dates else None

    @staticmethod
    def _build_message(
        *,
        level: str,
        external_identifier: str,
        building_label: str,
        overdue_due_dates: list[date],
        deadline: date | None,
    ) -> str:
        prefix = f"IPTU {external_identifier} ({building_label}):"
        if level == IptuAlertService.LEVEL_CRITICAL:
            return (
                f"{prefix} {len(overdue_due_dates)} parcelas atrasadas — "
                "parcelamento em risco. Reparcelar na prefeitura."
            )
        overdue_str = overdue_due_dates[0].strftime("%d/%m")
        if deadline is None:
            return (
                f"{prefix} 1 parcela atrasada (venc. {overdue_str}). "
                "Pague-a este mês ou o parcelamento será cancelado."
            )
        deadline_str = deadline.strftime("%d/%m")
        return (
            f"{prefix} 1 parcela atrasada (venc. {overdue_str}). "
            f"Pague-a este mês junto com a próxima (venc. {deadline_str}) "
            "ou o parcelamento será cancelado."
        )
