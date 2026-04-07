"""
Authentication Views

Custom views for handling OAuth and JWT integration.
Provides OAuth callback handler that issues JWT tokens after successful Google OAuth.
"""

import logging
from typing import Any

from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import OAuthExchangeCode
from core.viewsets.auth_views_cookie import _set_auth_cookies

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request: Request) -> Response:
    """Return the authenticated user's profile."""
    user = request.user
    if not user.is_authenticated:
        return Response({"error": "Authentication required"}, status=401)
    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }
    )


def get_tokens_for_user(user: Any) -> dict[str, str]:
    """
    Generate JWT tokens (access and refresh) for a given user.

    Args:
        user: Django User instance

    Returns:
        dict: Dictionary with 'refresh' and 'access' tokens
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class GoogleOAuthCallbackView:
    """
    Custom OAuth callback handler that issues JWT tokens after successful Google OAuth.

    Uses a one-time exchange code pattern instead of passing tokens in URL parameters.
    """

    @staticmethod
    def handle_callback(request: Request) -> Any:
        """
        Handle the OAuth callback and issue JWT tokens via one-time code exchange.

        Args:
            request: Django request object with authenticated user

        Returns:
            HttpResponseRedirect: Redirect to frontend with exchange code
        """
        if not request.user.is_authenticated:
            logger.warning("OAuth callback called but user is not authenticated")
            error_url = f"{settings.FRONTEND_URL}?error=oauth_failed"
            return redirect(error_url)

        try:
            # Generate JWT tokens for the authenticated user
            tokens = get_tokens_for_user(request.user)

            logger.info(
                f"User '{request.user.username}' (ID: {request.user.id}) logged in via Google OAuth"
            )

            # Create one-time exchange code instead of passing tokens in URL
            from core.models import OAuthExchangeCode

            exchange = OAuthExchangeCode.objects.create(
                user=request.user,
                access_token=str(tokens["access"]),
                refresh_token=str(tokens["refresh"]),
            )

            redirect_url = (
                f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}"
                f"?code={exchange.code}"
            )
            return redirect(redirect_url)

        except Exception:
            logger.exception("Error generating JWT tokens for OAuth user")
            error_url = f"{settings.FRONTEND_URL}?error=token_generation_failed"
            return redirect(error_url)


@api_view(["GET"])
@permission_classes([AllowAny])
def google_oauth_callback(request: Request) -> Any:
    """
    Endpoint for Google OAuth callback.

    URL: /api/auth/oauth/google/callback/
    Method: GET
    """
    return GoogleOAuthCallbackView.handle_callback(request)


@api_view(["POST"])
@permission_classes([AllowAny])
def exchange_oauth_code(request: Request) -> Response:
    """
    Exchange a one-time OAuth code for HttpOnly cookie tokens.

    URL: /api/auth/oauth/exchange/
    Method: POST
    Body: { "code": "uuid" }
    """

    code = request.data.get("code")
    if not code:
        return Response({"error": "Code is required"}, status=400)

    try:
        exchange = OAuthExchangeCode.objects.get(code=code)
    except (OAuthExchangeCode.DoesNotExist, ValueError):
        return Response({"error": "Invalid or expired code"}, status=400)

    if not exchange.is_valid():
        return Response({"error": "Invalid or expired code"}, status=400)

    exchange.is_used = True
    exchange.save(update_fields=["is_used"])

    user = exchange.user
    response = Response(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            },
        }
    )
    _set_auth_cookies(response, exchange.access_token, exchange.refresh_token)
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def link_oauth_account(request: Request) -> JsonResponse:
    """
    Manually link a Google account to an existing Django user by email.

    URL: /api/auth/oauth/link/
    Method: POST
    Body: { "email": "user@example.com" }
    """
    email = request.data.get("email")

    if not email:
        return JsonResponse({"error": "Email is required"}, status=400)

    try:
        user = User.objects.get(email=email)
        google_account = SocialAccount.objects.filter(user=user, provider="google").first()

        if google_account:
            return JsonResponse(
                {"success": True, "message": "Google account already linked", "user_id": user.id}
            )

        return JsonResponse(
            {
                "success": True,
                "message": "User found, ready to link Google account",
                "user_id": user.id,
            }
        )

    except User.DoesNotExist:
        return JsonResponse({"error": "User with this email does not exist"}, status=404)
    except Exception:
        logger.exception("Error linking OAuth account")
        return JsonResponse({"error": "Failed to link account"}, status=500)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def oauth_status(request: Request) -> JsonResponse:
    """
    Check OAuth configuration status. Admin only.

    URL: /api/auth/oauth/status/
    Method: GET
    """
    google_client_id = (
        getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
        .get("google", {})
        .get("APP", {})
        .get("client_id", "")
    )
    google_client_secret = (
        getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
        .get("google", {})
        .get("APP", {})
        .get("secret", "")
    )

    return JsonResponse(
        {
            "google_oauth_configured": bool(google_client_id and google_client_secret),
            "google_client_id_present": bool(google_client_id),
            "google_client_secret_present": bool(google_client_secret),
            "frontend_url": settings.FRONTEND_URL,
            "oauth_callback_path": settings.FRONTEND_AUTH_CALLBACK_PATH,
            "site_id": settings.SITE_ID,
        }
    )
