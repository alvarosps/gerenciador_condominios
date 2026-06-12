"""Session 61 — is_notification_sent_on (SP-aware idempotency mirror, design §9.3).

is_notification_sent_today uses the UTC date (timezone.now().date()); the new
is_notification_sent_on receives the day from the caller (which passes today_sp()),
so the idempotency window can track the São Paulo midnight rollover, not UTC.
The function itself compares sent_at__date == day — the caller owns the SP date.
"""

from datetime import date

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from freezegun import freeze_time

from core.models import Notification
from core.services.notification_service import (
    create_notification,
    is_notification_sent_on,
)
from tests.constants import TEST_PASSWORD

pytestmark = pytest.mark.django_db


@pytest.fixture
def recipient() -> User:
    return User.objects.create_user(
        username="iptu-admin", email="iptu-admin@test.com", password=TEST_PASSWORD, is_staff=True
    )


@pytest.fixture
def other_user() -> User:
    return User.objects.create_user(
        username="other", email="other@test.com", password=TEST_PASSWORD, is_staff=True
    )


def _make_notification(user: User, notification_type: str, sent_at) -> Notification:
    return Notification.objects.create(
        recipient=user,
        type=notification_type,
        title="t",
        body="b",
        sent_at=sent_at,
    )


@freeze_time("2026-07-15 12:00:00")
def test_returns_false_when_none_sent(recipient: User) -> None:
    """Sem Notification do tipo no dia → False."""
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 15))
        is False
    )


@freeze_time("2026-07-15 12:00:00")
def test_returns_true_when_sent_on_that_day(recipient: User) -> None:
    """Notification criada hoje (sent_at no dia) → True para is_notification_sent_on(today)."""
    create_notification(
        recipient=recipient,
        notification_type=Notification.TYPE_IPTU_OVERDUE_RISK,
        title="t",
        body="b",
    )
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 15))
        is True
    )


@freeze_time("2026-07-15 12:00:00")
def test_scoped_by_type(recipient: User) -> None:
    """Notification de outro tipo no mesmo dia → False (filtra por type)."""
    create_notification(
        recipient=recipient,
        notification_type=Notification.TYPE_IPTU_PARCELAMENTO_LOST,
        title="t",
        body="b",
    )
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 15))
        is False
    )


@freeze_time("2026-07-15 12:00:00")
def test_scoped_by_user(recipient: User, other_user: User) -> None:
    """Notification para outro usuário → False (filtra por recipient)."""
    create_notification(
        recipient=other_user,
        notification_type=Notification.TYPE_IPTU_OVERDUE_RISK,
        title="t",
        body="b",
    )
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 15))
        is False
    )


def test_sp_aware_midnight_boundary(recipient: User) -> None:
    """sent_at numa data UTC X; is_notification_sent_on com day=X True, day=X-1/X+1 False
    (compara sent_at__date == day; o caller controla a data SP)."""
    sent_at = timezone.make_aware(
        timezone.datetime(2026, 7, 15, 13, 0, 0), timezone.get_current_timezone()
    )
    _make_notification(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, sent_at)

    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 15))
        is True
    )
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 14))
        is False
    )
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, date(2026, 7, 16))
        is False
    )


@freeze_time("2026-07-16 02:30:00")
def test_no_duplicate_digest_across_sp_midnight(recipient: User) -> None:
    """Regression: TIME_ZONE=UTC truncates sent_at__date in UTC. At 02:30 UTC (= 23:30 SP on
    2026-07-15) a digest sent NOW carries SP day 2026-07-15. A same-SP-day re-run
    (is_notification_sent_on(today_sp()=2026-07-15)) must detect it → no duplicate. A naive
    UTC sent_at__date=2026-07-15 lookup would miss it (the row's UTC date is 2026-07-16)."""
    from core.services.timezone import today_sp

    # The send happens NOW (02:30 UTC). today_sp() at this instant is the SP calendar day.
    assert today_sp() == date(2026, 7, 15)
    create_notification(
        recipient=recipient,
        notification_type=Notification.TYPE_IPTU_OVERDUE_RISK,
        title="t",
        body="b",
    )
    # The persisted sent_at is 2026-07-16 02:30 UTC (its UTC date is the 16th, SP date the 15th).
    notif = Notification.objects.get(recipient=recipient, type=Notification.TYPE_IPTU_OVERDUE_RISK)
    assert notif.sent_at.date() == date(2026, 7, 16)  # UTC date — would fool a naive lookup
    # Same-SP-day re-run must see it → idempotent (no duplicate digest near SP midnight).
    assert (
        is_notification_sent_on(recipient, Notification.TYPE_IPTU_OVERDUE_RISK, today_sp()) is True
    )
