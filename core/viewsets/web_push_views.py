"""
Web Push (VAPID) subscription endpoints.

Provides endpoints for browser PWA clients to fetch the VAPID public key and
to subscribe/unsubscribe their push endpoint for web push notifications.
"""

from typing import cast

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import WebPushSubscription


def _as_str(value: object) -> str:
    """Coerce request data to a trimmed string (non-strings/None -> '')."""
    return value.strip() if isinstance(value, str) else ""


class WebPushViewSet(ViewSet):
    """ViewSet for managing browser Web Push subscriptions."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="vapid-public-key")
    def vapid_public_key(self, request: Request) -> Response:
        """
        GET /api/web-push/vapid-public-key/

        Return the VAPID public key the browser uses to subscribe.
        """
        return Response({"publicKey": settings.VAPID_PUBLIC_KEY})

    @action(detail=False, methods=["post"], url_path="subscribe")
    def subscribe(self, request: Request) -> Response:
        """
        POST /api/web-push/subscribe/

        Register or update a Web Push subscription for the user.
        Body: {"endpoint": "...", "keys": {"p256dh": "...", "auth": "..."}}
        """
        endpoint = _as_str(request.data.get("endpoint"))
        keys_raw = request.data.get("keys")
        keys = keys_raw if isinstance(keys_raw, dict) else {}
        p256dh = _as_str(keys.get("p256dh"))
        auth = _as_str(keys.get("auth"))

        if not endpoint or not p256dh or not auth:
            return Response(
                {"error": "endpoint e keys (p256dh, auth) são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authenticated_user = cast(User, request.user)
        sub, created = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": authenticated_user,
                "p256dh": p256dh,
                "auth": auth,
                "is_active": True,
                "updated_by": authenticated_user,
            },
            create_defaults={
                "user": authenticated_user,
                "p256dh": p256dh,
                "auth": auth,
                "is_active": True,
                "created_by": authenticated_user,
                "updated_by": authenticated_user,
            },
        )
        return Response(
            {"id": sub.pk, "endpoint": sub.endpoint},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unsubscribe")
    def unsubscribe(self, request: Request) -> Response:
        """
        POST /api/web-push/unsubscribe/

        Deactivate a Web Push subscription so it no longer receives notifications.
        Body: {"endpoint": "..."}
        """
        endpoint = _as_str(request.data.get("endpoint"))
        if not endpoint:
            return Response(
                {"error": "endpoint é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = WebPushSubscription.objects.filter(
            endpoint=endpoint, user=cast(User, request.user)
        ).update(is_active=False)
        if updated == 0:
            return Response(
                {"error": "Inscrição não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"message": "Inscrição removida"})
