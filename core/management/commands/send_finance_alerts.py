"""Management command: send_finance_alerts

Daily cron that warns the admins about IPTU installment plans at risk of losing the
prefeitura discount. Aggregates ALL of the day's WARNINGs into a SINGLE summary
Notification per admin (and CRITICALs into a second, independent one), so the admin
sees one digest instead of one per plan (design §9.3).

Idempotency: at most one summary per admin per type per São Paulo day, enforced by
is_notification_sent_on(today_sp()) — SP-aware so the window tracks the São Paulo
midnight, not UTC. Push is best-effort inside create_notification (a push failure never
drops the in-app Notification / banner).
"""

import logging
from collections.abc import Callable
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from finances.services.iptu_alert_service import IptuAlertService, IptuRiskRow

from core.models import Notification
from core.services.notification_service import create_notification, is_notification_sent_on
from core.services.timezone import today_sp

logger = logging.getLogger(__name__)

_WARNING_TITLE = "IPTU: parcelas atrasadas"
_CRITICAL_TITLE = "IPTU: parcelamento em risco"
_SCREEN = "finance"


def _warning_body(rows: list[IptuRiskRow]) -> str:
    inscricoes = ", ".join(r.external_identifier for r in rows)
    plural = "inscrições" if len(rows) > 1 else "inscrição"
    return (
        f"{len(rows)} {plural} com 1 parcela atrasada: {inscricoes}. "
        "Pague antes do próximo vencimento para não perder o parcelamento."
    )


def _critical_body(rows: list[IptuRiskRow]) -> str:
    inscricoes = ", ".join(r.external_identifier for r in rows)
    plural = "inscrições" if len(rows) > 1 else "inscrição"
    return (
        f"{len(rows)} {plural} com 2+ parcelas atrasadas: {inscricoes}. "
        "Parcelamento em risco — reparcelar na prefeitura."
    )


class Command(BaseCommand):
    help = "Send aggregated IPTU parcelamento-risk alerts to admins (daily cron, SP-aware)."

    def handle(self, *args: str, **options: str) -> None:
        today = today_sp()
        rows = IptuAlertService.evaluate(today)
        warnings = [r for r in rows if r.level == IptuAlertService.LEVEL_WARNING]
        criticals = [r for r in rows if r.level == IptuAlertService.LEVEL_CRITICAL]

        sent = 0
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            sent += self._send_summary(
                admin,
                warnings,
                notification_type=Notification.TYPE_IPTU_OVERDUE_RISK,
                title=_WARNING_TITLE,
                body_builder=_warning_body,
                today=today,
            )
            sent += self._send_summary(
                admin,
                criticals,
                notification_type=Notification.TYPE_IPTU_PARCELAMENTO_LOST,
                title=_CRITICAL_TITLE,
                body_builder=_critical_body,
                today=today,
            )

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} finance alerts."))

    def _send_summary(
        self,
        admin: User,
        rows: list[IptuRiskRow],
        *,
        notification_type: str,
        title: str,
        body_builder: Callable[[list[IptuRiskRow]], str],
        today: date,
    ) -> int:
        """Create one aggregated summary Notification for ``admin`` if there is risk and one was
        not already sent today (SP-aware). Returns 1 if created, else 0."""
        if not rows or is_notification_sent_on(admin, notification_type, today):
            return 0
        create_notification(
            recipient=admin,
            notification_type=notification_type,
            title=title,
            body=body_builder(rows),
            data={"screen": _SCREEN, "level": rows[0].level, "plan_ids": [r.plan_id for r in rows]},
        )
        return 1
