"""
Notification service for push and in-app notifications.

Handles creating Notification records and dispatching push notifications
to tenant and admin devices via the Expo Push API.
"""

import logging

import requests as http_requests
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import DeviceToken, Notification, PaymentProof

logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_EXPO_REQUEST_TIMEOUT = 10


def create_notification(
    recipient: User,
    notification_type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    """
    Create a Notification record and dispatch a push notification.

    Always persists the notification to the database, then attempts
    to send via Expo Push API if the user has active device tokens.
    """
    notif = Notification.objects.create(
        recipient=recipient,
        type=notification_type,
        title=title,
        body=body,
        sent_at=timezone.now(),
        data=data,
    )
    send_push_notification(recipient, title, body, data)
    return notif


def send_push_notification(
    user: User,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """
    Dispatch push notifications to all active devices for the user.

    Makes a single batch request to the Expo Push API.
    Failures are logged and silently ignored — the notification is
    already persisted in the database.
    """
    push_ids = list(
        DeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    )
    if not push_ids:
        return

    messages = [
        {"to": push_id, "title": title, "body": body, "data": data or {}, "sound": "default"}
        for push_id in push_ids
    ]

    try:
        http_requests.post(
            _EXPO_PUSH_URL,
            json=messages,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=_EXPO_REQUEST_TIMEOUT,
        )
    except http_requests.RequestException:
        logger.warning("Failed to send push notification to user %s", user.pk)


def is_notification_sent_today(user: User, notification_type: str) -> bool:
    """Check whether a notification of the given type was already sent today."""
    today = timezone.now().date()
    return Notification.objects.filter(
        recipient=user, type=notification_type, sent_at__date=today
    ).exists()


def notify_new_proof(proof: PaymentProof) -> None:
    """Notify all admin users that a tenant submitted a new payment proof."""
    admins = User.objects.filter(is_staff=True, is_active=True)
    tenant_name = proof.lease.responsible_tenant.name
    apt = proof.lease.apartment
    for admin_user in admins:
        create_notification(
            recipient=admin_user,
            notification_type="new_proof",
            title="Novo comprovante",
            body=f"{tenant_name} enviou comprovante para apto {apt.number} ({proof.reference_month:%m/%Y})",
            data={"screen": "proofs", "proof_id": proof.pk},
        )


def notify_proof_reviewed(proof: PaymentProof) -> None:
    """Notify the responsible tenant that their proof was approved or rejected."""
    tenant = proof.lease.responsible_tenant
    if not tenant.user:
        return
    if proof.status == "approved":
        create_notification(
            recipient=tenant.user,
            notification_type="proof_approved",
            title="Comprovante aprovado",
            body=f"Seu comprovante de {proof.reference_month:%m/%Y} foi aprovado.",
            data={"screen": "payments"},
        )
    elif proof.status == "rejected":
        reason = proof.rejection_reason or "Motivo não informado"
        create_notification(
            recipient=tenant.user,
            notification_type="proof_rejected",
            title="Comprovante rejeitado",
            body=f"Seu comprovante de {proof.reference_month:%m/%Y} foi rejeitado: {reason}",
            data={"screen": "payments"},
        )
