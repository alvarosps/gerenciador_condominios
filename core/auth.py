"""
Authentication Views

Custom views for handling OAuth and JWT integration.
Provides OAuth callback handler that issues JWT tokens after successful Google OAuth.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)
User = get_user_model()


def get_tokens_for_user(user):
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

    This view intercepts the OAuth callback, retrieves the authenticated user,
    generates JWT tokens, and redirects to the frontend with the tokens.

    Flow:
    1. User clicks "Login with Google" on frontend
    2. User is redirected to Google for authentication
    3. Google redirects back to /accounts/google/login/callback/
    4. Django-allauth processes the OAuth flow and authenticates the user
    5. This view generates JWT tokens for the authenticated user
    6. User is redirected to frontend with tokens in URL parameters

    Security Note:
    - Tokens in URL are visible in browser history
    - For production, consider using HTTP-only cookies or a more secure token delivery method
    - Current implementation is acceptable for development and can be upgraded later
    """

    @staticmethod
    def handle_callback(request):
        """
        Handle the OAuth callback and issue JWT tokens.

        Args:
            request: Django request object with authenticated user

        Returns:
            HttpResponseRedirect: Redirect to frontend with JWT tokens
        """
        if not request.user.is_authenticated:
            logger.warning("OAuth callback called but user is not authenticated")
            # Redirect to frontend with error
            error_url = f"{settings.FRONTEND_URL}?error=oauth_failed&message=Authentication failed"
            return redirect(error_url)

        try:
            # Generate JWT tokens for the authenticated user
            tokens = get_tokens_for_user(request.user)

            # Log the successful OAuth login
            logger.info(
                f"User '{request.user.username}' (ID: {request.user.id}) "
                f"logged in via Google OAuth and received JWT tokens"
            )

            # Check if this is a superuser (for logging)
            if request.user.is_superuser:
                logger.info(f"Superuser '{request.user.username}' logged in via OAuth")

            # Get user info for frontend
            user_info = {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "is_staff": request.user.is_staff,
                "is_superuser": request.user.is_superuser,
            }

            # Build the frontend redirect URL with tokens and user info
            params = {
                "access_token": tokens["access"],
                "refresh_token": tokens["refresh"],
                "user_id": user_info["id"],
                "username": user_info["username"],
                "email": user_info["email"],
                "is_staff": user_info["is_staff"],
                "is_superuser": user_info["is_superuser"],
            }

            # Construct the full redirect URL
            redirect_url = f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}?{urlencode(params)}"

            return redirect(redirect_url)

        except Exception as e:
            logger.error(f"Error generating JWT tokens for OAuth user: {str(e)}", exc_info=True)
            error_url = f"{settings.FRONTEND_URL}?error=token_generation_failed&message={str(e)}"
            return redirect(error_url)


@api_view(["GET"])
@permission_classes([AllowAny])
def google_oauth_callback(request):
    """
    Endpoint for Google OAuth callback.

    This endpoint is called by django-allauth after successful Google OAuth.
    It generates JWT tokens and redirects to the frontend.

    URL: /api/auth/oauth/google/callback/
    Method: GET

    Returns:
        HttpResponseRedirect: Redirect to frontend with JWT tokens
    """
    return GoogleOAuthCallbackView.handle_callback(request)


@api_view(["POST"])
@permission_classes([AllowAny])
def link_oauth_account(request):
    """
    Manually link a Google account to an existing Django user by email.

    This endpoint allows users to manually trigger the OAuth linking process.
    If a user with the OAuth email already exists, the accounts are linked.

    URL: /api/auth/oauth/link/
    Method: POST
    Body: { "email": "user@example.com" }

    Returns:
        JSON response with success status
    """
    email = request.data.get("email")

    if not email:
        return JsonResponse({"error": "Email is required"}, status=400)

    try:
        # Check if user with this email exists
        user = User.objects.get(email=email)

        # Check if user already has a Google account linked
        google_account = SocialAccount.objects.filter(user=user, provider="google").first()

        if google_account:
            return JsonResponse({"success": True, "message": "Google account already linked", "user_id": user.id})

        return JsonResponse(
            {
                "success": True,
                "message": "User found, ready to link Google account",
                "user_id": user.id,
            }
        )

    except User.DoesNotExist:
        return JsonResponse({"error": "User with this email does not exist"}, status=404)
    except Exception as e:
        logger.error(f"Error linking OAuth account: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Failed to link account", "message": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([AllowAny])
def oauth_status(request):
    """
    Check OAuth configuration status.

    This endpoint helps debug OAuth configuration by checking if:
    - Google OAuth credentials are configured
    - Required settings are present

    URL: /api/auth/oauth/status/
    Method: GET

    Returns:
        JSON response with configuration status
    """
    google_client_id = (
        getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("google", {}).get("APP", {}).get("client_id", "")
    )
    google_client_secret = (
        getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("google", {}).get("APP", {}).get("secret", "")
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
