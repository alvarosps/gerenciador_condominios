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

from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from core.auth import google_oauth_callback, link_oauth_account, oauth_status

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # JWT Authentication endpoints
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # API Documentation (Phase 8: OpenAPI/Swagger)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Custom OAuth endpoints
    path("api/auth/oauth/google/callback/", google_oauth_callback, name="google_oauth_callback"),
    path("api/auth/oauth/link/", link_oauth_account, name="link_oauth_account"),
    path("api/auth/oauth/status/", oauth_status, name="oauth_status"),
    # Django-allauth OAuth endpoints (Google OAuth)
    path("accounts/", include("allauth.urls")),
    # Core API endpoints
    path("", include("core.urls")),
]
