# Architectural Analysis & Improvement Recommendations
## Condomínios Manager Backend

**Date:** 2025-10-19
**Current Version:** Django 5.0.2 + DRF 3.14.0
**Analysis Scope:** Backend architecture review and modernization recommendations

---

## Executive Summary

The current system implements a functional but monolithic MVT (Model-View-Template) pattern typical of Django applications. While operational, it exhibits several architectural antipatterns that will hinder scalability, maintainability, and testability as the system grows. This analysis recommends migrating to a **Layered Architecture with Domain-Driven Design (DDD) lite** approach, which provides a practical middle ground between simplicity and enterprise-grade structure.

**Key Issues Identified:**
- Business logic tightly coupled to ViewSets (100+ line methods)
- No service layer or domain logic separation
- Configuration hardcoded throughout the codebase
- Mixed concerns (PDF generation in API views)
- Limited testability and extensibility
- Poor separation between data access and business rules

**Recommended Approach:** Layered Architecture + DDD Lite
**Migration Effort:** Medium (2-3 weeks for core refactoring)
**Risk Level:** Low (can be done incrementally without breaking changes)

---

## 1. Current Architecture Assessment

### 1.1 Current Pattern: Django MVT (Model-View-Template)

```
┌─────────────────────────────────────────────────┐
│                  API Layer                       │
│  (ViewSets - REST Framework)                     │
│  ┌──────────────────────────────────────────┐   │
│  │ LeaseViewSet.generate_contract()         │   │
│  │   - Business Logic (100+ lines)          │   │
│  │   - Date calculations                     │   │
│  │   - Furniture logic                       │   │
│  │   - PDF generation                        │   │
│  │   - File system operations               │   │
│  │   - Template rendering                    │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│            Serialization Layer                   │
│  (DRF Serializers with nested logic)             │
│  - Read/Write field splitting                    │
│  - Nested object creation                        │
│  - Validation mixed with transformation          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              Data Layer (Models)                 │
│  - 6 Django ORM models in single file            │
│  - Minimal validation                            │
│  - No business rules                             │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│              PostgreSQL Database                 │
└─────────────────────────────────────────────────┘
```

### 1.2 File Structure Analysis

```
core/
├── models.py              (210 lines - Data models only)
├── serializers.py         (79 lines - Mixed concerns)
├── views.py               (198 lines - EVERYTHING: CRUD + Business Logic + PDF + Calculations)
├── urls.py                (16 lines - Routing)
├── utils.py               (11 lines - Formatting helpers)
├── contract_rules.py      (36 lines - Static data)
└── templates/
    └── contract_template.html
```

**Single App Problem:** All models, business logic, API, and utilities in one Django app (`core`).

### 1.3 Architectural Antipatterns Identified

#### **1.3.1 God Object (LeaseViewSet)**
The `LeaseViewSet` class violates Single Responsibility Principle by handling:
- HTTP request/response handling
- Date calculations with complex edge cases (leap year logic)
- Furniture set calculations
- PDF generation with async operations
- File system management
- Template rendering
- Business rule application (fee calculations)

**Lines 48-160 of views.py:** Single method doing everything.

#### **1.3.2 Hardcoded Configuration**
Multiple hardcoded values scattered throughout:
- Chrome executable path: `C:\Program Files\Google\Chrome\Application\chrome.exe` (line 121)
- Database credentials in settings.py (lines 82-86)
- Fee calculations: 5% late fee, 50/80 tag fees (lines 73, 173)
- Directory structures hardcoded (line 109)

#### **1.3.3 Anemic Domain Model**
Models contain almost zero business logic:
```python
class Lease(models.Model):
    # Only data fields, no methods
    # Business logic lives in views
```

**Problem:** Domain knowledge scattered across views instead of encapsulated in domain objects.

#### **1.3.4 Mixed Abstraction Levels**
`generate_contract` method mixes:
- High-level orchestration (what to do)
- Low-level implementation (how to do it)
- Infrastructure concerns (async, file I/O, browser automation)

#### **1.3.5 Tight Coupling**
- PDF generation tightly coupled to pyppeteer
- Views directly coupled to ORM models
- No dependency injection
- Impossible to swap implementations without code changes

#### **1.3.6 Limited Testability**
- Cannot unit test business logic without mocking Django ORM
- Cannot test PDF generation without actual Chrome
- No separation between pure logic and I/O operations

---

## 2. Recommended Architecture: Layered DDD Lite

### 2.1 Architecture Overview

```
┌───────────────────────────────────────────────────────────────┐
│                    API / Presentation Layer                    │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │   ViewSets      │  │   Serializers    │  │    DTOs      │ │
│  │ (Thin handlers) │  │ (Data transform) │  │  (Requests)  │ │
│  └─────────────────┘  └──────────────────┘  └──────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                    Application Layer                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                     Service Classes                       │ │
│  │  - LeaseService (orchestration)                          │ │
│  │  - ContractService (document generation)                 │ │
│  │  - FinancialService (fee calculations)                   │ │
│  │  - NotificationService (future)                          │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                      Domain Layer                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Domain Models (Rich objects)                 │ │
│  │  - Lease.calculate_late_fee()                            │ │
│  │  - Lease.change_due_date()                               │ │
│  │  - Lease.calculate_furniture_inventory()                 │ │
│  │  - Apartment.can_be_rented()                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  Domain Services                          │ │
│  │  - DateCalculationService (leap year logic)              │ │
│  │  - FeeCalculationEngine                                  │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │               Repository Interfaces                       │ │
│  │  - ILeaseRepository                                      │ │
│  │  - IDocumentRepository                                   │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Repository Implementations                   │ │
│  │  - DjangoLeaseRepository (ORM)                           │ │
│  │  - FileSystemDocumentRepository                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                External Integrations                      │ │
│  │  - PDFGenerator (pyppeteer/WeasyPrint)                  │ │
│  │  - TemplateEngine (Jinja2)                              │ │
│  │  - FileStorage (local/S3)                               │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│                      Data Layer                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  Django ORM Models                        │ │
│  │  (Persistence only - minimal business logic)             │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities

#### **API/Presentation Layer**
- HTTP request/response handling
- Authentication & Authorization
- Request validation (basic)
- Data serialization
- Error handling and response formatting
- **NO business logic**

#### **Application Layer (Services)**
- Use case orchestration
- Transaction boundaries
- Service coordination
- Application-specific workflows
- DTO transformations

#### **Domain Layer**
- Business rules and logic
- Domain entities with behavior
- Domain services (complex operations involving multiple entities)
- Repository interfaces (contracts)
- Domain events (future)

#### **Infrastructure Layer**
- Database access (ORM implementations)
- External service integrations
- File system operations
- Caching
- Logging
- Configuration management

---

## 3. Proposed App Structure

### 3.1 Recommended Django App Organization

```
condominios_manager/
├── apps/
│   ├── properties/                 # Property management bounded context
│   │   ├── __init__.py
│   │   ├── models.py               # Building, Apartment (ORM)
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py         # Rich domain models
│   │   │   ├── services.py         # Domain services
│   │   │   └── repositories.py     # Repository interfaces
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── services.py         # Application services
│   │   │   └── dtos.py             # Data transfer objects
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   └── repositories.py     # ORM repository implementations
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views.py            # ViewSets (thin)
│   │   │   ├── serializers.py      # DRF serializers
│   │   │   └── urls.py             # Routing
│   │   └── migrations/
│   │
│   ├── leases/                     # Lease management bounded context
│   │   ├── __init__.py
│   │   ├── models.py               # Lease (ORM)
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py         # Lease entity with business logic
│   │   │   ├── services.py         # DateCalculationService, FeeCalculationEngine
│   │   │   ├── repositories.py     # ILeaseRepository interface
│   │   │   └── value_objects.py    # DateRange, Money, etc.
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   ├── services.py         # LeaseService, ContractService
│   │   │   └── dtos.py             # CreateLeaseRequest, etc.
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   └── repositories.py     # DjangoLeaseRepository
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   └── migrations/
│   │
│   ├── tenants/                    # Tenant management bounded context
│   │   ├── __init__.py
│   │   ├── models.py               # Tenant, Dependent (ORM)
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py
│   │   │   ├── services.py
│   │   │   └── repositories.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   └── services.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   └── repositories.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   └── migrations/
│   │
│   ├── documents/                  # Document generation bounded context
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── generators.py       # Document generator interfaces
│   │   │   ├── templates.py        # Template management
│   │   │   └── repositories.py     # IDocumentRepository
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   └── services.py         # DocumentGenerationService
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_generators/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pyppeteer_generator.py
│   │   │   │   └── weasyprint_generator.py
│   │   │   ├── storage.py          # FileSystemStorage, S3Storage
│   │   │   └── repositories.py
│   │   ├── templates/
│   │   │   ├── contract_template.html
│   │   │   ├── receipt_template.html
│   │   │   └── notice_template.html
│   │   └── tests/
│   │
│   ├── finances/                   # Financial management (future)
│   │   ├── __init__.py
│   │   ├── models.py               # Payment, Expense, Invoice
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── entities.py
│   │   │   └── services.py
│   │   ├── application/
│   │   │   ├── __init__.py
│   │   │   └── services.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   └── repositories.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── views.py
│   │       ├── serializers.py
│   │       └── urls.py
│   │
│   └── shared/                     # Shared kernel
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── base_entity.py      # Base classes
│       │   ├── value_objects.py    # Common value objects (Money, CPF, etc.)
│       │   └── exceptions.py       # Domain exceptions
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── config.py           # Configuration management
│       │   ├── logging.py          # Logging setup
│       │   └── utils.py            # Shared utilities
│       └── api/
│           ├── __init__.py
│           ├── exceptions.py       # API exceptions
│           └── pagination.py       # Shared pagination
│
├── config/                         # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base settings
│   │   ├── development.py          # Dev-specific settings
│   │   ├── production.py           # Prod-specific settings
│   │   └── test.py                 # Test settings
│   ├── urls.py                     # Root URL configuration
│   └── wsgi.py
│
├── tests/                          # Integration & E2E tests
│   ├── __init__.py
│   ├── integration/
│   └── e2e/
│
├── scripts/                        # Management scripts
│   ├── seed_data.py
│   └── migrate_architecture.py
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   ├── production.txt
│   └── test.txt
│
├── manage.py
├── .env.example                    # Environment variables template
└── README.md
```

### 3.2 Bounded Contexts Rationale

**Properties** - Building and apartment management
- Relatively independent
- Different change drivers than leases
- Can be managed by different admins

**Leases** - Contract and rental management
- Core domain
- Complex business rules
- Frequent changes

**Tenants** - Tenant and dependent management
- Identity and contact management
- Can exist independently of leases

**Documents** - Document generation
- Infrastructure concern
- Reusable across contexts
- Can be swapped/upgraded independently

**Finances** - Payment and expense tracking (future)
- Natural extension
- Separate reporting requirements
- Different security/audit needs

**Shared** - Common code and utilities
- Shared value objects
- Base classes
- Cross-cutting concerns

---

## 4. Service Layer Design

### 4.1 Service Layer Patterns

#### **Application Services (Use Case Orchestration)**

**Responsibility:** Coordinate domain objects and infrastructure to fulfill use cases.

**Example: LeaseService**
```python
# apps/leases/application/services.py
from typing import Optional
from decimal import Decimal
from datetime import date
from django.db import transaction

from apps.leases.domain.entities import Lease
from apps.leases.domain.repositories import ILeaseRepository
from apps.properties.domain.repositories import IApartmentRepository
from apps.tenants.domain.repositories import ITenantRepository
from apps.documents.application.services import DocumentGenerationService
from apps.leases.application.dtos import (
    CreateLeaseRequest,
    LeaseResponse,
    ContractGenerationRequest
)


class LeaseService:
    """
    Application service for lease management.
    Orchestrates use cases involving leases.
    """

    def __init__(
        self,
        lease_repository: ILeaseRepository,
        apartment_repository: IApartmentRepository,
        tenant_repository: ITenantRepository,
        document_service: DocumentGenerationService
    ):
        self._lease_repo = lease_repository
        self._apartment_repo = apartment_repository
        self._tenant_repo = tenant_repository
        self._document_service = document_service

    @transaction.atomic
    def create_lease(self, request: CreateLeaseRequest) -> LeaseResponse:
        """
        Create a new lease.

        Workflow:
        1. Validate apartment availability
        2. Validate tenants
        3. Create lease domain entity
        4. Apply business rules
        5. Persist
        6. Return response
        """
        # Retrieve entities
        apartment = self._apartment_repo.get_by_id(request.apartment_id)
        if not apartment:
            raise ApartmentNotFoundError(request.apartment_id)

        if not apartment.can_be_rented():
            raise ApartmentNotAvailableError(apartment.id)

        responsible_tenant = self._tenant_repo.get_by_id(request.responsible_tenant_id)
        if not responsible_tenant:
            raise TenantNotFoundError(request.responsible_tenant_id)

        tenants = [self._tenant_repo.get_by_id(tid) for tid in request.tenant_ids]

        # Create domain entity (with business logic)
        lease = Lease.create(
            apartment=apartment,
            responsible_tenant=responsible_tenant,
            tenants=tenants,
            start_date=request.start_date,
            validity_months=request.validity_months,
            due_day=request.due_day,
            rental_value=request.rental_value,
            cleaning_fee=request.cleaning_fee,
            tag_fee=request.tag_fee or self._calculate_tag_fee(len(tenants))
        )

        # Persist
        saved_lease = self._lease_repo.save(lease)

        # Mark apartment as rented
        apartment.mark_as_rented(lease.start_date)
        self._apartment_repo.save(apartment)

        return LeaseResponse.from_entity(saved_lease)

    def generate_contract(self, lease_id: int) -> str:
        """
        Generate contract PDF for a lease.

        Returns: Path to generated PDF
        """
        lease = self._lease_repo.get_by_id(lease_id)
        if not lease:
            raise LeaseNotFoundError(lease_id)

        # Prepare contract data
        contract_request = ContractGenerationRequest(
            lease_id=lease.id,
            tenant=lease.responsible_tenant,
            apartment=lease.apartment,
            building=lease.apartment.building,
            furnitures=lease.calculate_furniture_inventory(),
            start_date=lease.start_date,
            final_date=lease.calculate_final_date(),
            next_month_date=lease.calculate_next_month_date(),
            rental_value=lease.rental_value,
            cleaning_fee=lease.cleaning_fee,
            tag_fee=lease.tag_fee,
            total_value=lease.calculate_total_value(),
            validity_months=lease.validity_months,
        )

        # Delegate to document service
        pdf_path = self._document_service.generate_contract(contract_request)

        # Update lease status
        lease.mark_contract_generated()
        self._lease_repo.save(lease)

        return pdf_path

    def calculate_late_fee(self, lease_id: int) -> Optional[Decimal]:
        """
        Calculate late fee for a lease based on current date.
        """
        lease = self._lease_repo.get_by_id(lease_id)
        if not lease:
            raise LeaseNotFoundError(lease_id)

        return lease.calculate_late_fee(date.today())

    @transaction.atomic
    def change_due_date(self, lease_id: int, new_due_day: int) -> Decimal:
        """
        Change the due date of a lease and calculate the fee.

        Returns: Fee charged for the change
        """
        lease = self._lease_repo.get_by_id(lease_id)
        if not lease:
            raise LeaseNotFoundError(lease_id)

        fee = lease.change_due_date(new_due_day)
        self._lease_repo.save(lease)

        return fee

    def _calculate_tag_fee(self, number_of_tenants: int) -> Decimal:
        """Calculate tag fee based on number of tenants."""
        return Decimal('50.00') if number_of_tenants == 1 else Decimal('80.00')
```

#### **Domain Services (Complex Business Logic)**

**Responsibility:** Encapsulate business logic that doesn't naturally belong to a single entity.

**Example: DateCalculationService**
```python
# apps/leases/domain/services.py
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class DateCalculationService:
    """
    Domain service for complex date calculations.
    Handles edge cases like leap years.
    """

    @staticmethod
    def calculate_final_date(start_date: date, validity_months: int) -> date:
        """
        Calculate the final date of a lease.

        Handles special case: Feb 29 start date
        If calculated end is Feb 28, move to March 1
        """
        calculated_final_date = start_date + relativedelta(months=validity_months)

        # Special case for leap year
        if start_date.month == 2 and start_date.day == 29:
            if calculated_final_date.month == 2 and calculated_final_date.day == 28:
                calculated_final_date = calculated_final_date + timedelta(days=1)

        return calculated_final_date

    @staticmethod
    def calculate_next_month_date(start_date: date) -> date:
        """Calculate the date one month after start date."""
        return start_date + relativedelta(months=1)

    @staticmethod
    def days_late(due_day: int, current_date: date) -> int:
        """
        Calculate how many days a payment is late.

        Returns 0 if not late.
        """
        if current_date.day <= due_day:
            return 0

        return current_date.day - due_day


class FeeCalculationEngine:
    """
    Domain service for fee calculations.
    Encapsulates fee calculation rules.
    """

    # Configuration (should come from settings in production)
    LATE_FEE_RATE = 0.05  # 5% per day
    DAYS_PER_MONTH = 30
    TAG_FEE_SINGLE = 50.00
    TAG_FEE_MULTIPLE = 80.00

    @classmethod
    def calculate_late_fee(
        cls,
        rental_value: Decimal,
        days_late: int
    ) -> Decimal:
        """
        Calculate late fee based on daily rate.

        Formula: (rental_value / 30) * days_late * 5%
        """
        if days_late <= 0:
            return Decimal('0.00')

        daily_rate = rental_value / Decimal(cls.DAYS_PER_MONTH)
        late_fee = daily_rate * Decimal(days_late) * Decimal(cls.LATE_FEE_RATE)

        return late_fee.quantize(Decimal('0.01'))

    @classmethod
    def calculate_due_date_change_fee(
        cls,
        rental_value: Decimal,
        current_due_day: int,
        new_due_day: int
    ) -> Decimal:
        """
        Calculate fee for changing due date.

        Formula: (rental_value / 30) * abs(day_difference)
        """
        days_difference = abs(new_due_day - current_due_day)
        daily_rate = rental_value / Decimal(cls.DAYS_PER_MONTH)
        fee = daily_rate * Decimal(days_difference)

        return fee.quantize(Decimal('0.01'))

    @classmethod
    def calculate_tag_fee(cls, number_of_tenants: int) -> Decimal:
        """Calculate tag deposit fee based on number of tenants."""
        if number_of_tenants == 1:
            return Decimal(str(cls.TAG_FEE_SINGLE))
        return Decimal(str(cls.TAG_FEE_MULTIPLE))
```

#### **Infrastructure Services (External Integrations)**

**Example: DocumentGenerationService**
```python
# apps/documents/application/services.py
from abc import ABC, abstractmethod
from typing import Protocol
from pathlib import Path

from apps.documents.domain.generators import IPDFGenerator
from apps.documents.infrastructure.storage import IDocumentStorage
from apps.leases.application.dtos import ContractGenerationRequest


class DocumentGenerationService:
    """
    Application service for document generation.
    Coordinates PDF generation and storage.
    """

    def __init__(
        self,
        pdf_generator: IPDFGenerator,
        document_storage: IDocumentStorage,
        template_engine: ITemplateEngine
    ):
        self._pdf_generator = pdf_generator
        self._storage = document_storage
        self._template_engine = template_engine

    def generate_contract(self, request: ContractGenerationRequest) -> str:
        """
        Generate a lease contract PDF.

        Returns: Path or URL to the generated document
        """
        # Prepare template context
        context = self._prepare_contract_context(request)

        # Render HTML from template
        html_content = self._template_engine.render(
            'contract_template.html',
            context
        )

        # Generate PDF
        pdf_bytes = self._pdf_generator.generate_from_html(html_content)

        # Store document
        filename = f"contract_apto_{request.apartment.number}_{request.lease_id}.pdf"
        path_pattern = f"contracts/{request.building.street_number}/{filename}"

        document_path = self._storage.save(
            path=path_pattern,
            content=pdf_bytes,
            content_type='application/pdf'
        )

        return document_path

    def _prepare_contract_context(self, request: ContractGenerationRequest) -> dict:
        """Prepare Jinja2 template context."""
        from apps.shared.infrastructure.formatters import format_currency, number_to_words
        from apps.documents.domain.content import get_condominium_rules

        return {
            'tenant': request.tenant,
            'building_number': request.building.street_number,
            'apartment_number': request.apartment.number,
            'furnitures': request.furnitures,
            'validity': request.validity_months,
            'start_date': request.start_date.strftime("%d/%m/%Y"),
            'final_date': request.final_date.strftime("%d/%m/%Y"),
            'next_month_date': request.next_month_date.strftime("%d/%m/%Y"),
            'rental_value': request.rental_value,
            'tag_fee': request.tag_fee,
            'cleaning_fee': request.cleaning_fee,
            'valor_total': request.total_value,
            'rules': get_condominium_rules(),
        }
```

### 4.2 Repository Pattern

**Interface Definition (Domain Layer)**
```python
# apps/leases/domain/repositories.py
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from apps.leases.domain.entities import Lease


class ILeaseRepository(ABC):
    """Repository interface for Lease aggregate."""

    @abstractmethod
    def get_by_id(self, lease_id: int) -> Optional[Lease]:
        """Retrieve a lease by ID."""
        pass

    @abstractmethod
    def save(self, lease: Lease) -> Lease:
        """Save or update a lease."""
        pass

    @abstractmethod
    def delete(self, lease_id: int) -> bool:
        """Delete a lease."""
        pass

    @abstractmethod
    def find_by_apartment(self, apartment_id: int) -> Optional[Lease]:
        """Find active lease for an apartment."""
        pass

    @abstractmethod
    def find_expiring_soon(self, days: int) -> List[Lease]:
        """Find leases expiring within specified days."""
        pass

    @abstractmethod
    def find_by_tenant(self, tenant_id: int) -> List[Lease]:
        """Find all leases for a tenant."""
        pass
```

**Implementation (Infrastructure Layer)**
```python
# apps/leases/infrastructure/repositories.py
from typing import Optional, List
from datetime import date, timedelta

from apps.leases.domain.entities import Lease as LeaseDomain
from apps.leases.domain.repositories import ILeaseRepository
from apps.leases.models import Lease as LeaseModel


class DjangoLeaseRepository(ILeaseRepository):
    """Django ORM implementation of lease repository."""

    def get_by_id(self, lease_id: int) -> Optional[LeaseDomain]:
        """Retrieve a lease by ID."""
        try:
            lease_model = LeaseModel.objects.select_related(
                'apartment__building',
                'responsible_tenant'
            ).prefetch_related(
                'tenants',
                'apartment__furnitures',
                'responsible_tenant__furnitures'
            ).get(id=lease_id)

            return self._to_domain(lease_model)
        except LeaseModel.DoesNotExist:
            return None

    def save(self, lease: LeaseDomain) -> LeaseDomain:
        """Save or update a lease."""
        if lease.id:
            # Update existing
            lease_model = LeaseModel.objects.get(id=lease.id)
            self._update_model_from_domain(lease_model, lease)
        else:
            # Create new
            lease_model = self._create_model_from_domain(lease)

        lease_model.save()

        # Update many-to-many relationships
        lease_model.tenants.set(lease.tenant_ids)

        return self._to_domain(lease_model)

    def delete(self, lease_id: int) -> bool:
        """Delete a lease."""
        try:
            LeaseModel.objects.filter(id=lease_id).delete()
            return True
        except Exception:
            return False

    def find_by_apartment(self, apartment_id: int) -> Optional[LeaseDomain]:
        """Find active lease for an apartment."""
        try:
            lease_model = LeaseModel.objects.select_related(
                'apartment__building',
                'responsible_tenant'
            ).prefetch_related('tenants').get(apartment_id=apartment_id)

            return self._to_domain(lease_model)
        except LeaseModel.DoesNotExist:
            return None

    def find_expiring_soon(self, days: int) -> List[LeaseDomain]:
        """Find leases expiring within specified days."""
        today = date.today()
        threshold = today + timedelta(days=days)

        lease_models = LeaseModel.objects.select_related(
            'apartment__building',
            'responsible_tenant'
        ).filter(
            start_date__lte=threshold
        ).prefetch_related('tenants')

        return [self._to_domain(lm) for lm in lease_models]

    def find_by_tenant(self, tenant_id: int) -> List[LeaseDomain]:
        """Find all leases for a tenant."""
        lease_models = LeaseModel.objects.select_related(
            'apartment__building',
            'responsible_tenant'
        ).filter(
            tenants__id=tenant_id
        ).prefetch_related('tenants')

        return [self._to_domain(lm) for lm in lease_models]

    # Mapping methods
    def _to_domain(self, model: LeaseModel) -> LeaseDomain:
        """Convert ORM model to domain entity."""
        # Implementation details...
        pass

    def _create_model_from_domain(self, domain: LeaseDomain) -> LeaseModel:
        """Create ORM model from domain entity."""
        # Implementation details...
        pass

    def _update_model_from_domain(
        self,
        model: LeaseModel,
        domain: LeaseDomain
    ) -> None:
        """Update ORM model from domain entity."""
        # Implementation details...
        pass
```

### 4.3 Dependency Injection

**Service Container Setup**
```python
# apps/shared/infrastructure/container.py
from dependency_injector import containers, providers

from apps.leases.application.services import LeaseService
from apps.leases.infrastructure.repositories import DjangoLeaseRepository
from apps.properties.infrastructure.repositories import DjangoApartmentRepository
from apps.tenants.infrastructure.repositories import DjangoTenantRepository
from apps.documents.application.services import DocumentGenerationService
from apps.documents.infrastructure.pdf_generators.pyppeteer_generator import PyppeteerPDFGenerator
from apps.documents.infrastructure.storage import FileSystemDocumentStorage
from apps.documents.infrastructure.template_engine import Jinja2TemplateEngine


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""

    config = providers.Configuration()

    # Repositories
    lease_repository = providers.Singleton(DjangoLeaseRepository)
    apartment_repository = providers.Singleton(DjangoApartmentRepository)
    tenant_repository = providers.Singleton(DjangoTenantRepository)

    # Infrastructure services
    pdf_generator = providers.Singleton(
        PyppeteerPDFGenerator,
        chrome_path=config.pdf.chrome_path
    )
    document_storage = providers.Singleton(
        FileSystemDocumentStorage,
        base_path=config.storage.contracts_path
    )
    template_engine = providers.Singleton(
        Jinja2TemplateEngine,
        template_dir=config.templates.path
    )

    # Application services
    document_service = providers.Singleton(
        DocumentGenerationService,
        pdf_generator=pdf_generator,
        document_storage=document_storage,
        template_engine=template_engine
    )

    lease_service = providers.Singleton(
        LeaseService,
        lease_repository=lease_repository,
        apartment_repository=apartment_repository,
        tenant_repository=tenant_repository,
        document_service=document_service
    )
```

**ViewSet Integration**
```python
# apps/leases/api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.shared.infrastructure.container import Container
from apps.leases.api.serializers import LeaseSerializer, CreateLeaseSerializer
from apps.leases.application.dtos import CreateLeaseRequest


class LeaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for lease management.
    Thin layer - delegates to service.
    """
    serializer_class = LeaseSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lease_service = Container.lease_service()

    def create(self, request):
        """Create a new lease."""
        serializer = CreateLeaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Convert to DTO
        dto = CreateLeaseRequest(**serializer.validated_data)

        # Delegate to service
        try:
            lease_response = self._lease_service.create_lease(dto)
            return Response(
                LeaseSerializer(lease_response).data,
                status=status.HTTP_201_CREATED
            )
        except ApartmentNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ApartmentNotAvailableError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        """Generate contract PDF for a lease."""
        try:
            pdf_path = self._lease_service.generate_contract(int(pk))
            return Response(
                {
                    'message': 'Contract generated successfully',
                    'pdf_path': pdf_path
                },
                status=status.HTTP_200_OK
            )
        except LeaseNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate contract: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def calculate_late_fee(self, request, pk=None):
        """Calculate late fee for a lease."""
        try:
            late_fee = self._lease_service.calculate_late_fee(int(pk))

            if late_fee and late_fee > 0:
                return Response(
                    {
                        'late_fee': str(late_fee),
                        'message': 'Payment is late'
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'message': 'Payment is not late'},
                    status=status.HTTP_200_OK
                )
        except LeaseNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def change_due_date(self, request, pk=None):
        """Change due date of a lease."""
        new_due_day = request.data.get('new_due_day')

        if not new_due_day:
            return Response(
                {'error': 'new_due_day is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fee = self._lease_service.change_due_date(
                lease_id=int(pk),
                new_due_day=int(new_due_day)
            )
            return Response(
                {
                    'message': 'Due date changed successfully',
                    'fee': str(fee)
                },
                status=status.HTTP_200_OK
            )
        except LeaseNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

---

## 5. Configuration Management

### 5.1 Environment-Based Configuration

**Current Problem:**
- Database credentials hardcoded in settings.py
- Chrome path hardcoded in views.py
- No distinction between dev/staging/prod environments

**Recommended Solution:**

#### **.env.example (template)**
```bash
# Environment
DJANGO_ENV=development  # development, staging, production

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=condominio
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# PDF Generation
PDF_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
PDF_TIMEOUT=30000

# Document Storage
STORAGE_TYPE=filesystem  # filesystem, s3
STORAGE_BASE_PATH=./contracts
# AWS_S3_BUCKET_NAME=your-bucket
# AWS_ACCESS_KEY_ID=your-key
# AWS_SECRET_ACCESS_KEY=your-secret

# Fee Configuration
FEE_LATE_RATE=0.05
FEE_TAG_SINGLE=50.00
FEE_TAG_MULTIPLE=80.00
FEE_DAYS_PER_MONTH=30

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log
```

#### **config/settings/base.py**
```python
"""Base settings shared across all environments."""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'corsheaders',
    'rest_framework',
    # Local apps
    'apps.properties',
    'apps.leases',
    'apps.tenants',
    'apps.documents',
    'apps.finances',
    'apps.shared',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Change for production
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# Application-specific settings
PDF_GENERATION = {
    'CHROME_PATH': config('PDF_CHROME_PATH', default=None),
    'TIMEOUT': config('PDF_TIMEOUT', default=30000, cast=int),
}

DOCUMENT_STORAGE = {
    'TYPE': config('STORAGE_TYPE', default='filesystem'),
    'BASE_PATH': config('STORAGE_BASE_PATH', default='./contracts'),
    'AWS_S3_BUCKET_NAME': config('AWS_S3_BUCKET_NAME', default=None),
}

FEE_CONFIGURATION = {
    'LATE_RATE': config('FEE_LATE_RATE', default=0.05, cast=float),
    'TAG_SINGLE': config('FEE_TAG_SINGLE', default=50.00, cast=float),
    'TAG_MULTIPLE': config('FEE_TAG_MULTIPLE', default=80.00, cast=float),
    'DAYS_PER_MONTH': config('FEE_DAYS_PER_MONTH', default=30, cast=int),
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': config('LOG_FILE_PATH', default='./logs/app.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

#### **config/settings/development.py**
```python
"""Development-specific settings."""
from .base import *

DEBUG = True

INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Disable password validation in development
AUTH_PASSWORD_VALIDATORS = []

# Development email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

#### **config/settings/production.py**
```python
"""Production-specific settings."""
from .base import *

DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Static and media files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging - use production-grade handlers
LOGGING['handlers']['sentry'] = {
    'level': 'ERROR',
    'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
}
```

#### **manage.py update**
```python
#!/usr/bin/env python
import os
import sys
from decouple import config

if __name__ == '__main__':
    # Load appropriate settings based on environment
    env = config('DJANGO_ENV', default='development')
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE',
        f'config.settings.{env}'
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)
```

### 5.2 Configuration Access Pattern

**Centralized Config Access**
```python
# apps/shared/infrastructure/config.py
from django.conf import settings
from typing import Any


class AppConfig:
    """Centralized configuration access."""

    @staticmethod
    def get_pdf_chrome_path() -> str:
        """Get Chrome executable path for PDF generation."""
        return settings.PDF_GENERATION.get('CHROME_PATH')

    @staticmethod
    def get_pdf_timeout() -> int:
        """Get PDF generation timeout in milliseconds."""
        return settings.PDF_GENERATION.get('TIMEOUT', 30000)

    @staticmethod
    def get_storage_type() -> str:
        """Get document storage type."""
        return settings.DOCUMENT_STORAGE.get('TYPE', 'filesystem')

    @staticmethod
    def get_contracts_base_path() -> str:
        """Get base path for contract storage."""
        return settings.DOCUMENT_STORAGE.get('BASE_PATH', './contracts')

    @staticmethod
    def get_late_fee_rate() -> float:
        """Get late payment fee rate."""
        return settings.FEE_CONFIGURATION.get('LATE_RATE', 0.05)

    @staticmethod
    def get_tag_fee_single() -> float:
        """Get tag fee for single tenant."""
        return settings.FEE_CONFIGURATION.get('TAG_SINGLE', 50.00)

    @staticmethod
    def get_tag_fee_multiple() -> float:
        """Get tag fee for multiple tenants."""
        return settings.FEE_CONFIGURATION.get('TAG_MULTIPLE', 80.00)
```

**Usage in Services**
```python
from apps.shared.infrastructure.config import AppConfig

class FeeCalculationEngine:
    @classmethod
    def calculate_late_fee(cls, rental_value: Decimal, days_late: int) -> Decimal:
        rate = AppConfig.get_late_fee_rate()
        # ... calculation logic
```

---

## 6. Scalability Considerations

### 6.1 Database Optimization

#### **Indexes**
```python
# apps/leases/models.py
class Lease(models.Model):
    # ... fields ...

    class Meta:
        indexes = [
            models.Index(fields=['apartment', 'start_date']),
            models.Index(fields=['responsible_tenant']),
            models.Index(fields=['start_date', 'validity_months']),  # For expiration queries
            models.Index(fields=['contract_generated', 'contract_signed']),  # For filtering
        ]
```

#### **Query Optimization**
```python
# Use select_related and prefetch_related
lease = Lease.objects.select_related(
    'apartment__building',
    'responsible_tenant'
).prefetch_related(
    'tenants',
    'apartment__furnitures',
    'responsible_tenant__furnitures'
).get(id=lease_id)
```

### 6.2 Caching Strategy

**Redis Caching Layer**
```python
# config/settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'condominios',
        'TIMEOUT': 300,
    }
}
```

**Service-Level Caching**
```python
# apps/leases/application/services.py
from django.core.cache import cache

class LeaseService:
    CACHE_TTL = 300  # 5 minutes

    def get_lease_summary(self, lease_id: int) -> dict:
        """Get cached lease summary."""
        cache_key = f'lease_summary_{lease_id}'

        cached = cache.get(cache_key)
        if cached:
            return cached

        # Fetch from database
        lease = self._lease_repo.get_by_id(lease_id)
        summary = lease.to_summary_dict()

        # Cache for future requests
        cache.set(cache_key, summary, self.CACHE_TTL)

        return summary

    def invalidate_lease_cache(self, lease_id: int):
        """Invalidate cache when lease is updated."""
        cache_key = f'lease_summary_{lease_id}'
        cache.delete(cache_key)
```

### 6.3 Background Job Processing

**Celery Integration (for async tasks)**
```python
# config/celery.py
from celery import Celery
from django.conf import settings

app = Celery('condominios_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**Async Contract Generation**
```python
# apps/documents/tasks.py
from celery import shared_task
from apps.shared.infrastructure.container import Container

@shared_task
def generate_contract_async(lease_id: int) -> str:
    """Generate contract asynchronously."""
    document_service = Container.document_service()
    pdf_path = document_service.generate_contract(lease_id)

    # Send notification
    # send_contract_ready_notification(lease_id, pdf_path)

    return pdf_path
```

### 6.4 Multi-Tenancy Support (Future)

**Tenant Isolation Strategies**
```python
# apps/shared/domain/multi_tenancy.py
from django.db import models

class TenantAwareModel(models.Model):
    """Base model for multi-tenant applications."""
    organization = models.ForeignKey(
        'shared.Organization',
        on_delete=models.CASCADE,
        db_index=True
    )

    class Meta:
        abstract = True

# apps/properties/models.py
class Building(TenantAwareModel):
    # Building now belongs to an organization
    street_number = models.PositiveIntegerField()
    # ... other fields

    class Meta:
        unique_together = ('organization', 'street_number')
```

**Middleware for Tenant Context**
```python
# apps/shared/middleware/tenant_middleware.py
from apps.shared.domain.tenant_context import set_current_organization

class TenantMiddleware:
    """Set current organization based on request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract organization from JWT token or subdomain
        organization_id = self.extract_organization(request)
        set_current_organization(organization_id)

        response = self.get_response(request)
        return response
```

### 6.5 API Rate Limiting

```python
# config/settings/base.py
REST_FRAMEWORK = {
    # ... other settings
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'contract_generation': '10/hour',  # Custom rate for expensive operations
    }
}
```

### 6.6 Database Sharding Strategy (Future Scale)

**Shard by Building/Organization**
```python
# For extreme scale, partition data by organization
DATABASE_ROUTERS = ['apps.shared.infrastructure.db_router.OrganizationDatabaseRouter']

class OrganizationDatabaseRouter:
    """Route database queries based on organization."""

    def db_for_read(self, model, **hints):
        if hasattr(model, 'organization_id'):
            org_id = getattr(model, 'organization_id', None)
            return self.get_shard_for_organization(org_id)
        return 'default'

    def get_shard_for_organization(self, org_id):
        # Consistent hashing to determine shard
        # shard_index = hash(org_id) % NUM_SHARDS
        # return f'shard_{shard_index}'
        pass
```

---

## 7. Migration Strategy

### 7.1 Phased Approach (Recommended)

**Phase 1: Foundation (Week 1)**
- Set up new app structure (properties, leases, tenants, documents, shared)
- Create environment-based configuration
- Implement base classes and interfaces
- Set up dependency injection container
- No breaking changes to API

**Phase 2: Domain Layer (Week 2)**
- Extract business logic from views to domain entities
- Implement domain services (DateCalculationService, FeeCalculationEngine)
- Create repository interfaces
- Implement repository implementations
- Add comprehensive unit tests for domain logic

**Phase 3: Application Layer (Week 3)**
- Create application services (LeaseService, DocumentGenerationService)
- Refactor ViewSets to use services
- Implement DTOs
- Add integration tests

**Phase 4: Infrastructure Improvements (Week 4)**
- Abstract PDF generation (support multiple generators)
- Implement pluggable storage (filesystem, S3)
- Add caching layer
- Set up background job processing

**Phase 5: Future Features (Week 5+)**
- Financial module (payments, expenses)
- Dashboard and analytics
- Advanced document generation (receipts, notices)
- Multi-tenancy support

### 7.2 Migration Script Example

```python
# scripts/migrate_architecture.py
"""
Script to gradually migrate code to new architecture.
Can be run incrementally without breaking the system.
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from core.models import Lease as OldLease
from apps.leases.models import Lease as NewLease
from apps.leases.infrastructure.repositories import DjangoLeaseRepository

def migrate_leases():
    """Migrate leases from old structure to new."""
    print("Migrating leases...")

    old_leases = OldLease.objects.all()
    repository = DjangoLeaseRepository()

    for old_lease in old_leases:
        # Create domain entity from old model
        domain_lease = convert_to_domain(old_lease)

        # Save using new repository
        repository.save(domain_lease)

        print(f"Migrated lease {old_lease.id}")

    print(f"Migrated {len(old_leases)} leases successfully")

if __name__ == '__main__':
    migrate_leases()
```

### 7.3 Backwards Compatibility

**Dual Write Pattern** (during migration)
```python
# Maintain both old and new structures temporarily
class LeaseService:
    def create_lease(self, request: CreateLeaseRequest) -> LeaseResponse:
        # Save to new structure
        lease = self._lease_repo.save(domain_lease)

        # Also save to old structure (temporary)
        self._legacy_save(lease)

        return LeaseResponse.from_entity(lease)
```

### 7.4 Testing Strategy During Migration

```python
# tests/migration/test_parity.py
"""
Ensure new implementation matches old behavior.
"""
import pytest
from core.views import LeaseViewSet as OldLeaseViewSet
from apps.leases.api.views import LeaseViewSet as NewLeaseViewSet

def test_create_lease_parity():
    """Ensure old and new implementations produce same results."""
    test_data = {
        'apartment_id': 1,
        'responsible_tenant_id': 1,
        'tenant_ids': [1, 2],
        'start_date': '2025-01-15',
        'validity_months': 12,
        'due_day': 10,
        'rental_value': '1500.00',
        'cleaning_fee': '200.00',
    }

    # Create using old implementation
    old_result = create_lease_old(test_data)

    # Create using new implementation
    new_result = create_lease_new(test_data)

    # Compare results
    assert old_result['rental_value'] == new_result['rental_value']
    assert old_result['start_date'] == new_result['start_date']
    # ... more assertions
```

---

## 8. Technology Recommendations

### 8.1 Core Technologies (Keep)

| Technology | Version | Rationale |
|------------|---------|-----------|
| Django | 5.0.2 | Solid foundation, no need to change |
| DRF | 3.14.0 | Well-suited for REST APIs |
| PostgreSQL | 13+ | Excellent for relational data |
| pyppeteer | Current | Works, but consider alternatives |

### 8.2 New Additions (Recommended)

| Technology | Purpose | Priority |
|------------|---------|----------|
| **python-decouple** | Environment configuration | HIGH |
| **dependency-injector** | Dependency injection | HIGH |
| **WeasyPrint** | Alternative PDF generator (doesn't need Chrome) | MEDIUM |
| **Redis** | Caching layer | MEDIUM |
| **Celery** | Background job processing | MEDIUM |
| **pytest** | Testing framework | HIGH |
| **factory-boy** | Test fixtures | MEDIUM |
| **django-extensions** | Development utilities | LOW |
| **django-debug-toolbar** | Development debugging | LOW |
| **sentry-sdk** | Error tracking (production) | MEDIUM |
| **gunicorn** | Production WSGI server | HIGH |

### 8.3 PDF Generation Alternatives

**Current: pyppeteer**
- Pros: Handles complex CSS/HTML
- Cons: Requires Chrome, slow, platform-dependent

**Alternative 1: WeasyPrint**
```python
# apps/documents/infrastructure/pdf_generators/weasyprint_generator.py
from weasyprint import HTML
from apps.documents.domain.generators import IPDFGenerator

class WeasyPrintPDFGenerator(IPDFGenerator):
    """WeasyPrint-based PDF generator (no Chrome needed)."""

    def generate_from_html(self, html_content: str) -> bytes:
        """Generate PDF from HTML string."""
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
```

**Alternative 2: ReportLab (programmatic)**
```python
# For simple documents, consider programmatic generation
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
```

**Recommendation:** Support multiple generators via strategy pattern (already shown in architecture).

---

## 9. Security Enhancements

### 9.1 Authentication & Authorization

**Add JWT Authentication**
```python
# config/settings/base.py
INSTALLED_APPS += ['rest_framework_simplejwt']

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # Change from AllowAny
    ],
}
```

**Role-Based Access Control**
```python
# apps/shared/api/permissions.py
from rest_framework import permissions

class IsPropertyManager(permissions.BasePermission):
    """Only property managers can modify leases."""

    def has_permission(self, request, view):
        return request.user.role == 'PROPERTY_MANAGER'

class IsOwnerOrPropertyManager(permissions.BasePermission):
    """Users can only access their own data."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'PROPERTY_MANAGER':
            return True

        if hasattr(obj, 'responsible_tenant'):
            return obj.responsible_tenant.user == request.user

        return False
```

### 9.2 Input Validation

**Domain-Level Validation**
```python
# apps/leases/domain/entities.py
class Lease:
    def change_due_date(self, new_due_day: int) -> Decimal:
        """Change due date with validation."""
        if not 1 <= new_due_day <= 31:
            raise ValueError("Due day must be between 1 and 31")

        if new_due_day == self.due_day:
            raise ValueError("New due day cannot be the same as current")

        # Calculate fee
        fee = FeeCalculationEngine.calculate_due_date_change_fee(
            self.rental_value,
            self.due_day,
            new_due_day
        )

        self.due_day = new_due_day
        return fee
```

### 9.3 Audit Logging

```python
# apps/shared/domain/audit.py
from django.db import models

class AuditMixin(models.Model):
    """Mixin for audit fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        abstract = True
```

---

## 10. Summary & Next Steps

### 10.1 Key Takeaways

1. **Current State:** Functional but monolithic MVT pattern with business logic in views
2. **Target State:** Layered architecture with DDD lite - clear separation of concerns
3. **Migration:** Phased approach over 4-5 weeks without breaking changes
4. **Benefits:** Better testability, maintainability, scalability, and extensibility

### 10.2 Immediate Actions (Priority Order)

**Week 1: Foundation**
1. Create `.env` file and migrate hardcoded config
2. Set up environment-based settings (base, development, production)
3. Create new app structure (properties, leases, tenants, documents, shared)
4. Install new dependencies (python-decouple, dependency-injector, pytest)

**Week 2: Domain Layer**
5. Extract business logic from views to domain entities
6. Implement domain services for date and fee calculations
7. Create repository interfaces
8. Write unit tests for domain logic

**Week 3: Application Layer**
9. Implement application services
10. Refactor ViewSets to use services
11. Add integration tests

**Week 4: Infrastructure**
12. Abstract PDF generation (support WeasyPrint as alternative)
13. Add caching layer
14. Set up background job processing for contract generation

### 10.3 Success Metrics

- **Testability:** 80%+ code coverage with isolated unit tests
- **Maintainability:** New features can be added without modifying existing code (Open/Closed Principle)
- **Performance:** Contract generation < 3 seconds (with caching)
- **Scalability:** Support for 10,000+ leases without performance degradation
- **Code Quality:** All business logic in domain layer, ViewSets < 50 lines each

### 10.4 Risk Mitigation

1. **Risk:** Breaking existing API contracts during migration
   - **Mitigation:** Maintain backwards compatibility, dual-write during transition

2. **Risk:** Performance degradation from additional layers
   - **Mitigation:** Comprehensive benchmarking, caching strategy

3. **Risk:** Learning curve for team
   - **Mitigation:** Comprehensive documentation, gradual migration, code reviews

4. **Risk:** Over-engineering for current scale
   - **Mitigation:** Start with "lite" DDD, add complexity only when needed

---

## Appendix: Architecture Decision Records

### ADR-001: Layered Architecture vs. Hexagonal Architecture

**Context:** Need to separate concerns and improve testability

**Decision:** Use Layered Architecture with DDD lite instead of full Hexagonal/Clean Architecture

**Rationale:**
- Simpler to understand for team familiar with Django MVT
- Provides sufficient separation of concerns for current scale
- Can evolve to Hexagonal if needed
- Less boilerplate than full Clean Architecture

**Consequences:**
- Some coupling between layers (acceptable tradeoff)
- Easier migration path from current structure
- Faster initial implementation

### ADR-002: Multiple Apps vs. Single App with Modules

**Context:** Current single-app structure is becoming unwieldy

**Decision:** Use multiple Django apps based on bounded contexts

**Rationale:**
- Clear separation of domains (properties, leases, tenants, documents)
- Enables independent development and testing
- Supports future microservices migration if needed
- Better code organization and discoverability

**Consequences:**
- More files and structure to navigate
- Cross-app imports need to be managed carefully
- Clearer boundaries and responsibilities

### ADR-003: Repository Pattern vs. Direct ORM Access

**Context:** Need to decouple business logic from data access

**Decision:** Implement Repository Pattern with interfaces

**Rationale:**
- Enables unit testing without database
- Allows swapping ORM implementations
- Clear contract for data access
- Supports CQRS pattern in future

**Consequences:**
- Additional abstraction layer
- More initial code to write
- Better testability and flexibility

---

**Document Version:** 1.0
**Last Updated:** 2025-10-19
**Author:** Claude (Backend Architecture Specialist)
