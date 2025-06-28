# core/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import BuildingViewSet, FurnitureViewSet, ApartmentViewSet, TenantViewSet, LeaseViewSet

router = DefaultRouter()
router.register(r'buildings', BuildingViewSet)
router.register(r'furnitures', FurnitureViewSet)
router.register(r'apartments', ApartmentViewSet)
router.register(r'tenants', TenantViewSet)
router.register(r'leases', LeaseViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
