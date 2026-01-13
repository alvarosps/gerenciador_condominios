# core/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApartmentViewSet, BuildingViewSet, DashboardViewSet, FurnitureViewSet, LeaseViewSet, TenantViewSet
from .viewsets.template_views import ContractTemplateViewSet

router = DefaultRouter()
router.register(r"buildings", BuildingViewSet)
router.register(r"furnitures", FurnitureViewSet)
router.register(r"apartments", ApartmentViewSet)
router.register(r"tenants", TenantViewSet)
router.register(r"leases", LeaseViewSet)
router.register(r"dashboard", DashboardViewSet, basename="dashboard")  # Phase 7
router.register(r"templates", ContractTemplateViewSet, basename="templates")  # Contract template management

urlpatterns = [
    path("api/", include(router.urls)),
]
