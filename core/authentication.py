"""Cookie-based JWT authentication backend."""

from typing import Any

from django.http import HttpRequest, HttpResponse
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate using JWT from HttpOnly cookies, falling back to Authorization header.

    The Authorization header path (mobile, server-to-server) is exempt from CSRF — a bearer
    token is never sent automatically by a browser, so it cannot be forged cross-site. The
    cookie path IS sent automatically by the browser, so it requires the same CSRF check DRF's
    SessionAuthentication performs, or a malicious site could ride the user's cookie.
    """

    def authenticate(self, request: Request) -> tuple[Any, Token] | None:
        # Try standard Authorization header first (get_header returns None or a non-empty header)
        header = self.get_header(request)
        if header:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # Fall back to cookie
        raw_token_str = request.COOKIES.get("access_token")
        if raw_token_str is None:
            return None

        validated_token = self.get_validated_token(raw_token_str.encode())
        user = self.get_user(validated_token)
        self.enforce_csrf(request)
        return user, validated_token

    def enforce_csrf(self, request: Request) -> None:
        """Run DRF's standard CSRF check for the cookie-authenticated path.

        Mirrors rest_framework.authentication.SessionAuthentication.enforce_csrf.
        """

        def dummy_get_response(request: HttpRequest) -> HttpResponse:  # pragma: no cover
            msg = "dummy_get_response is never actually called by process_request/process_view"
            raise NotImplementedError(msg)

        def dummy_callback(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            # pragma: no cover — CsrfViewMiddleware never invokes the callback itself; it only
            # inspects it (e.g. the csrf_exempt marker), so this is never actually called.
            msg = "dummy_callback is never actually called by process_view"
            raise NotImplementedError(msg)

        check = CSRFCheck(dummy_get_response)
        # populates request.META['CSRF_COOKIE'], which is used in process_view()
        check.process_request(request)
        reason = check.process_view(request, dummy_callback, (), {})
        if reason:
            detail = f"CSRF Failed: {reason}"
            raise exceptions.PermissionDenied(detail)
