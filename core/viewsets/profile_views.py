"""
User profile management views.

Endpoints:
    PATCH /api/auth/me/update/ — update first_name / last_name
    POST  /api/auth/change-password/ — change password (validates old password)
"""

import logging
from typing import cast

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_MIN_PASSWORD_LENGTH = 8


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request: Request) -> Response:
    """
    Update the authenticated user's first_name and last_name.

    PATCH /api/auth/me/update/

    Body (all optional):
        first_name (str)
        last_name  (str)

    Returns:
        200 with updated profile fields.
        400 if no valid field is provided.
    """
    user = cast(User, request.user)

    first_name: str | None = request.data.get("first_name")
    last_name: str | None = request.data.get("last_name")

    if first_name is None and last_name is None:
        return Response(
            {"error": "Nenhum campo para atualizar foi enviado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    update_fields: list[str] = []

    if first_name is not None:
        user.first_name = str(first_name)
        update_fields.append("first_name")

    if last_name is not None:
        user.last_name = str(last_name)
        update_fields.append("last_name")

    user.save(update_fields=update_fields)
    logger.info("Profile updated for user pk=%s fields=%s", user.pk, update_fields)

    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request: Request) -> Response:
    """
    Change the authenticated user's password.

    POST /api/auth/change-password/

    Body:
        old_password (str): Current password for verification.
        new_password (str): New password (minimum 8 characters).

    Returns:
        200 on success.
        400 if old_password is wrong or new_password is too short.
    """
    user = cast(User, request.user)

    old_password: str = request.data.get("old_password", "")
    new_password: str = request.data.get("new_password", "")

    if not old_password or not new_password:
        return Response(
            {"error": "old_password e new_password são obrigatórios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not user.check_password(old_password):
        return Response(
            {"error": "Senha atual incorreta."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < _MIN_PASSWORD_LENGTH:
        return Response(
            {"error": "A nova senha deve ter no mínimo 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])
    logger.info("Password changed for user pk=%s", user.pk)

    return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
