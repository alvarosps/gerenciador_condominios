"""Cookie-based JWT authentication backend."""

from typing import Any

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate using JWT from HttpOnly cookies, falling back to Authorization header."""

    def authenticate(self, request: Request) -> tuple[Any, Token] | None:
        # Try standard Authorization header first
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # Fall back to cookie
        raw_token_str = request.COOKIES.get("access_token")
        if raw_token_str is None:
            return None

        validated_token = self.get_validated_token(raw_token_str.encode())
        return self.get_user(validated_token), validated_token
