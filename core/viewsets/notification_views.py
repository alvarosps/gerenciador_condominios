"""
Admin notification endpoints.

Provides admin-only endpoints for listing, reading, and bulk-reading notifications.
Mirrors the tenant notification endpoints but with IsAdminUser permission.
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import Notification
from core.pagination import CustomPageNumberPagination
from core.permissions import IsAdminUser
from core.serializers import NotificationSerializer


class AdminNotificationViewSet(ViewSet):
    """Admin notification management."""

    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        queryset = Notification.objects.filter(recipient=request.user).order_by("-sent_at")
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request: Request, pk: int = None) -> Response:
        try:
            notif = Notification.objects.get(pk=pk, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notificação não encontrada"}, status=status.HTTP_404_NOT_FOUND
            )
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = timezone.now()
            notif.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request: Request) -> Response:
        count = Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"marked_read": count})
