"""Token views that set HttpOnly cookies."""

import logging
from typing import Any, Literal, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, Token
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

logger = logging.getLogger(__name__)

User = get_user_model()

ACCESS_TOKEN_MAX_AGE = 60 * 60  # 1 hour
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
COOKIE_SAMESITE: Literal["Lax"] = "Lax"


def _set_auth_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    is_secure = not settings.DEBUG
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=is_secure,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
    )
    if refresh is not None:
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            secure=is_secure,
            samesite=COOKIE_SAMESITE,
            max_age=REFRESH_TOKEN_MAX_AGE,
            path="/",
        )
    response.set_cookie(
        key="is_authenticated",
        value="1",
        httponly=False,
        secure=is_secure,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in ("access_token", "refresh_token", "is_authenticated"):
        response.delete_cookie(name, path="/", samesite=COOKIE_SAMESITE)


class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access_token_str = response.data["access"]
            _set_auth_cookies(response, access_token_str, response.data["refresh"])
            token = AccessToken(access_token_str)
            user = User.objects.get(pk=token["user_id"])
            response.data = {
                "user": {
                    "id": user.pk,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,
                },
            }
        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Inject refresh token from cookie into request data when not already provided.
        refresh_from_cookie = request.COOKIES.get("refresh_token")
        if refresh_from_cookie and "refresh" not in request.data:
            # Build a mutable copy with the cookie value so the parent serializer sees it.
            data = dict(request.data)
            data["refresh"] = refresh_from_cookie
            serializer = self.get_serializer(data=data)
            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as exc:
                raise InvalidToken(exc.args[0]) from exc
            access = serializer.validated_data.get("access", "")
            new_refresh = serializer.validated_data.get("refresh")
            response = Response(status=status.HTTP_200_OK)
            _set_auth_cookies(response, access, new_refresh)
            response.data = {}
            return response

        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            access = response.data.get("access", "")
            new_refresh = response.data.get("refresh")
            _set_auth_cookies(response, access, new_refresh)
            response.data = {}
        return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cookie_logout(request: Request) -> Response:
    refresh_token = request.COOKIES.get("refresh_token")
    if refresh_token:
        try:
            token = RefreshToken(cast(Token, refresh_token))
            token.blacklist()
        except TokenError as exc:
            logger.warning("Could not blacklist refresh token on logout: %s", exc)
    response = Response(status=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response
