"""
Service layer for Condomínios Manager.

This package contains business logic services separated from the HTTP layer:
- FeeCalculatorService: Fee calculations (late fees, due date changes, tag fees)
- DateCalculatorService: Date calculations with edge case handling
- ContractService: Contract generation and PDF creation
- DashboardService: Financial metrics and operational statistics (Phase 7)
- TemplateManagementService: Contract template CRUD operations (Phase 6)
"""

from .base import BaseService
from .contract_service import ContractService
from .dashboard_service import DashboardService
from .date_calculator import DateCalculatorService
from .fee_calculator import FeeCalculatorService
from .template_management_service import TemplateManagementService

__all__ = [
    "FeeCalculatorService",
    "DateCalculatorService",
    "ContractService",
    "DashboardService",
    "TemplateManagementService",
    "BaseService",
]
