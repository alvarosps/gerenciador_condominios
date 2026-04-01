"""
Device token management endpoints.

Provides endpoints for mobile clients to register and unregister
Expo push notification tokens.
"""

from typing import cast

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import DeviceToken

_VALID_PLATFORMS = ("ios", "android")


class DeviceTokenViewSet(ViewSet):
    """ViewSet for registering and unregistering device push tokens."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="register")
    def register_token(self, request: Request) -> Response:
        """
        POST /api/devices/register/

        Register or update a device token for push notifications.
        Body: {"token": "ExpoToken[...]", "platform": "ios"|"android"}
        """
        token = request.data.get("token", "").strip()
        platform = request.data.get("platform", "").strip()

        if not token or not platform:
            return Response(
                {"error": "token e platform são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if platform not in _VALID_PLATFORMS:
            return Response(
                {"error": "platform deve ser 'ios' ou 'android'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authenticated_user = cast(User, request.user)
        device, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": authenticated_user,
                "platform": platform,
                "is_active": True,
                "updated_by": authenticated_user,
            },
            create_defaults={
                "created_by": authenticated_user,
            },
        )
        return Response(
            {"id": device.pk, "token": device.token, "platform": device.platform},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unregister")
    def unregister_token(self, request: Request) -> Response:
        """
        POST /api/devices/unregister/

        Deactivate a device token so it no longer receives push notifications.
        Body: {"token": "ExpoToken[...]"}
        """
        token = request.data.get("token", "").strip()
        if not token:
            return Response(
                {"error": "token é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = DeviceToken.objects.filter(token=token, user=cast(User, request.user)).update(
            is_active=False
        )
        if updated == 0:
            return Response(
                {"error": "Token não encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"message": "Token removido"})
