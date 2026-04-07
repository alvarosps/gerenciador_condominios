"""
URL configuration for condominios_manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from core.auth import (
    current_user,
    exchange_oauth_code,
    google_oauth_callback,
    link_oauth_account,
    oauth_status,
)
from core.throttles import AuthRateThrottle
from core.views import task_status
from core.viewsets.auth_views_cookie import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    cookie_logout,
)
from core.viewsets.auth_views_registration import RegisterView


class ThrottledTokenObtainPairView(CookieTokenObtainPairView):
    throttle_classes = [AuthRateThrottle]


class ThrottledTokenRefreshView(CookieTokenRefreshView):
    throttle_classes = [AuthRateThrottle]


urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # Async task status
    path("api/tasks/<str:task_id>/status/", task_status, name="task_status"),
    # JWT Authentication endpoints
    path("api/auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    # Current user profile
    path("api/auth/me/", current_user, name="current_user"),
    # Registration and logout
    path("api/auth/register/", RegisterView.as_view(), name="auth_register"),
    path("api/auth/logout/", cookie_logout, name="auth_logout"),
    # Custom OAuth endpoints
    path("api/auth/oauth/google/callback/", google_oauth_callback, name="google_oauth_callback"),
    path("api/auth/oauth/exchange/", exchange_oauth_code, name="exchange_oauth_code"),
    path("api/auth/oauth/link/", link_oauth_account, name="link_oauth_account"),
    path("api/auth/oauth/status/", oauth_status, name="oauth_status"),
    # Django-allauth OAuth endpoints (Google OAuth)
    path("accounts/", include("allauth.urls")),
    # Core API endpoints
    path("", include("core.urls")),
]

# API docs and schema only in development
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

# Serve media files (contracts) in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
