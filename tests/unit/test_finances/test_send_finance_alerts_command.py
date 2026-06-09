"""Session 61 — send_finance_alerts management command (design §9.3).

Aggregates ALL IPTU WARNINGs into a SINGLE summary Notification per admin per day
(not one per plan), with CRITICAL as an independent type, idempotent via the SP-aware
is_notification_sent_on(today_sp()). Push is best-effort inside create_notification.

External push (Expo HTTP + Web Push / VAPID) is mocked at the HTTP boundary; the in-app
Notification rows (real ORM) are the assertion target. Only freezegun and the HTTP push
boundary are mocked — IptuAlertService / create_notification / ORM are real.
"""

import contextlib
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
import requests as http_requests
from django.contrib.auth.models import User
from django.core.management import call_command
from finances.models import BillingAccountType, InstallmentPlanState
from freezegun import freeze_time

from core.models import Notification
from tests.constants import TEST_PASSWORD
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_billing_account,
    make_installment,
    make_installment_plan,
)

pytestmark = pytest.mark.django_db

FROZEN = "2026-07-15 12:00:00"


@contextlib.contextmanager
def _no_push() -> Iterator[None]:
    """Stub the external push HTTP boundary (Expo + Web Push) — no outbound traffic."""
    with (
        patch("core.services.notification_service.http_requests.post"),
        patch("core.services.notification_service.webpush"),
    ):
        yield


def _make_admin(username: str, *, is_staff: bool = True, is_active: bool = True) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password=TEST_PASSWORD,
        is_staff=is_staff,
        is_active=is_active,
    )


def _iptu_plan(external_identifier: str, condominium=None):
    account = make_billing_account(
        condominium=condominium,
        account_type=BillingAccountType.IPTU,
        external_identifier=external_identifier,
        name=f"IPTU {external_identifier}",
    )
    return make_installment_plan(
        condominium=account.condominium,
        building=account.building,
        billing_account=account,
        embedded=False,
        lifecycle_state=InstallmentPlanState.ACTIVE,
        installment_count=10,
    )


def _parcela_bill(plan, *, number: int, due_date: date, amount: str = "100.00") -> None:
    installment = make_installment(
        plan=plan, number=number, due_date=due_date, amount=Decimal(amount)
    )
    bill = make_bill(
        condominium=plan.condominium,
        building=plan.building,
        installment=installment,
        due_date=due_date,
        competence_month=due_date.replace(day=1),
        description=f"IPTU parcela {number}",
        behavior="installment",
    )
    make_bill_line_item(bill=bill, amount=Decimal(amount))


def _warning_plan(external_identifier: str, condominium=None) -> None:
    plan = _iptu_plan(external_identifier, condominium=condominium)
    _parcela_bill(plan, number=1, due_date=date(2026, 6, 10))


def _critical_plan(external_identifier: str, condominium=None) -> None:
    plan = _iptu_plan(external_identifier, condominium=condominium)
    _parcela_bill(plan, number=1, due_date=date(2026, 5, 10))
    _parcela_bill(plan, number=2, due_date=date(2026, 6, 10))


@freeze_time(FROZEN)
def test_nine_plans_one_warning_summary_per_admin() -> None:
    """9 planos IPTU com 1 parcela vencida cada + 2 admins → 2 Notifications WARNING (1/admin),
    NÃO 18; o corpo enumera as 9 inscrições."""
    admin_a = _make_admin("admin-a")
    admin_b = _make_admin("admin-b")
    base_account = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="000000", name="seed"
    )
    condo = base_account.condominium
    inscricoes = [f"51640{n}" for n in range(1, 10)]  # 9 distinct
    for insc in inscricoes:
        _warning_plan(insc, condominium=condo)

    with _no_push():
        call_command("send_finance_alerts")

    warnings = Notification.objects.filter(type=Notification.TYPE_IPTU_OVERDUE_RISK)
    assert warnings.count() == 2  # one per admin, NOT 18
    recipients = set(warnings.values_list("recipient_id", flat=True))
    assert recipients == {admin_a.pk, admin_b.pk}
    first_warning = warnings.first()
    assert first_warning is not None
    for insc in inscricoes:
        assert insc in first_warning.body


@freeze_time(FROZEN)
def test_critical_summary_separate_from_warning() -> None:
    """Planos WARNING + planos CRITICAL → 2 Notifications/admin (TYPE_IPTU_OVERDUE_RISK +
    TYPE_IPTU_PARCELAMENTO_LOST); tipos independentes."""
    admin = _make_admin("admin-only")
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-1", name="seed"
    )
    _warning_plan("700001", condominium=base.condominium)
    _critical_plan("700002", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")

    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_OVERDUE_RISK
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_PARCELAMENTO_LOST
        ).count()
        == 1
    )


@freeze_time(FROZEN)
def test_idempotent_same_day_no_duplicate() -> None:
    """Rodar o comando 2x no mesmo dia SP → não cria Notification duplicada."""
    admin = _make_admin("admin-idem")
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-2", name="seed"
    )
    _warning_plan("800001", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")
        call_command("send_finance_alerts")

    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_OVERDUE_RISK
        ).count()
        == 1
    )


@freeze_time(FROZEN)
def test_critical_not_suppressed_by_prior_warning_same_day() -> None:
    """WARNING já enviado hoje não impede o CRITICAL (tipo distinto) no mesmo dia."""
    admin = _make_admin("admin-escalate")
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-3", name="seed"
    )
    _warning_plan("900001", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")  # only WARNING exists so far

    # A plan escalates to CRITICAL later the same day.
    _critical_plan("900002", condominium=base.condominium)
    with _no_push():
        call_command("send_finance_alerts")

    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_OVERDUE_RISK
        ).count()
        == 1
    )
    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_PARCELAMENTO_LOST
        ).count()
        == 1
    )


@freeze_time(FROZEN)
def test_no_admins_no_notifications() -> None:
    """Sem usuário is_staff/is_active → 0 Notifications, comando não falha."""
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-4", name="seed"
    )
    _warning_plan("100001", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")

    assert Notification.objects.count() == 0


@freeze_time(FROZEN)
def test_no_iptu_risk_no_notifications() -> None:
    """Sem planos em risco → 0 Notifications."""
    _make_admin("admin-quiet")

    with _no_push():
        call_command("send_finance_alerts")

    assert Notification.objects.count() == 0


@freeze_time(FROZEN)
def test_push_failure_does_not_drop_in_app_notification() -> None:
    """Boundary de push levantando exceção → a Notification in-app AINDA é persistida
    (push best-effort dentro de create_notification)."""
    admin = _make_admin("admin-pushfail")
    # Give the admin a device token so the Expo path actually runs (and then fails).
    from core.models import DeviceToken

    DeviceToken.objects.create(user=admin, token="ExponentPushToken[xxx]", is_active=True)
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-5", name="seed"
    )
    _warning_plan("110001", condominium=base.condominium)

    with patch(
        "core.services.notification_service.http_requests.post",
        side_effect=http_requests.RequestException("boom"),
    ):
        call_command("send_finance_alerts")

    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_OVERDUE_RISK
        ).count()
        == 1
    )


@freeze_time(FROZEN)
def test_no_device_token_still_creates_notification() -> None:
    """Admin sem DeviceToken/WebPushSubscription → Notification criada (push no-op, banner intacto)."""
    admin = _make_admin("admin-notoken")
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-6", name="seed"
    )
    _warning_plan("120001", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")

    assert (
        Notification.objects.filter(
            recipient=admin, type=Notification.TYPE_IPTU_OVERDUE_RISK
        ).count()
        == 1
    )


@freeze_time(FROZEN)
def test_only_staff_active_admins_notified() -> None:
    """is_staff=False ou is_active=False → não recebe; só staff ativo."""
    staff_active = _make_admin("staff-active")
    _make_admin("not-staff", is_staff=False)
    _make_admin("not-active", is_active=False)
    base = make_billing_account(
        account_type=BillingAccountType.IPTU, external_identifier="seed-7", name="seed"
    )
    _warning_plan("130001", condominium=base.condominium)

    with _no_push():
        call_command("send_finance_alerts")

    recipients = set(
        Notification.objects.filter(type=Notification.TYPE_IPTU_OVERDUE_RISK).values_list(
            "recipient_id", flat=True
        )
    )
    assert recipients == {staff_active.pk}
