# core/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApartmentViewSet,
    BuildingViewSet,
    DashboardViewSet,
    FurnitureViewSet,
    LeaseViewSet,
    TenantViewSet,
)
from .viewsets import (
    CashFlowViewSet,
    ContractRuleViewSet,
    ContractTemplateViewSet,
    CreditCardViewSet,
    DailyControlViewSet,
    EmployeePaymentViewSet,
    ExpenseCategoryViewSet,
    ExpenseInstallmentViewSet,
    ExpenseMonthSkipViewSet,
    ExpenseViewSet,
    FinancialDashboardViewSet,
    FinancialSettingsViewSet,
    IncomeViewSet,
    LandlordViewSet,
    MonthAdvanceViewSet,
    PersonIncomeViewSet,
    PersonPaymentScheduleViewSet,
    PersonPaymentViewSet,
    PersonViewSet,
    RentPaymentViewSet,
)
from .viewsets.auth_views import SetPasswordViewSet, WhatsAppAuthViewSet
from .viewsets.tenant_views import TenantViewSet as TenantPortalViewSet

router = DefaultRouter()
router.register(r"buildings", BuildingViewSet)
router.register(r"furnitures", FurnitureViewSet)
router.register(r"apartments", ApartmentViewSet)
router.register(r"tenants", TenantViewSet)
router.register(r"leases", LeaseViewSet)
router.register(r"dashboard", DashboardViewSet, basename="dashboard")  # Phase 7
router.register(
    r"templates", ContractTemplateViewSet, basename="templates"
)  # Contract template management
router.register(r"landlords", LandlordViewSet, basename="landlords")  # Landlord configuration
router.register(r"rules", ContractRuleViewSet, basename="rules")  # Contract rule management
router.register(r"persons", PersonViewSet, basename="persons")
router.register(r"credit-cards", CreditCardViewSet, basename="credit-cards")
router.register(r"expense-categories", ExpenseCategoryViewSet, basename="expense-categories")
router.register(r"financial-settings", FinancialSettingsViewSet, basename="financial-settings")
router.register(r"expenses", ExpenseViewSet, basename="expenses")
router.register(r"expense-installments", ExpenseInstallmentViewSet, basename="expense-installments")
router.register(r"incomes", IncomeViewSet, basename="incomes")
router.register(r"rent-payments", RentPaymentViewSet, basename="rent-payments")
router.register(r"employee-payments", EmployeePaymentViewSet, basename="employee-payments")
router.register(r"person-incomes", PersonIncomeViewSet, basename="person-incomes")
router.register(r"person-payments", PersonPaymentViewSet, basename="person-payments")
router.register(r"financial-dashboard", FinancialDashboardViewSet, basename="financial-dashboard")
router.register(r"cash-flow", CashFlowViewSet, basename="cash-flow")
router.register(r"daily-control", DailyControlViewSet, basename="daily-control")
router.register(
    r"person-payment-schedules", PersonPaymentScheduleViewSet, basename="person-payment-schedules"
)
router.register(r"expense-month-skips", ExpenseMonthSkipViewSet, basename="expense-month-skips")
router.register(r"month-advance", MonthAdvanceViewSet, basename="month-advance")

_whatsapp_auth = WhatsAppAuthViewSet.as_view({"post": "request_code"})
_whatsapp_verify = WhatsAppAuthViewSet.as_view({"post": "verify_code"})
_set_password = SetPasswordViewSet.as_view({"post": "set_password"})

# Tenant portal — manual URLs to avoid router conflicts with existing TenantViewSet

_tenant_me = TenantPortalViewSet.as_view({"get": "me"})
_tenant_contract = TenantPortalViewSet.as_view({"get": "contract"})
_tenant_payments = TenantPortalViewSet.as_view({"get": "payments"})
_tenant_adjustments = TenantPortalViewSet.as_view({"get": "rent_adjustments"})
_tenant_pix = TenantPortalViewSet.as_view({"post": "payments_pix"})
_tenant_proof_upload = TenantPortalViewSet.as_view({"post": "payments_proof_upload"})
_tenant_proof_status = TenantPortalViewSet.as_view({"get": "payments_proof_status"})
_tenant_simulate = TenantPortalViewSet.as_view({"post": "due_date_simulate"})
_tenant_notifications = TenantPortalViewSet.as_view({"get": "notifications"})
_tenant_notif_read = TenantPortalViewSet.as_view({"patch": "notification_mark_read"})
_tenant_notif_read_all = TenantPortalViewSet.as_view({"post": "notifications_read_all"})

urlpatterns = [
    # Auth
    path("api/auth/whatsapp/request/", _whatsapp_auth, name="whatsapp-request"),
    path("api/auth/whatsapp/verify/", _whatsapp_verify, name="whatsapp-verify"),
    path("api/auth/set-password/", _set_password, name="set-password"),
    # Tenant portal
    path("api/tenant/me/", _tenant_me, name="tenant-me"),
    path("api/tenant/contract/", _tenant_contract, name="tenant-contract"),
    path("api/tenant/payments/", _tenant_payments, name="tenant-payments"),
    path("api/tenant/rent-adjustments/", _tenant_adjustments, name="tenant-adjustments"),
    path("api/tenant/payments/pix/", _tenant_pix, name="tenant-pix"),
    path("api/tenant/payments/proof/", _tenant_proof_upload, name="tenant-proof-upload"),
    path(
        "api/tenant/payments/proof/<int:proof_id>/",
        _tenant_proof_status,
        name="tenant-proof-status",
    ),
    path("api/tenant/due-date/simulate/", _tenant_simulate, name="tenant-simulate"),
    path("api/tenant/notifications/", _tenant_notifications, name="tenant-notifications"),
    path(
        "api/tenant/notifications/<int:notification_id>/read/",
        _tenant_notif_read,
        name="tenant-notif-read",
    ),
    path(
        "api/tenant/notifications/read-all/",
        _tenant_notif_read_all,
        name="tenant-notif-read-all",
    ),
    # API router
    path("api/", include(router.urls)),
]
