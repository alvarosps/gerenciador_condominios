"""URL routing for the condominium-finance API (mounted at /api/finances/)."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from finances.viewsets import (
    BillingAccountViewSet,
    BillSkipViewSet,
    BillViewSet,
    CategoryViewSet,
    EmployeeViewSet,
    FinanceDashboardViewSet,
    InstallmentPlanViewSet,
    InstallmentViewSet,
    PaymentViewSet,
)

# SimpleRouter (not DefaultRouter): a JSON API needs no format-suffix routes, and a second
# DefaultRouter would re-register the drf_format_suffix URL converter (Django 6 warning).
router = SimpleRouter()
router.register(r"finance-categories", CategoryViewSet, basename="finance-categories")
router.register(r"billing-accounts", BillingAccountViewSet, basename="billing-accounts")
router.register(r"bills", BillViewSet, basename="bills")
router.register(r"bill-skips", BillSkipViewSet, basename="bill-skips")
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"installment-plans", InstallmentPlanViewSet, basename="finance-installment-plans")
router.register(r"installments", InstallmentViewSet, basename="finance-installments")
router.register(r"employees", EmployeeViewSet, basename="finance-employees")
router.register(r"finance-dashboard", FinanceDashboardViewSet, basename="finance-dashboard")

urlpatterns = [path("", include(router.urls))]
