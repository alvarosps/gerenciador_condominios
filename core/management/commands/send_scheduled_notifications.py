"""
Management command: send_scheduled_notifications

Sends automated push/in-app notifications to tenants based on
payment due dates and contract expiry. Designed to run daily via cron.

Notifications sent:
  due_reminder     — 3 days before the monthly due date
  due_today        — on the day rent is due
  overdue          — at 1, 5, and 15 days after the due date (if unpaid)
  contract_expiring — 30 days before the contract end date

Idempotency: each notification type is sent at most once per São Paulo day per user,
enforced by is_notification_sent_on() (SP-aware — tracks the SP midnight, not UTC).
"""

import calendar
import logging
from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Lease, RentPayment, Tenant
from core.services.notification_service import create_notification, is_notification_sent_on
from core.services.rent_schedule_service import RentScheduleService
from core.services.timezone import today_sp

logger = logging.getLogger(__name__)

_DUE_REMINDER_DAYS_BEFORE = 3
_CONTRACT_EXPIRY_WARNING_DAYS = 30
_OVERDUE_CHECK_DAYS = (1, 5, 15)


def _contract_end_date(lease: Lease) -> date:
    """Return the date on which the lease contract expires."""
    return lease.start_date + relativedelta(months=lease.validity_months)


def _has_rent_payment_for_month(lease: Lease, reference_month: date) -> bool:
    """Return True if a RentPayment exists for the given lease and month."""
    return RentPayment.objects.filter(
        lease=lease,
        reference_month__year=reference_month.year,
        reference_month__month=reference_month.month,
    ).exists()


def _current_reference_month(today: date) -> date:
    """Return the first day of the current month as the reference month."""
    return today.replace(day=1)


def _next_due_date(today: date, due_day: int) -> date:
    """Return the next occurrence of ``due_day`` on/after ``today``.

    Clamps ``due_day`` to the last valid day of each month (e.g. 31 -> Feb 28). Computed
    by adding days/months rather than comparing the day-of-month against ``today``, so a
    due_day of 1-3 near a month boundary correctly rolls into the next month instead of
    silently pointing at an already-past date in the current month (which made the
    3-day-before reminder never fire for those due days).
    """
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    this_month_due = today.replace(day=min(due_day, last_day_of_month))
    if this_month_due >= today:
        return this_month_due

    next_month = today.replace(day=1) + relativedelta(months=1)
    last_day_of_next_month = calendar.monthrange(next_month.year, next_month.month)[1]
    return next_month.replace(day=min(due_day, last_day_of_next_month))


class Command(BaseCommand):
    help = "Send scheduled payment-due and contract-expiry notifications to tenants."

    def handle(self, *args: str, **options: str) -> None:
        today = today_sp()
        sent_count = 0

        reference_month = _current_reference_month(today)
        collectible_ids = {
            lease.pk for lease in RentScheduleService.collectible_leases(reference_month)
        }

        active_leases = Lease.objects.filter(is_deleted=False).select_related(
            "responsible_tenant", "responsible_tenant__user", "apartment"
        )

        for lease in active_leases:
            tenant = lease.responsible_tenant
            if not isinstance(tenant.user, User):
                continue

            if lease.pk in collectible_ids:
                sent_count += self._send_due_notifications(
                    lease, tenant, tenant.user, today, tenant.due_day
                )
            sent_count += self._send_contract_expiry_notification(lease, tenant.user, today)

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} notifications."))

    def _send_due_notifications(
        self,
        lease: Lease,
        tenant: Tenant,
        user: User,
        today: date,
        due_day: int,
    ) -> int:
        """Send due_reminder, due_today, and overdue notifications. Returns count sent."""
        sent = 0
        reference_month = _current_reference_month(today)

        # Skip due_reminder/due_today/overdue entirely once the month's rent is paid —
        # a paid tenant should never get a reminder to pay it again.
        if _has_rent_payment_for_month(lease, reference_month):
            return sent

        # This month's due date (clamped), used for the overdue day-count — an overdue
        # check always references the current month's due date, never a rolled-forward one.
        last_day_of_month = calendar.monthrange(today.year, today.month)[1]
        effective_due_day = min(due_day, last_day_of_month)
        current_month_due_date = today.replace(day=effective_due_day)
        days_past_due = (today - current_month_due_date).days

        # Next occurrence of due_day on/after today — computed by adding days/months so a
        # due_day of 1-3 near a month boundary rolls into the next month correctly instead
        # of pointing at an already-past date in the current month.
        next_due_date = _next_due_date(today, due_day)
        days_until_due = (next_due_date - today).days

        # due_reminder: 3 days before due
        if days_until_due == _DUE_REMINDER_DAYS_BEFORE:
            if not is_notification_sent_on(user, "due_reminder", today):
                create_notification(
                    recipient=user,
                    notification_type="due_reminder",
                    title="Lembrete de vencimento",
                    body=f"Seu aluguel vence em {_DUE_REMINDER_DAYS_BEFORE} dias (dia {next_due_date.day}).",
                    data={"screen": "payments", "lease_id": lease.pk},
                )
                sent += 1

        # due_today: on the due date
        elif days_until_due == 0:
            if not is_notification_sent_on(user, "due_today", today):
                create_notification(
                    recipient=user,
                    notification_type="due_today",
                    title="Vencimento hoje",
                    body=f"Seu aluguel vence hoje (dia {next_due_date.day}). Lembre-se de pagar!",
                    data={"screen": "payments", "lease_id": lease.pk},
                )
                sent += 1

        # overdue: 1, 5, or 15 days past due
        elif days_past_due in _OVERDUE_CHECK_DAYS and not is_notification_sent_on(
            user, "overdue", today
        ):
            create_notification(
                recipient=user,
                notification_type="overdue",
                title="Aluguel atrasado",
                body=f"Seu aluguel está {days_past_due} dia(s) atrasado. Por favor, regularize.",
                data={"screen": "payments", "lease_id": lease.pk, "days_late": days_past_due},
            )
            sent += 1

        return sent

    def _send_contract_expiry_notification(
        self,
        lease: Lease,
        user: User,
        today: date,
    ) -> int:
        """Send contract_expiring notification 30 days before end. Returns count sent."""
        end_date = _contract_end_date(lease)
        days_until_end = (end_date - today).days

        if days_until_end == _CONTRACT_EXPIRY_WARNING_DAYS and not is_notification_sent_on(
            user, "contract_expiring", today
        ):
            create_notification(
                recipient=user,
                notification_type="contract_expiring",
                title="Contrato vencendo",
                body=f"Seu contrato vence em {_CONTRACT_EXPIRY_WARNING_DAYS} dias ({end_date:%d/%m/%Y}).",
                data={"screen": "contract", "lease_id": lease.pk},
            )
            return 1
        return 0
