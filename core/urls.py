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
from .viewsets.auth_views import SetPasswordViewSet, WhatsAppAuthViewSet

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

urlpatterns = [
    path("api/auth/whatsapp/request/", _whatsapp_auth, name="whatsapp-request"),
    path("api/auth/whatsapp/verify/", _whatsapp_verify, name="whatsapp-verify"),
    path("api/auth/set-password/", _set_password, name="set-password"),
    path("api/", include(router.urls)),
]
