# core/viewsets/__init__.py
"""
Additional ViewSets package for the core application.

This package contains ViewSets that have been extracted from views.py
for better separation of concerns:
- template_views: Contract template management endpoints
- landlord_views: Landlord (LOCADOR) configuration endpoints
- rule_views: Contract rule management endpoints
"""

from .financial_dashboard_views import CashFlowViewSet, FinancialDashboardViewSet
from .financial_views import (
    CreditCardViewSet,
    EmployeePaymentViewSet,
    ExpenseCategoryViewSet,
    ExpenseInstallmentViewSet,
    ExpenseViewSet,
    FinancialSettingsViewSet,
    IncomeViewSet,
    PersonIncomeViewSet,
    PersonViewSet,
    RentPaymentViewSet,
)
from .landlord_views import LandlordViewSet
from .rule_views import ContractRuleViewSet
from .template_views import ContractTemplateViewSet

__all__ = [
    "CashFlowViewSet",
    "ContractRuleViewSet",
    "ContractTemplateViewSet",
    "CreditCardViewSet",
    "EmployeePaymentViewSet",
    "ExpenseCategoryViewSet",
    "ExpenseInstallmentViewSet",
    "ExpenseViewSet",
    "FinancialDashboardViewSet",
    "FinancialSettingsViewSet",
    "IncomeViewSet",
    "LandlordViewSet",
    "PersonIncomeViewSet",
    "PersonViewSet",
    "RentPaymentViewSet",
]
