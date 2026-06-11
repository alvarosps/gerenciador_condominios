"""
Service layer for Condomínios Manager.

This package contains business logic services separated from the HTTP layer:
- FeeCalculatorService: Fee calculations (late fees, due date changes, tag fees)
- DateCalculatorService: Date calculations with edge case handling
- ContractService: Contract generation and PDF creation
- DashboardService: Financial metrics and operational statistics (Phase 7)
- TemplateManagementService: Contract template CRUD operations (Phase 6)
- MonthAdvanceService: Month advancement orchestration (validate, snapshot, prepare next month)

The shared sandboxed Jinja environment factory lives at ``core.jinja_environment`` (peer of
``models``/``utils``), not here, because both the model and service layers consume it.
"""

from .base import BaseService
from .contract_service import ContractService
from .dashboard_service import DashboardService
from .date_calculator import DateCalculatorService
from .fee_calculator import FeeCalculatorService
from .month_advance_service import MonthAdvanceService
from .template_management_service import TemplateManagementService

__all__ = [
    "BaseService",
    "ContractService",
    "DashboardService",
    "DateCalculatorService",
    "FeeCalculatorService",
    "MonthAdvanceService",
    "TemplateManagementService",
]
