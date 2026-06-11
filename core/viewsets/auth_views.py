"""
Tenant authentication views.

Provides WhatsApp-based OTP authentication for tenants and a set-password
endpoint for administrators.

Endpoints:
    POST /api/auth/whatsapp/request/ — request a verification code
    POST /api/auth/whatsapp/verify/  — verify the code and receive JWT tokens
    POST /api/auth/set-password/     — set password on the authenticated user (admin only)
"""

import logging
from datetime import timedelta
from typing import cast

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Tenant, WhatsAppVerification
from core.permissions import IsAdminUser
from core.services.whatsapp_service import (
    generate_verification_code,
    normalize_phone_to_e164,
    send_verification_code,
)
from core.throttles import VerificationRateThrottle

logger = logging.getLogger(__name__)

_CODE_EXPIRY_MINUTES = 5
_RATE_LIMIT_WINDOW_MINUTES = 15
_RATE_LIMIT_MAX_REQUESTS = 3
_MAX_VERIFY_ATTEMPTS = 3

# Generic, identical responses that never reveal whether a CPF/CNPJ belongs to a tenant.
_GENERIC_REQUEST_DETAIL = "Se o CPF/CNPJ estiver cadastrado, um código foi enviado via WhatsApp."
_GENERIC_VERIFY_ERROR = "Código inválido."


class WhatsAppAuthViewSet(viewsets.ViewSet):
    """
    ViewSet for WhatsApp-based OTP tenant authentication.

    All endpoints are public (AllowAny) because the caller is not yet
    authenticated when requesting or verifying a code.
    """

    permission_classes = [AllowAny]
    throttle_classes = [VerificationRateThrottle]

    @action(detail=False, methods=["post"], url_path="request")
    def request_code(self, request: Request) -> Response:
        """
        Send a 6-digit OTP to the tenant's WhatsApp.

        POST /api/auth/whatsapp/request/

        Body:
            cpf_cnpj (str): Tenant's CPF or CNPJ.

        Returns:
            200 with a generic message whether or not a tenant matches (no enumeration).
            400 if cpf_cnpj is missing.
            429 if the rate limit has been exceeded (3 codes in 15 minutes).
        """
        cpf_cnpj: str = request.data.get("cpf_cnpj", "").strip()
        if not cpf_cnpj:
            return Response({"error": "cpf_cnpj é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        tenant = Tenant.objects.filter(cpf_cnpj=cpf_cnpj).first()

        # Always respond identically so a caller cannot tell whether the CPF/CNPJ is a tenant.
        if tenant is None:
            logger.info("Verification code requested for unknown cpf_cnpj=%s", cpf_cnpj)
            return Response({"detail": _GENERIC_REQUEST_DETAIL}, status=status.HTTP_200_OK)

        window_start = timezone.now() - timedelta(minutes=_RATE_LIMIT_WINDOW_MINUTES)
        recent_count = WhatsAppVerification.objects.filter(
            cpf_cnpj=cpf_cnpj,
            created_at__gte=window_start,
        ).count()

        if recent_count >= _RATE_LIMIT_MAX_REQUESTS:
            return Response(
                {"error": "Muitas solicitações. Tente novamente em 15 minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = generate_verification_code()
        phone = normalize_phone_to_e164(tenant.phone)
        expires_at = timezone.now() + timedelta(minutes=_CODE_EXPIRY_MINUTES)

        WhatsAppVerification.objects.create(
            cpf_cnpj=cpf_cnpj,
            code=code,
            phone=phone,
            expires_at=expires_at,
        )

        send_verification_code(phone, code)
        logger.info("Verification code requested for cpf_cnpj=%s", cpf_cnpj)

        return Response({"detail": _GENERIC_REQUEST_DETAIL}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="verify")
    def verify_code(self, request: Request) -> Response:
        """
        Verify the OTP and return JWT tokens.

        POST /api/auth/whatsapp/verify/

        Body:
            cpf_cnpj (str): Tenant's CPF or CNPJ.
            code (str): The 6-digit OTP received via WhatsApp.

        Returns:
            200 with {access, refresh} on success.
            400 with a generic "Código inválido." for an unknown CPF/CNPJ, a missing pending
                verification, or a wrong code (no enumeration).
        """
        cpf_cnpj: str = request.data.get("cpf_cnpj", "").strip()
        code: str = request.data.get("code", "").strip()

        if not cpf_cnpj or not code:
            return Response(
                {"error": "cpf_cnpj e code são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Unknown CPF/CNPJ must be indistinguishable from a wrong code (no tenant enumeration).
        tenant = Tenant.objects.filter(cpf_cnpj=cpf_cnpj).first()
        if tenant is None:
            return Response({"error": _GENERIC_VERIFY_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            verification = (
                WhatsAppVerification.objects.select_for_update()
                .filter(cpf_cnpj=cpf_cnpj, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if verification is None:
                return Response(
                    {"error": _GENERIC_VERIFY_ERROR},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if verification.attempts >= _MAX_VERIFY_ATTEMPTS:
                return Response(
                    {"error": "Código bloqueado por excesso de tentativas. Solicite um novo."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            if not verification.is_valid:
                return Response(
                    {"error": "Código expirado ou esgotado. Solicite um novo código."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if verification.code != code:
                verification.attempts += 1
                verification.save(update_fields=["attempts"])
                return Response(
                    {"error": _GENERIC_VERIFY_ERROR}, status=status.HTTP_400_BAD_REQUEST
                )

            verification.is_used = True
            verification.save(update_fields=["is_used"])

            if tenant.user is None:
                user = User.objects.create_user(
                    username=f"tenant_{tenant.pk}",
                    is_staff=False,
                    is_active=True,
                )
                tenant.user = user
                tenant.save(update_fields=["user"])
                logger.info("Created user account for tenant pk=%s", tenant.pk)

        refresh = RefreshToken.for_user(tenant.user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class SetPasswordViewSet(viewsets.ViewSet):
    """
    ViewSet for setting a password on the authenticated admin user.

    Permission: IsAdminUser only.

    Registered via a manual URL in core/urls.py to avoid conflicts with the
    existing JWT auth routes registered in condominios_manager/urls.py.
    """

    permission_classes = [IsAdminUser]

    def set_password(self, request: Request) -> Response:
        """
        Set a new password on the currently authenticated user.

        POST /api/auth/set-password/

        Body:
            password (str): New password — validated against AUTH_PASSWORD_VALIDATORS.

        Returns:
            200 on success.
            400 if the password is missing or fails Django's password validators.
        """
        password: str = request.data.get("password", "")
        user = cast(User, request.user)

        if not password:
            return Response(
                {"error": "A senha é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            return Response(
                {"error": " ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(password)
        user.save(update_fields=["password"])
        logger.info("Password updated for user pk=%s", user.pk)

        return Response({"detail": "Senha atualizada com sucesso."}, status=status.HTTP_200_OK)
