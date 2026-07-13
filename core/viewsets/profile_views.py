"""
User profile management views.

Endpoints:
    PATCH /api/auth/me/update/ — update first_name / last_name / phone (tenants only)
    POST  /api/auth/change-password/ — change password (validates old password)
"""

import logging
from typing import cast

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from core.services.whatsapp_service import normalize_phone_to_e164

logger = logging.getLogger(__name__)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request: Request) -> Response:
    """
    Update the authenticated user's first_name / last_name, and — for tenants — phone.

    PATCH /api/auth/me/update/

    Body (all optional):
        first_name (str)
        last_name  (str)
        phone (str): The tenant's WhatsApp/OTP channel. Only applies to a user with a
            linked ``tenant_profile``; normalized to E.164 before saving on the Tenant.

    Returns:
        200 with updated profile fields.
        400 if no valid field is provided, or phone is sent by a non-tenant user or fails
            E.164 normalization.
    """
    user = cast(User, request.user)

    first_name: str | None = request.data.get("first_name")
    last_name: str | None = request.data.get("last_name")
    phone: str | None = request.data.get("phone")

    if first_name is None and last_name is None and phone is None:
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

    if phone is not None:
        tenant = getattr(user, "tenant_profile", None)
        if tenant is None:
            return Response(
                {"error": "Apenas inquilinos podem atualizar o telefone."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            normalized_phone = normalize_phone_to_e164(str(phone))
        except ValueError:
            return Response(
                {"error": "Telefone inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tenant.phone = normalized_phone
        tenant.save(update_fields=["phone"])

    if update_fields:
        user.save(update_fields=update_fields)
    logger.info(
        "Profile updated for user pk=%s fields=%s phone_updated=%s",
        user.pk,
        update_fields,
        phone is not None,
    )

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
        new_password (str): New password — validated against AUTH_PASSWORD_VALIDATORS.

    Returns:
        200 on success.
        400 if old_password is wrong or new_password fails Django's password validators.
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

    try:
        validate_password(new_password, user)
    except DjangoValidationError as exc:
        return Response(
            {"error": " ".join(exc.messages)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save(update_fields=["password"])
    logger.info("Password changed for user pk=%s", user.pk)

    return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
