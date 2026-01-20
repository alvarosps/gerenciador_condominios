# core/viewsets/__init__.py
"""
Additional ViewSets package for the core application.

This package contains ViewSets that have been extracted from views.py
for better separation of concerns:
- template_views: Contract template management endpoints
- landlord_views: Landlord (LOCADOR) configuration endpoints
- rule_views: Contract rule management endpoints
"""

from .landlord_views import LandlordViewSet
from .rule_views import ContractRuleViewSet
from .template_views import ContractTemplateViewSet

__all__ = ["ContractTemplateViewSet", "ContractRuleViewSet", "LandlordViewSet"]
