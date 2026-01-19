"""
Contract generation service for PDF contract creation.

Phase 4 Infrastructure: Refactored to use IPDFGenerator and IDocumentStorage abstractions.

Handles all business logic related to contract generation including:
- Context preparation for contract templates
- Furniture calculations
- Template rendering with Jinja2
- PDF generation via IPDFGenerator (supports multiple engines)
- File storage via IDocumentStorage (supports filesystem and cloud)
"""

from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import transaction

from asgiref.sync import async_to_sync
from jinja2 import Environment, FileSystemLoader

from core.contract_rules import regras_condominio
from core.infrastructure import FileSystemDocumentStorage, IDocumentStorage, IPDFGenerator, PyppeteerPDFGenerator
from core.models import Furniture, Lease
from core.utils import format_currency, number_to_words

from .date_calculator import DateCalculatorService
from .fee_calculator import FeeCalculatorService

logger = logging.getLogger(__name__)


class ContractService:
    """
    Service for contract generation and PDF creation.

    Phase 4 Infrastructure: Uses Strategy pattern with IPDFGenerator and IDocumentStorage.

    Handles all contract-related business logic including context preparation,
    template rendering, and PDF generation. Supports dependency injection for
    PDF generators and document storage backends.

    Attributes:
        pdf_generator: IPDFGenerator implementation (default: PyppeteerPDFGenerator)
        document_storage: IDocumentStorage implementation (default: FileSystemDocumentStorage)

    Example usage:
        >>> # Using default implementations
        >>> lease = Lease.objects.get(pk=1)
        >>> pdf_path = ContractService.generate_contract(lease)
        >>> print(f"Contract generated: {pdf_path}")

        >>> # Using custom implementations (dependency injection)
        >>> from core.infrastructure import WeasyPrintPDFGenerator, S3DocumentStorage
        >>> service = ContractService(
        ...     pdf_generator=WeasyPrintPDFGenerator(),
        ...     document_storage=S3DocumentStorage(bucket_name="my-bucket")
        ... )
        >>> pdf_path = service.generate_contract_instance(lease)
    """

    # Class-level default implementations
    _default_pdf_generator: Optional[IPDFGenerator] = None
    _default_document_storage: Optional[IDocumentStorage] = None

    def __init__(
        self,
        pdf_generator: Optional[IPDFGenerator] = None,
        document_storage: Optional[IDocumentStorage] = None,
    ):
        """
        Initialize ContractService with custom implementations.

        Args:
            pdf_generator: Custom PDF generator (default: PyppeteerPDFGenerator)
            document_storage: Custom document storage (default: FileSystemDocumentStorage)
        """
        self.pdf_generator = pdf_generator or self._get_default_pdf_generator()
        self.document_storage = document_storage or self._get_default_document_storage()

    @classmethod
    def _get_default_pdf_generator(cls) -> IPDFGenerator:
        """Get or create the default PDF generator."""
        if cls._default_pdf_generator is None:
            chrome_path = getattr(settings, "CHROME_EXECUTABLE_PATH", None)
            cls._default_pdf_generator = PyppeteerPDFGenerator(chrome_path=chrome_path)
            logger.info("Initialized default PyppeteerPDFGenerator")
        return cls._default_pdf_generator

    @classmethod
    def _get_default_document_storage(cls) -> IDocumentStorage:
        """Get or create the default document storage."""
        if cls._default_document_storage is None:
            base_dir = getattr(settings, "PDF_OUTPUT_DIR", "contracts")
            cls._default_document_storage = FileSystemDocumentStorage(base_path=base_dir)
            logger.info(f"Initialized default FileSystemDocumentStorage at: {base_dir}")
        return cls._default_document_storage

    @staticmethod
    def calculate_lease_furniture(lease: Lease) -> List[Furniture]:
        """
        Calculate furniture list for the lease.

        Lease furniture = Apartment furniture - ALL tenants' furniture
        (subtracts furniture from all tenants, not just the responsible tenant)

        Args:
            lease: The lease object

        Returns:
            List of Furniture objects included in the lease

        Examples:
            >>> lease = Lease.objects.get(pk=1)
            >>> furniture = ContractService.calculate_lease_furniture(lease)
            >>> print(f"Lease includes {len(furniture)} furniture items")
        """
        apt_furniture = set(lease.apartment.furnitures.all())

        # Collect furniture from ALL tenants, not just responsible tenant
        all_tenant_furniture = set()
        for tenant in lease.tenants.all():
            all_tenant_furniture.update(tenant.furnitures.all())

        lease_furnitures = list(apt_furniture - all_tenant_furniture)

        logger.debug(
            f"Lease {lease.id}: {len(lease_furnitures)} furniture items "
            f"({len(apt_furniture)} apt - {len(all_tenant_furniture)} all tenants)"
        )

        return lease_furnitures

    @staticmethod
    def prepare_contract_context(lease: Lease) -> Dict[str, Any]:
        """
        Prepare the context dictionary for contract template rendering.

        Calculates all necessary data for the contract including dates,
        fees, furniture, lease details, and landlord information using
        other service classes.

        Args:
            lease: The lease object

        Returns:
            Dictionary containing all template variables including landlord

        Examples:
            >>> lease = Lease.objects.get(pk=1)
            >>> context = ContractService.prepare_contract_context(lease)
            >>> print(context['tenant'])  # Responsible tenant
            >>> print(context['landlord'])  # Active landlord
            >>> print(context['rental_value'])  # Monthly rent
        """
        from core.models import Landlord

        start_date = lease.start_date
        validity = lease.validity_months

        # Use DateCalculatorService for all date calculations
        formatted_dates = DateCalculatorService.format_lease_dates_for_contract(
            start_date=start_date, validity_months=validity
        )

        next_month_date = formatted_dates["next_month_date_formatted"]
        final_date = formatted_dates["final_date_formatted"]

        # Use FeeCalculatorService for fee calculations
        num_tenants = len(lease.tenants.all())
        valor_tags = FeeCalculatorService.calculate_tag_fee(num_tenants)
        valor_total = FeeCalculatorService.calculate_total_value(
            rental_value=lease.rental_value, cleaning_fee=lease.cleaning_fee, tag_fee=valor_tags
        )

        # Calculate lease furniture
        lease_furnitures = ContractService.calculate_lease_furniture(lease)

        # Get active landlord for contract
        landlord = Landlord.get_active()

        context = {
            "landlord": landlord,
            "tenant": lease.responsible_tenant,
            "building_number": lease.apartment.building.street_number,
            "apartment_number": lease.apartment.number,
            "furnitures": lease_furnitures,
            "validity": validity,
            "start_date": formatted_dates["start_date_formatted"],
            "final_date": final_date,
            "rental_value": lease.rental_value,
            "next_month_date": next_month_date,
            "tag_fee": lease.tag_fee,
            "cleaning_fee": lease.cleaning_fee,
            "valor_total": valor_total,
            "rules": regras_condominio,
            "lease": lease,
            "valor_tags": valor_tags,
        }

        logger.info(f"Prepared contract context for lease {lease.id}")
        return context

    @staticmethod
    def get_contract_relative_path(lease: Lease) -> str:
        """
        Calculate the relative path for a lease contract PDF.

        Path format: {building_number}/contract_apto_{apt_number}_{lease_id}.pdf

        Args:
            lease: The lease object

        Returns:
            Relative path for the PDF file

        Examples:
            >>> lease = Lease.objects.get(pk=1)
            >>> path = ContractService.get_contract_relative_path(lease)
            >>> print(path)  # '836/contract_apto_101_1.pdf'
        """
        building_number = lease.apartment.building.street_number
        apartment_number = lease.apartment.number
        relative_path = f"{building_number}/contract_apto_{apartment_number}_{lease.id}.pdf"

        logger.debug(f"Relative PDF path for lease {lease.id}: {relative_path}")
        return relative_path

    @staticmethod
    def get_contract_pdf_path(lease: Lease) -> str:
        """
        Calculate the full PDF output path for a lease contract (backward compatibility).

        DEPRECATED: This method is maintained for backward compatibility.
        New code should use get_contract_relative_path() with IDocumentStorage.

        Creates the directory structure if it doesn't exist.
        Path format: {PDF_OUTPUT_DIR}/{building_number}/contract_apto_{apt_number}_{lease_id}.pdf

        Args:
            lease: The lease object

        Returns:
            Absolute path to the PDF file

        Examples:
            >>> lease = Lease.objects.get(pk=1)
            >>> path = ContractService.get_contract_pdf_path(lease)
            >>> print(path)  # 'C:/path/contracts/836/contract_apto_101_1.pdf'
        """
        base_dir = settings.BASE_DIR
        contracts_dir = os.path.join(base_dir, settings.PDF_OUTPUT_DIR, str(lease.apartment.building.street_number))
        os.makedirs(contracts_dir, exist_ok=True)

        pdf_path = os.path.join(contracts_dir, f"contract_apto_{lease.apartment.number}_{lease.id}.pdf")

        logger.debug(f"PDF path for lease {lease.id}: {pdf_path}")
        return pdf_path

    @staticmethod
    def render_contract_template(context: Dict[str, Any]) -> str:
        """
        Render the contract HTML template with the given context.

        Uses Jinja2 template engine with custom filters for currency formatting
        and number-to-words conversion.

        Args:
            context: Template context dictionary

        Returns:
            Rendered HTML string

        Examples:
            >>> context = ContractService.prepare_contract_context(lease)
            >>> html = ContractService.render_contract_template(context)
            >>> assert '<html>' in html
        """
        template_path = os.path.join(settings.BASE_DIR, "core", "templates")
        env = Environment(loader=FileSystemLoader(template_path))
        env.filters["currency"] = format_currency
        env.filters["extenso"] = number_to_words

        template = env.get_template("contract_template.html")
        html_content = template.render(context)

        logger.debug("Contract template rendered successfully")
        return html_content

    async def generate_pdf_with_infrastructure(self, html_content: str, relative_path: str) -> str:
        """
        Generate PDF using IPDFGenerator and save using IDocumentStorage.

        Phase 4 Infrastructure: Uses injected PDF generator and document storage.

        Args:
            html_content: HTML content to convert to PDF
            relative_path: Relative path for the PDF file

        Returns:
            Full path or URL to the saved PDF document

        Raises:
            PDFGenerationError: If PDF generation fails
            StorageError: If document storage fails

        Examples:
            >>> service = ContractService()
            >>> html = "<html><body>Contract</body></html>"
            >>> path = await service.generate_pdf_with_infrastructure(html, "836/contract_1.pdf")
        """
        import tempfile

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name

        try:
            # Generate PDF using IPDFGenerator
            await self.pdf_generator.generate_pdf(html_content=html_content, output_path=temp_pdf_path, options=None)

            # Read PDF content
            pdf_content = Path(temp_pdf_path).read_bytes()

            # Save to storage using IDocumentStorage
            stored_path = self.document_storage.save(
                file_path=relative_path,
                content=pdf_content,
                metadata={"content-type": "application/pdf"},
            )

            logger.info(f"PDF generated and stored successfully: {stored_path}")
            return stored_path

        finally:
            # Clean up temporary file
            try:
                Path(temp_pdf_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete temporary PDF {temp_pdf_path}: {e}")

    @staticmethod
    async def generate_pdf_from_html(html_content: str, pdf_path: str, lease_id: int) -> None:
        """
        Generate PDF from HTML content using pyppeteer (backward compatibility).

        DEPRECATED: This method is maintained for backward compatibility.
        New code should use generate_pdf_with_infrastructure() with IPDFGenerator.

        Creates a temporary HTML file, opens it in headless Chrome,
        and generates a PDF. Cleans up the temporary file afterward.

        Args:
            html_content: The HTML string to convert to PDF
            pdf_path: Output path for the PDF file
            lease_id: Lease ID for temporary file naming

        Raises:
            Exception: If PDF generation fails

        Examples:
            >>> html = "<html><body>Contract</body></html>"
            >>> await ContractService.generate_pdf_from_html(html, "output.pdf", 1)
        """
        from pyppeteer import launch

        # Calculate contracts directory from pdf_path
        contracts_dir = os.path.dirname(pdf_path)

        browser = await launch(
            handleSIGINT=False,
            handleSIGTERM=False,
            handleSIGHUP=False,
            options={
                "pipe": "true",
                "executablePath": settings.CHROME_EXECUTABLE_PATH,
                "headless": True,
                "args": [
                    "--headless",
                    "--full-memory-crash-report",
                    "--unlimited-storage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                ],
            },
        )

        try:
            page = await browser.newPage()

            # Save temporary HTML file
            temp_html_path = os.path.join(contracts_dir, f"temp_contract_{lease_id}.html")
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Generate PDF
            file_url = f"file:///{temp_html_path}"
            await page.goto(file_url, {"waitUntil": "networkidle2"})
            await page.pdf({"path": pdf_path, "format": "A4"})

            # Clean up temporary file
            os.remove(temp_html_path)

            logger.info(f"PDF generated successfully for lease {lease_id}: {pdf_path}")
        finally:
            await browser.close()

    def generate_contract_with_infrastructure(self, lease: Lease) -> str:
        """
        Generate a complete PDF contract for a lease using infrastructure abstractions.

        Phase 4 Infrastructure: Uses IPDFGenerator and IDocumentStorage for flexibility.

        Main orchestration method that:
        1. Prepares contract context
        2. Renders HTML template
        3. Calculates relative path
        4. Generates PDF using IPDFGenerator
        5. Saves PDF using IDocumentStorage
        6. Updates lease status

        Args:
            lease: The lease object

        Returns:
            Path or URL to the generated PDF file

        Raises:
            PDFGenerationError: If PDF generation fails
            StorageError: If document storage fails

        Examples:
            >>> service = ContractService()
            >>> lease = Lease.objects.get(pk=1)
            >>> pdf_path = service.generate_contract_with_infrastructure(lease)
            >>> assert lease.contract_generated is True

            >>> # Using custom implementations
            >>> from core.infrastructure import WeasyPrintPDFGenerator
            >>> service = ContractService(pdf_generator=WeasyPrintPDFGenerator())
            >>> pdf_path = service.generate_contract_with_infrastructure(lease)
        """
        logger.info(f"Starting contract generation for lease {lease.id} (infrastructure mode)")

        # Prepare context
        context = self.prepare_contract_context(lease)

        # Render template
        html_content = self.render_contract_template(context)

        # Calculate relative path
        relative_path = self.get_contract_relative_path(lease)

        # Generate and store PDF (async operation using async_to_sync for ASGI compatibility)
        generate_pdf_sync = async_to_sync(self.generate_pdf_with_infrastructure)
        stored_path = generate_pdf_sync(html_content, relative_path)

        # Update lease status atomically
        with transaction.atomic():
            lease.refresh_from_db()
            lease.contract_generated = True
            lease.save(update_fields=["contract_generated"])

        logger.info(f"Contract generation complete for lease {lease.id}: {stored_path}")
        return stored_path

    @staticmethod
    def generate_contract(lease: Lease) -> str:
        """
        Generate a complete PDF contract for a lease (backward compatibility).

        DEPRECATED: This static method is maintained for backward compatibility.
        New code should use generate_contract_with_infrastructure() for better testability
        and flexibility (supports custom PDF generators and storage backends).

        Main orchestration method that:
        1. Prepares contract context
        2. Renders HTML template
        3. Calculates PDF output path
        4. Generates PDF from HTML (async with asyncio.run)
        5. Updates lease status

        Args:
            lease: The lease object

        Returns:
            Path to the generated PDF file

        Raises:
            Exception: If any step of contract generation fails

        Examples:
            >>> lease = Lease.objects.get(pk=1)
            >>> pdf_path = ContractService.generate_contract(lease)
            >>> assert os.path.exists(pdf_path)
            >>> assert lease.contract_generated is True
        """
        # Emit deprecation warning
        warnings.warn(
            "ContractService.generate_contract() is deprecated. "
            "Use ContractService().generate_contract_with_infrastructure() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        logger.info(f"Starting contract generation for lease {lease.id} (legacy mode)")

        # Prepare context
        context = ContractService.prepare_contract_context(lease)

        # Render template
        html_content = ContractService.render_contract_template(context)

        # Calculate output path
        pdf_path = ContractService.get_contract_pdf_path(lease)

        # Generate PDF (async operation using async_to_sync for ASGI compatibility)
        generate_pdf_sync = async_to_sync(ContractService.generate_pdf_from_html)
        generate_pdf_sync(html_content, pdf_path, lease.id)

        # Update lease status atomically
        with transaction.atomic():
            lease.refresh_from_db()
            lease.contract_generated = True
            lease.save(update_fields=["contract_generated"])

        logger.info(f"Contract generation complete for lease {lease.id}")
        return pdf_path
