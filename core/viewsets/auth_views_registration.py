"""
Registration view.

Endpoints:
    POST /api/auth/register/ — create user account, set HttpOnly cookies, return user info
"""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.throttles import AuthRateThrottle
from core.viewsets.auth_views_cookie import _set_auth_cookies

logger = logging.getLogger(__name__)
User = get_user_model()

_EMAIL_DUPLICATE_MSG = "Um usuário com este email já existe."
_PASSWORDS_MISMATCH_MSG = "As senhas não conferem."


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
    Create a new user account, set HttpOnly auth cookies, and return user info.

    POST /api/auth/register/

    Body: { email, password, password2, first_name, last_name }

    Returns 201 with { user: { id, email, first_name, last_name, is_staff } }
    Tokens are set as HttpOnly cookies (access_token, refresh_token, is_authenticated).
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

        response = Response(
            {
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
        _set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response
