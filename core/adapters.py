"""Allauth adapters.

Custom social-account adapter that promotes allowlisted Google accounts to admin
(is_staff + is_superuser) on signup and on every subsequent login, keeping them in
sync. It only ever promotes; it never demotes, so manually-promoted users are safe.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest


class AdminAllowlistSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Promote allowlisted Google emails to staff/superuser. Never demotes."""

    def apply_admin_allowlist(self, user: AbstractUser) -> bool:
        """Promote the user to admin if their email is allowlisted.

        Returns True if any flag was changed, False otherwise. Only ever sets flags
        to True — non-allowlisted or already-correct users are left untouched.
        """
        email = (user.email or "").strip().lower()
        if not email:
            return False

        allowlist = {entry.strip().lower() for entry in settings.ADMIN_GOOGLE_EMAILS}
        if email not in allowlist:
            return False

        changed = False
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        return changed

    def save_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        form: object | None = None,
    ) -> AbstractUser:
        """Persist a newly signed-up social user, promoting it if allowlisted."""
        user: AbstractUser = super().save_user(request, sociallogin, form)
        if self.apply_admin_allowlist(user):
            user.save(update_fields=["is_staff", "is_superuser"])
        return user

    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        """Keep existing allowlisted users in sync on every login."""
        super().pre_social_login(request, sociallogin)
        if sociallogin.is_existing and self.apply_admin_allowlist(sociallogin.user):
            sociallogin.user.save(update_fields=["is_staff", "is_superuser"])
