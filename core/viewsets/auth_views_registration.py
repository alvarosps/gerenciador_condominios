"""
Registration and logout views.

Endpoints:
    POST /api/auth/register/ — create user account, return JWT tokens + user info
    POST /api/auth/logout/   — blacklist refresh token, return 204
"""

import logging
from typing import cast

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, Token

from core.throttles import AuthRateThrottle

logger = logging.getLogger(__name__)
User = get_user_model()

_EMAIL_DUPLICATE_MSG = "Um usuário com este email já existe."
_PASSWORDS_MISMATCH_MSG = "As senhas não conferem."
_REFRESH_REQUIRED_MSG = "Este campo é obrigatório."


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_EMAIL_DUPLICATE_MSG)
        return value.lower()

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": _PASSWORDS_MISMATCH_MSG})
        return attrs


class RegisterView(APIView):
    """
    Create a new user account and return JWT tokens.

    POST /api/auth/register/

    Body: { email, password, password2, first_name, last_name }

    Returns 201 with { access, refresh, user: { id, email, first_name, last_name, is_staff } }
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            is_staff=False,
        )

        refresh = RefreshToken.for_user(user)
        logger.info("New user registered: email=%s pk=%s", user.email, user.pk)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.pk,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """
    Blacklist the provided refresh token.

    POST /api/auth/logout/

    Body: { refresh: "<refresh_token>" }

    Returns 204 on success.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        refresh_token: str = request.data.get("refresh", "")
        if not refresh_token:
            return Response(
                {"refresh": _REFRESH_REQUIRED_MSG},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # RefreshToken.__init__ accepts str at runtime; stubs incorrectly type it as Token
            token = RefreshToken(cast(Token, refresh_token))
            token.blacklist()
        except TokenError as exc:
            return Response({"refresh": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("User logged out: pk=%s", request.user.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
