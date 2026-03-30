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

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Tenant, WhatsAppVerification
from core.permissions import IsAdminUser
from core.services.whatsapp_service import (
    generate_verification_code,
    normalize_phone_to_e164,
    send_verification_code,
)

logger = logging.getLogger(__name__)

User = get_user_model()

_CODE_EXPIRY_MINUTES = 5
_RATE_LIMIT_WINDOW_MINUTES = 15
_RATE_LIMIT_MAX_REQUESTS = 3
_MAX_VERIFY_ATTEMPTS = 3
_MIN_PASSWORD_LENGTH = 8


class WhatsAppAuthViewSet(viewsets.ViewSet):
    """
    ViewSet for WhatsApp-based OTP tenant authentication.

    All endpoints are public (AllowAny) because the caller is not yet
    authenticated when requesting or verifying a code.
    """

    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="request")
    def request_code(self, request):
        """
        Send a 6-digit OTP to the tenant's WhatsApp.

        POST /api/auth/whatsapp/request/

        Body:
            cpf_cnpj (str): Tenant's CPF or CNPJ.

        Returns:
            200 on success.
            404 if no tenant matches the CPF/CNPJ.
            429 if the rate limit has been exceeded (3 codes in 15 minutes).
        """
        cpf_cnpj: str = request.data.get("cpf_cnpj", "").strip()
        if not cpf_cnpj:
            return Response({"error": "cpf_cnpj é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant = Tenant.objects.get(cpf_cnpj=cpf_cnpj)
        except Tenant.DoesNotExist:
            return Response({"error": "Inquilino não encontrado"}, status=status.HTTP_404_NOT_FOUND)

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

        return Response({"detail": "Código enviado via WhatsApp."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="verify")
    def verify_code(self, request):
        """
        Verify the OTP and return JWT tokens.

        POST /api/auth/whatsapp/verify/

        Body:
            cpf_cnpj (str): Tenant's CPF or CNPJ.
            code (str): The 6-digit OTP received via WhatsApp.

        Returns:
            200 with {access, refresh} on success.
            400 if the code is wrong, expired, or exhausted.
            404 if no tenant or no pending verification found.
        """
        cpf_cnpj: str = request.data.get("cpf_cnpj", "").strip()
        code: str = request.data.get("code", "").strip()

        if not cpf_cnpj or not code:
            return Response(
                {"error": "cpf_cnpj e code são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(cpf_cnpj=cpf_cnpj)
        except Tenant.DoesNotExist:
            return Response({"error": "Inquilino não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        verification = (
            WhatsAppVerification.objects.filter(cpf_cnpj=cpf_cnpj, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if verification is None:
            return Response(
                {"error": "Nenhuma verificação pendente encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not verification.is_valid:
            return Response(
                {"error": "Código expirado ou esgotado. Solicite um novo código."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            return Response({"error": "Código inválido."}, status=status.HTTP_400_BAD_REQUEST)

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

    def set_password(self, request):
        """
        Set a new password on the currently authenticated user.

        POST /api/auth/set-password/

        Body:
            password (str): New password (minimum 8 characters).

        Returns:
            200 on success.
            400 if the password is too short or missing.
        """
        password: str = request.data.get("password", "")
        if len(password) < _MIN_PASSWORD_LENGTH:
            return Response(
                {"error": "A senha deve ter no mínimo 8 caracteres."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(password)
        request.user.save(update_fields=["password"])
        logger.info("Password updated for user pk=%s", request.user.pk)

        return Response({"detail": "Senha atualizada com sucesso."}, status=status.HTTP_200_OK)
