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
    EmployeePaymentViewSet,
    ExpenseCategoryViewSet,
    ExpenseInstallmentViewSet,
    ExpenseViewSet,
    FinancialDashboardViewSet,
    FinancialSettingsViewSet,
    IncomeViewSet,
    LandlordViewSet,
    PersonIncomeViewSet,
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

urlpatterns = [
    path("api/", include(router.urls)),
]
