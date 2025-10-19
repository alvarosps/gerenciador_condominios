# Refactoring Example: Contract Generation
## Before & After Comparison

This document provides a concrete example of refactoring the contract generation feature from the current monolithic approach to the recommended layered architecture.

---

## Current Implementation (Monolithic)

### File: `core/views.py` (lines 47-160)

**Problems:**
- 113 lines in a single method
- Mixes HTTP handling, business logic, infrastructure concerns
- Impossible to unit test without mocking Django ORM, file system, and browser
- Hardcoded configuration
- Tight coupling to pyppeteer
- No separation of concerns

```python
# core/views.py - CURRENT IMPLEMENTATION
class LeaseViewSet(viewsets.ModelViewSet):
    queryset = Lease.objects.all()
    serializer_class = LeaseSerializer

    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        lease = self.get_object()

        try:
            # Date calculations mixed with orchestration
            start_date = lease.start_date
            validity = lease.validity_months
            next_month_date = (start_date + relativedelta(months=1)).strftime("%d/%m/%Y")
            calculated_final_date = start_date + relativedelta(months=validity)

            # Leap year edge case handling
            if start_date.month == 2 and start_date.day == 29:
                if calculated_final_date.month == 2 and calculated_final_date.day == 28:
                    calculated_final_date = calculated_final_date + timedelta(days=1)

            final_date = calculated_final_date.strftime("%d/%m/%Y")

            # Business logic: tag fee calculation
            valor_tags = 50 if len(lease.tenants.all()) == 1 else 80
            valor_total = lease.rental_value + lease.cleaning_fee + valor_tags

            # Business logic: furniture calculation
            apt_furniture = set(lease.apartment.furnitures.all())
            tenant_furniture = set(lease.responsible_tenant.furnitures.all())
            lease_furnitures = list(apt_furniture - tenant_furniture)

            # Template context preparation
            context = {
                'tenant': lease.responsible_tenant,
                'building_number': lease.apartment.building.street_number,
                'apartment_number': lease.apartment.number,
                'furnitures': lease_furnitures,
                'validity': validity,
                'start_date': start_date.strftime("%d/%m/%Y"),
                'final_date': final_date,
                'rental_value': lease.rental_value,
                'next_month_date': next_month_date,
                'tag_fee': lease.tag_fee,
                'cleaning_fee': lease.cleaning_fee,
                'valor_total': valor_total,
                'rules': regras_condominio,
                'lease': lease,
                'valor_tags': valor_tags,
            }

            # Template rendering
            template_path = os.path.join(settings.BASE_DIR, 'core', 'templates')
            env = Environment(loader=FileSystemLoader(template_path))
            env.filters['currency'] = format_currency
            env.filters['extenso'] = number_to_words
            template = env.get_template('contract_template.html')
            html_content = template.render(context)

            # File system operations
            base_dir = settings.BASE_DIR
            contracts_dir = os.path.join(base_dir, 'contracts', str(lease.apartment.building.street_number))
            os.makedirs(contracts_dir, exist_ok=True)
            pdf_path = os.path.join(contracts_dir, f"contract_apto_{lease.apartment.number}_{lease.id}.pdf")

            # PDF generation with pyppeteer (async)
            async def create_pdf():
                browser = await launch(
                    handleSIGINT=False,
                    handleSIGTERM=False,
                    handleSIGHUP=False,
                    options={
                        'pipe': 'true',
                        'executablePath': "C:\Program Files\Google\Chrome\Application\chrome.exe",  # HARDCODED!
                        'headless': True,
                        'args': ['--headless', '--no-sandbox', '--disable-gpu'],
                    },
                )
                page = await browser.newPage()
                temp_html_path = os.path.join(contracts_dir, f"temp_contract_{lease.id}.html")
                with open(temp_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                file_url = f'file:///{temp_html_path}'
                await page.goto(file_url, {'waitUntil': 'networkidle2'})
                await page.pdf({'path': pdf_path, 'format': 'A4'})
                await browser.close()
                os.remove(temp_html_path)

            asyncio.run(create_pdf())

            # Database update
            lease.contract_generated = True
            lease.save()

            return Response({"message": "Contrato gerado com sucesso!", "pdf_path": pdf_path}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Issues Summary:**
1. **God Method:** Does everything (113 lines)
2. **Multiple Responsibilities:** HTTP handling + business logic + infrastructure
3. **Hardcoded Values:** Chrome path, tag fees, date formats
4. **Tight Coupling:** Cannot swap PDF generator
5. **No Testability:** Requires mocking everything
6. **Poor Error Handling:** Generic exception catching
7. **No Reusability:** Cannot generate contracts outside of HTTP context

---

## Refactored Implementation (Layered Architecture)

### Layer 1: API Layer (Presentation)

**File: `apps/leases/api/views.py`**

**Responsibility:** HTTP handling only - validate request, call service, return response

```python
# apps/leases/api/views.py - REFACTORED
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.shared.infrastructure.container import Container
from apps.leases.api.serializers import LeaseSerializer
from apps.leases.domain.exceptions import (
    LeaseNotFoundError,
    ContractGenerationError
)


class LeaseViewSet(viewsets.ModelViewSet):
    """
    Lease management API.
    Thin layer - delegates all business logic to service layer.
    """
    serializer_class = LeaseSerializer
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dependency injection
        self._lease_service = Container.lease_service()

    @action(detail=True, methods=['post'])
    def generate_contract(self, request, pk=None):
        """
        Generate contract PDF for a lease.

        Returns:
            - 200: Contract generated successfully
            - 404: Lease not found
            - 500: Contract generation failed
        """
        try:
            pdf_path = self._lease_service.generate_contract(lease_id=int(pk))

            return Response(
                {
                    'message': 'Contract generated successfully',
                    'pdf_path': pdf_path,
                    'download_url': f'/api/documents/download?path={pdf_path}'
                },
                status=status.HTTP_200_OK
            )

        except LeaseNotFoundError as e:
            return Response(
                {'error': f'Lease not found: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )

        except ContractGenerationError as e:
            return Response(
                {'error': f'Failed to generate contract: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            # Log unexpected errors
            logger.exception(f"Unexpected error generating contract for lease {pk}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
```

**Benefits:**
- Only 45 lines (vs 113)
- Clear responsibility: HTTP handling only
- Proper error handling with specific exceptions
- Testable by mocking service
- Permission control
- No business logic

---

### Layer 2: Application Layer (Service)

**File: `apps/leases/application/services.py`**

**Responsibility:** Use case orchestration - coordinate domain objects and infrastructure

```python
# apps/leases/application/services.py - REFACTORED
from typing import Optional
from datetime import date

from apps.leases.domain.repositories import ILeaseRepository
from apps.documents.application.services import DocumentGenerationService
from apps.leases.application.dtos import ContractGenerationRequest
from apps.leases.domain.exceptions import LeaseNotFoundError, ContractGenerationError


class LeaseService:
    """
    Application service for lease management.
    Orchestrates use cases involving leases.
    """

    def __init__(
        self,
        lease_repository: ILeaseRepository,
        document_service: DocumentGenerationService
    ):
        self._lease_repo = lease_repository
        self._document_service = document_service

    def generate_contract(self, lease_id: int) -> str:
        """
        Generate contract PDF for a lease.

        Workflow:
        1. Retrieve lease from repository
        2. Validate lease can generate contract
        3. Prepare contract data using domain logic
        4. Delegate PDF generation to document service
        5. Update lease status
        6. Return PDF path

        Args:
            lease_id: ID of the lease

        Returns:
            Path to generated PDF file

        Raises:
            LeaseNotFoundError: If lease doesn't exist
            ContractGenerationError: If generation fails
        """
        # Step 1: Retrieve lease
        lease = self._lease_repo.get_by_id(lease_id)
        if not lease:
            raise LeaseNotFoundError(f"Lease with ID {lease_id} not found")

        # Step 2: Validate (using domain logic)
        if not lease.can_generate_contract():
            raise ContractGenerationError(
                "Lease cannot generate contract - missing required data"
            )

        # Step 3: Prepare contract data (using domain methods)
        contract_request = ContractGenerationRequest(
            lease_id=lease.id,
            tenant=lease.responsible_tenant,
            apartment=lease.apartment,
            building=lease.apartment.building,
            furnitures=lease.calculate_furniture_inventory(),  # Domain method
            start_date=lease.start_date,
            final_date=lease.calculate_final_date(),  # Domain method
            next_month_date=lease.calculate_next_month_date(),  # Domain method
            rental_value=lease.rental_value,
            cleaning_fee=lease.cleaning_fee,
            tag_fee=lease.tag_fee,
            total_value=lease.calculate_total_value(),  # Domain method
            validity_months=lease.validity_months,
        )

        # Step 4: Delegate to document service
        try:
            pdf_path = self._document_service.generate_contract(contract_request)
        except Exception as e:
            raise ContractGenerationError(f"PDF generation failed: {str(e)}")

        # Step 5: Update lease status (using domain method)
        lease.mark_contract_generated()
        self._lease_repo.save(lease)

        # Step 6: Return result
        return pdf_path
```

**Benefits:**
- Clear orchestration workflow
- Uses domain methods for business logic
- Delegates infrastructure concerns to other services
- Proper exception handling
- Testable by mocking repositories and services
- No knowledge of HTTP, templates, or PDF generation

---

### Layer 3: Domain Layer (Business Logic)

**File: `apps/leases/domain/entities.py`**

**Responsibility:** Business rules and domain logic

```python
# apps/leases/domain/entities.py - REFACTORED
from datetime import date
from decimal import Decimal
from typing import List, Set

from apps.leases.domain.services import DateCalculationService, FeeCalculationEngine
from apps.leases.domain.value_objects import DateRange
from apps.properties.domain.entities import Apartment
from apps.tenants.domain.entities import Tenant
from apps.shared.domain.entities import Furniture


class Lease:
    """
    Lease aggregate root.
    Encapsulates all business logic related to leases.
    """

    def __init__(
        self,
        id: int,
        apartment: Apartment,
        responsible_tenant: Tenant,
        tenants: List[Tenant],
        start_date: date,
        validity_months: int,
        due_day: int,
        rental_value: Decimal,
        cleaning_fee: Decimal,
        tag_fee: Decimal,
        contract_generated: bool = False,
        contract_signed: bool = False,
        interfone_configured: bool = False,
        warning_count: int = 0
    ):
        self.id = id
        self.apartment = apartment
        self.responsible_tenant = responsible_tenant
        self.tenants = tenants
        self.start_date = start_date
        self.validity_months = validity_months
        self.due_day = due_day
        self.rental_value = rental_value
        self.cleaning_fee = cleaning_fee
        self.tag_fee = tag_fee
        self.contract_generated = contract_generated
        self.contract_signed = contract_signed
        self.interfone_configured = interfone_configured
        self.warning_count = warning_count

    # ============================================
    # Business Logic Methods
    # ============================================

    def calculate_final_date(self) -> date:
        """
        Calculate the final date of the lease.
        Delegates to domain service for complex date logic.
        """
        return DateCalculationService.calculate_final_date(
            self.start_date,
            self.validity_months
        )

    def calculate_next_month_date(self) -> date:
        """Calculate the date one month after start date."""
        return DateCalculationService.calculate_next_month_date(self.start_date)

    def calculate_furniture_inventory(self) -> List[Furniture]:
        """
        Calculate furniture that comes with the lease.

        Business Rule: Lease furniture = Apartment furniture - Responsible tenant's furniture
        (Because tenant may bring their own furniture)
        """
        apartment_furniture = set(self.apartment.furnitures)
        tenant_furniture = set(self.responsible_tenant.furnitures)
        lease_furniture = apartment_furniture - tenant_furniture

        return list(lease_furniture)

    def calculate_total_value(self) -> Decimal:
        """
        Calculate total initial payment.
        Total = rental + cleaning fee + tag fee
        """
        return self.rental_value + self.cleaning_fee + self.tag_fee

    def calculate_late_fee(self, current_date: date) -> Decimal:
        """
        Calculate late payment fee based on current date.

        Business Rule: 5% per day based on daily rental rate
        """
        days_late = DateCalculationService.days_late(self.due_day, current_date)

        if days_late <= 0:
            return Decimal('0.00')

        return FeeCalculationEngine.calculate_late_fee(
            self.rental_value,
            days_late
        )

    def change_due_date(self, new_due_day: int) -> Decimal:
        """
        Change the due date and calculate the fee.

        Business Rule: Fee = daily_rate * days_difference

        Args:
            new_due_day: New due day (1-31)

        Returns:
            Fee charged for the change

        Raises:
            ValueError: If invalid due day
        """
        # Validation
        if not 1 <= new_due_day <= 31:
            raise ValueError("Due day must be between 1 and 31")

        if new_due_day == self.due_day:
            raise ValueError("New due day must be different from current")

        # Calculate fee
        fee = FeeCalculationEngine.calculate_due_date_change_fee(
            self.rental_value,
            self.due_day,
            new_due_day
        )

        # Update state
        self.due_day = new_due_day

        return fee

    def can_generate_contract(self) -> bool:
        """
        Validate if contract can be generated.

        Business Rules:
        - Must have responsible tenant
        - Must have at least one tenant
        - Apartment must be valid
        """
        if not self.responsible_tenant:
            return False

        if not self.tenants or len(self.tenants) == 0:
            return False

        if not self.apartment:
            return False

        return True

    def mark_contract_generated(self):
        """Mark contract as generated."""
        self.contract_generated = True

    def mark_contract_signed(self):
        """Mark contract as signed."""
        if not self.contract_generated:
            raise ValueError("Cannot sign contract that hasn't been generated")

        self.contract_signed = True

    def is_expired(self, current_date: date) -> bool:
        """Check if lease has expired."""
        final_date = self.calculate_final_date()
        return current_date > final_date

    def days_until_expiration(self, current_date: date) -> int:
        """Calculate days until lease expires."""
        final_date = self.calculate_final_date()
        delta = final_date - current_date
        return delta.days

    # ============================================
    # Factory Methods
    # ============================================

    @staticmethod
    def create(
        apartment: Apartment,
        responsible_tenant: Tenant,
        tenants: List[Tenant],
        start_date: date,
        validity_months: int,
        due_day: int,
        rental_value: Decimal,
        cleaning_fee: Decimal,
        tag_fee: Decimal = None
    ) -> 'Lease':
        """
        Factory method to create a new lease with validation.

        Args:
            apartment: Apartment to lease
            responsible_tenant: Tenant responsible for the contract
            tenants: All tenants living in the apartment
            start_date: Lease start date
            validity_months: Contract validity in months
            due_day: Monthly payment due day
            rental_value: Monthly rental value
            cleaning_fee: One-time cleaning fee
            tag_fee: Tag deposit (optional, will be calculated if not provided)

        Returns:
            New Lease instance

        Raises:
            ValueError: If validation fails
        """
        # Validation
        if not apartment.can_be_rented():
            raise ValueError(f"Apartment {apartment.id} is not available for rent")

        if responsible_tenant not in tenants:
            raise ValueError("Responsible tenant must be in the tenants list")

        if len(tenants) > apartment.max_tenants:
            raise ValueError(
                f"Number of tenants ({len(tenants)}) exceeds maximum ({apartment.max_tenants})"
            )

        if not 1 <= due_day <= 31:
            raise ValueError("Due day must be between 1 and 31")

        # Calculate tag fee if not provided
        if tag_fee is None:
            tag_fee = FeeCalculationEngine.calculate_tag_fee(len(tenants))

        return Lease(
            id=None,  # Will be assigned by repository
            apartment=apartment,
            responsible_tenant=responsible_tenant,
            tenants=tenants,
            start_date=start_date,
            validity_months=validity_months,
            due_day=due_day,
            rental_value=rental_value,
            cleaning_fee=cleaning_fee,
            tag_fee=tag_fee,
            contract_generated=False,
            contract_signed=False,
            interfone_configured=False,
            warning_count=0
        )
```

**File: `apps/leases/domain/services.py`**

**Responsibility:** Complex business logic that doesn't belong to a single entity

```python
# apps/leases/domain/services.py - REFACTORED
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from apps.shared.infrastructure.config import AppConfig


class DateCalculationService:
    """
    Domain service for complex date calculations.
    Encapsulates date-related business rules.
    """

    @staticmethod
    def calculate_final_date(start_date: date, validity_months: int) -> date:
        """
        Calculate the final date of a lease.

        Business Rule: Handle special case for leap year
        If start date is Feb 29 and calculated end is Feb 28, move to March 1

        Args:
            start_date: Lease start date
            validity_months: Number of months

        Returns:
            Final date of the lease
        """
        calculated_final_date = start_date + relativedelta(months=validity_months)

        # Special case: Feb 29 leap year handling
        if start_date.month == 2 and start_date.day == 29:
            if calculated_final_date.month == 2 and calculated_final_date.day == 28:
                # Move to March 1
                calculated_final_date = calculated_final_date + timedelta(days=1)

        return calculated_final_date

    @staticmethod
    def calculate_next_month_date(start_date: date) -> date:
        """
        Calculate the date one month after start date.

        Args:
            start_date: Reference date

        Returns:
            Date one month later
        """
        return start_date + relativedelta(months=1)

    @staticmethod
    def days_late(due_day: int, current_date: date) -> int:
        """
        Calculate how many days a payment is late.

        Business Rule: If current day > due day, payment is late

        Args:
            due_day: Day of month payment is due
            current_date: Current date

        Returns:
            Number of days late (0 if not late)
        """
        if current_date.day <= due_day:
            return 0

        return current_date.day - due_day


class FeeCalculationEngine:
    """
    Domain service for fee calculations.
    Encapsulates all fee calculation business rules.
    """

    @classmethod
    def calculate_late_fee(
        cls,
        rental_value: Decimal,
        days_late: int
    ) -> Decimal:
        """
        Calculate late payment fee.

        Business Rule: (rental_value / 30) * days_late * 5%

        Args:
            rental_value: Monthly rental value
            days_late: Number of days late

        Returns:
            Late fee amount
        """
        if days_late <= 0:
            return Decimal('0.00')

        # Get configuration
        late_rate = Decimal(str(AppConfig.get_late_fee_rate()))
        days_per_month = Decimal(str(AppConfig.get_fee_days_per_month()))

        # Calculate
        daily_rate = rental_value / days_per_month
        late_fee = daily_rate * Decimal(days_late) * late_rate

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

        Business Rule: (rental_value / 30) * abs(day_difference)

        Args:
            rental_value: Monthly rental value
            current_due_day: Current due day
            new_due_day: New due day

        Returns:
            Change fee amount
        """
        days_difference = abs(new_due_day - current_due_day)
        days_per_month = Decimal(str(AppConfig.get_fee_days_per_month()))

        daily_rate = rental_value / days_per_month
        fee = daily_rate * Decimal(days_difference)

        return fee.quantize(Decimal('0.01'))

    @classmethod
    def calculate_tag_fee(cls, number_of_tenants: int) -> Decimal:
        """
        Calculate tag deposit fee based on number of tenants.

        Business Rule:
        - 1 tenant: R$ 50
        - 2+ tenants: R$ 80

        Args:
            number_of_tenants: Number of tenants

        Returns:
            Tag fee amount
        """
        if number_of_tenants == 1:
            return Decimal(str(AppConfig.get_tag_fee_single()))

        return Decimal(str(AppConfig.get_tag_fee_multiple()))
```

**Benefits:**
- All business logic in domain layer
- Pure functions - easily testable
- No dependencies on infrastructure
- Clear business rules documentation
- Configuration externalized

---

### Layer 4: Infrastructure Layer

**File: `apps/documents/application/services.py`**

**Responsibility:** Coordinate document generation infrastructure

```python
# apps/documents/application/services.py - REFACTORED
from typing import Dict

from apps.documents.domain.generators import IPDFGenerator
from apps.documents.infrastructure.storage import IDocumentStorage
from apps.documents.infrastructure.template_engine import ITemplateEngine
from apps.leases.application.dtos import ContractGenerationRequest
from apps.documents.domain.content import get_condominium_rules
from apps.shared.infrastructure.formatters import format_currency, number_to_words


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

        Workflow:
        1. Prepare template context
        2. Render HTML from template
        3. Generate PDF from HTML
        4. Store PDF file
        5. Return file path

        Args:
            request: Contract generation request DTO

        Returns:
            Path or URL to the generated document

        Raises:
            TemplateRenderError: If template rendering fails
            PDFGenerationError: If PDF generation fails
            StorageError: If file storage fails
        """
        # Step 1: Prepare context
        context = self._prepare_contract_context(request)

        # Step 2: Render HTML
        html_content = self._template_engine.render(
            template_name='contract_template.html',
            context=context
        )

        # Step 3: Generate PDF
        pdf_bytes = self._pdf_generator.generate_from_html(html_content)

        # Step 4: Store document
        filename = f"contract_apto_{request.apartment.number}_{request.lease_id}.pdf"
        path_pattern = f"contracts/{request.building.street_number}/{filename}"

        document_path = self._storage.save(
            path=path_pattern,
            content=pdf_bytes,
            content_type='application/pdf'
        )

        # Step 5: Return path
        return document_path

    def _prepare_contract_context(self, request: ContractGenerationRequest) -> Dict:
        """
        Prepare Jinja2 template context.

        Args:
            request: Contract generation request

        Returns:
            Dictionary with template variables
        """
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

**File: `apps/documents/infrastructure/pdf_generators/pyppeteer_generator.py`**

**Responsibility:** PDF generation implementation (swappable)

```python
# apps/documents/infrastructure/pdf_generators/pyppeteer_generator.py - REFACTORED
import asyncio
import os
import tempfile
from pathlib import Path

from pyppeteer import launch

from apps.documents.domain.generators import IPDFGenerator
from apps.documents.domain.exceptions import PDFGenerationError
from apps.shared.infrastructure.config import AppConfig


class PyppeteerPDFGenerator(IPDFGenerator):
    """
    PDF generator using pyppeteer (headless Chrome).
    Implementation of IPDFGenerator interface.
    """

    def __init__(self):
        """Initialize generator with configuration."""
        self._chrome_path = AppConfig.get_pdf_chrome_path()
        self._timeout = AppConfig.get_pdf_timeout()

    def generate_from_html(self, html_content: str) -> bytes:
        """
        Generate PDF from HTML content.

        Args:
            html_content: HTML string

        Returns:
            PDF file as bytes

        Raises:
            PDFGenerationError: If generation fails
        """
        try:
            # Run async PDF generation
            pdf_bytes = asyncio.run(self._generate_pdf_async(html_content))
            return pdf_bytes

        except Exception as e:
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")

    async def _generate_pdf_async(self, html_content: str) -> bytes:
        """
        Async PDF generation implementation.

        Args:
            html_content: HTML string

        Returns:
            PDF file as bytes
        """
        browser = None
        temp_html_file = None

        try:
            # Launch browser
            browser = await launch(
                handleSIGINT=False,
                handleSIGTERM=False,
                handleSIGHUP=False,
                options={
                    'pipe': 'true',
                    'executablePath': self._chrome_path,
                    'headless': True,
                    'args': [
                        '--headless',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ],
                },
            )

            # Create page
            page = await browser.newPage()

            # Write HTML to temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                suffix='.html',
                delete=False
            ) as f:
                f.write(html_content)
                temp_html_file = f.name

            # Load HTML
            file_url = f'file:///{temp_html_file}'
            await page.goto(file_url, {'waitUntil': 'networkidle2'})

            # Generate PDF
            pdf_bytes = await page.pdf({'format': 'A4'})

            return pdf_bytes

        finally:
            # Cleanup
            if browser:
                await browser.close()

            if temp_html_file and os.path.exists(temp_html_file):
                os.remove(temp_html_file)
```

**File: `apps/documents/infrastructure/pdf_generators/weasyprint_generator.py`**

**Responsibility:** Alternative PDF generator (no Chrome required)

```python
# apps/documents/infrastructure/pdf_generators/weasyprint_generator.py - NEW
from weasyprint import HTML

from apps.documents.domain.generators import IPDFGenerator
from apps.documents.domain.exceptions import PDFGenerationError


class WeasyPrintPDFGenerator(IPDFGenerator):
    """
    PDF generator using WeasyPrint.
    Alternative implementation that doesn't require Chrome.
    Better for server environments.
    """

    def generate_from_html(self, html_content: str) -> bytes:
        """
        Generate PDF from HTML content.

        Args:
            html_content: HTML string

        Returns:
            PDF file as bytes

        Raises:
            PDFGenerationError: If generation fails
        """
        try:
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes

        except Exception as e:
            raise PDFGenerationError(f"Failed to generate PDF with WeasyPrint: {str(e)}")
```

**Benefits:**
- Pluggable PDF generators (can swap implementation)
- Clean separation of concerns
- No hardcoded paths
- Proper error handling
- Easy to test each component
- Can add new generators (ReportLab, etc.) without changing existing code

---

## Testing Comparison

### Current Implementation Testing (DIFFICULT)

```python
# Requires mocking everything
from unittest.mock import patch, MagicMock

@patch('core.views.Lease.objects')
@patch('core.views.Environment')
@patch('core.views.launch')
@patch('core.views.os.makedirs')
@patch('core.views.os.path.join')
def test_generate_contract_old(
    mock_path_join,
    mock_makedirs,
    mock_launch,
    mock_env,
    mock_lease_objects
):
    # Complex setup...
    # Difficult to maintain
    # Brittle tests
    pass
```

### Refactored Implementation Testing (EASY)

**Domain Layer Tests (Pure Logic)**
```python
# tests/domain/test_lease_entity.py
import pytest
from datetime import date
from decimal import Decimal

from apps.leases.domain.entities import Lease
from apps.leases.domain.services import DateCalculationService


def test_calculate_final_date_normal():
    """Test normal final date calculation."""
    start_date = date(2025, 1, 15)
    validity_months = 12

    final_date = DateCalculationService.calculate_final_date(
        start_date,
        validity_months
    )

    assert final_date == date(2026, 1, 15)


def test_calculate_final_date_leap_year():
    """Test leap year edge case."""
    start_date = date(2024, 2, 29)  # Leap year
    validity_months = 12

    final_date = DateCalculationService.calculate_final_date(
        start_date,
        validity_months
    )

    # Feb 28 2025 -> March 1 2025 (edge case handling)
    assert final_date == date(2025, 3, 1)


def test_calculate_late_fee():
    """Test late fee calculation."""
    from apps.leases.domain.services import FeeCalculationEngine

    rental_value = Decimal('1500.00')
    days_late = 5

    late_fee = FeeCalculationEngine.calculate_late_fee(
        rental_value,
        days_late
    )

    # (1500 / 30) * 5 * 0.05 = 12.50
    assert late_fee == Decimal('12.50')


def test_calculate_furniture_inventory():
    """Test furniture calculation business logic."""
    # Create test data
    apartment_furniture = [
        Furniture(id=1, name="Bed"),
        Furniture(id=2, name="Desk"),
        Furniture(id=3, name="Chair"),
    ]

    tenant_furniture = [
        Furniture(id=2, name="Desk"),  # Tenant brings their own desk
    ]

    lease = Lease(
        id=1,
        apartment=Apartment(furnitures=apartment_furniture),
        responsible_tenant=Tenant(furnitures=tenant_furniture),
        # ... other fields
    )

    lease_furniture = lease.calculate_furniture_inventory()

    # Should have Bed and Chair (Desk is tenant's)
    assert len(lease_furniture) == 2
    assert any(f.name == "Bed" for f in lease_furniture)
    assert any(f.name == "Chair" for f in lease_furniture)
    assert not any(f.name == "Desk" for f in lease_furniture)
```

**Service Layer Tests (With Mocks)**
```python
# tests/application/test_lease_service.py
import pytest
from unittest.mock import Mock
from datetime import date
from decimal import Decimal

from apps.leases.application.services import LeaseService
from apps.leases.domain.entities import Lease
from apps.leases.domain.exceptions import LeaseNotFoundError


def test_generate_contract_success():
    """Test successful contract generation."""
    # Arrange
    mock_lease_repo = Mock()
    mock_document_service = Mock()

    lease = Lease(
        id=1,
        # ... lease data
    )

    mock_lease_repo.get_by_id.return_value = lease
    mock_document_service.generate_contract.return_value = "/path/to/contract.pdf"

    service = LeaseService(
        lease_repository=mock_lease_repo,
        document_service=mock_document_service
    )

    # Act
    pdf_path = service.generate_contract(lease_id=1)

    # Assert
    assert pdf_path == "/path/to/contract.pdf"
    mock_lease_repo.get_by_id.assert_called_once_with(1)
    mock_document_service.generate_contract.assert_called_once()
    mock_lease_repo.save.assert_called_once()
    assert lease.contract_generated is True


def test_generate_contract_lease_not_found():
    """Test contract generation with non-existent lease."""
    # Arrange
    mock_lease_repo = Mock()
    mock_lease_repo.get_by_id.return_value = None

    service = LeaseService(
        lease_repository=mock_lease_repo,
        document_service=Mock()
    )

    # Act & Assert
    with pytest.raises(LeaseNotFoundError):
        service.generate_contract(lease_id=999)
```

**Benefits:**
- Unit tests run in milliseconds (no I/O)
- Clear test boundaries
- Easy to test edge cases
- No complex mocking
- Test failures are obvious

---

## Summary: Before vs After

| Aspect | Before (Monolithic) | After (Layered) |
|--------|---------------------|-----------------|
| **Lines of Code** | 113 lines in one method | Split across 4+ files, each focused |
| **Testability** | Difficult (requires mocking everything) | Easy (pure functions, dependency injection) |
| **Reusability** | Locked in ViewSet | Business logic reusable anywhere |
| **Flexibility** | Hardcoded PDF generator | Pluggable generators via interface |
| **Maintainability** | God method, hard to understand | Clear responsibilities, easy to navigate |
| **Configuration** | Hardcoded values | Externalized config |
| **Error Handling** | Generic exceptions | Specific domain exceptions |
| **Separation of Concerns** | Mixed (HTTP + logic + infrastructure) | Clear layers |
| **Business Logic Location** | Scattered in views | Centralized in domain layer |
| **Dependency Direction** | Unclear | Always inward (dependency inversion) |

---

## Migration Path

**Step 1:** Create new domain entity with business logic
**Step 2:** Create domain services for complex calculations
**Step 3:** Create application service
**Step 4:** Create infrastructure services
**Step 5:** Refactor ViewSet to use service
**Step 6:** Add tests
**Step 7:** Remove old code

**Can be done incrementally** without breaking existing functionality!

---

**Author:** Claude (Backend Architecture Specialist)
**Version:** 1.0
**Date:** 2025-10-19
