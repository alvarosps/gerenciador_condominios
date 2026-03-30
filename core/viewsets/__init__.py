# core/viewsets/__init__.py
"""
Additional ViewSets package for the core application.

This package contains ViewSets that have been extracted from views.py
for better separation of concerns:
- template_views: Contract template management endpoints
- landlord_views: Landlord (LOCADOR) configuration endpoints
- rule_views: Contract rule management endpoints
"""

from .financial_dashboard_views import (
    CashFlowViewSet,
    DailyControlViewSet,
    FinancialDashboardViewSet,
)
from .financial_views import (
    CreditCardViewSet,
    EmployeePaymentViewSet,
    ExpenseCategoryViewSet,
    ExpenseInstallmentViewSet,
    ExpenseMonthSkipViewSet,
    ExpenseViewSet,
    FinancialSettingsViewSet,
    IncomeViewSet,
    PersonIncomeViewSet,
    PersonPaymentScheduleViewSet,
    PersonPaymentViewSet,
    PersonViewSet,
    RentPaymentViewSet,
)
from .landlord_views import LandlordViewSet
from .month_advance_views import MonthAdvanceViewSet
from .proof_views import AdminProofViewSet
from .rule_views import ContractRuleViewSet
from .template_views import ContractTemplateViewSet

__all__ = [
    "AdminProofViewSet",
    "CashFlowViewSet",
    "ContractRuleViewSet",
    "ContractTemplateViewSet",
    "CreditCardViewSet",
    "DailyControlViewSet",
    "EmployeePaymentViewSet",
    "ExpenseCategoryViewSet",
    "ExpenseInstallmentViewSet",
    "ExpenseMonthSkipViewSet",
    "ExpenseViewSet",
    "FinancialDashboardViewSet",
    "FinancialSettingsViewSet",
    "IncomeViewSet",
    "LandlordViewSet",
    "MonthAdvanceViewSet",
    "PersonIncomeViewSet",
    "PersonPaymentScheduleViewSet",
    "PersonPaymentViewSet",
    "PersonViewSet",
    "RentPaymentViewSet",
]
