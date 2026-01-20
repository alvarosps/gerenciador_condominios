"""
PDF Generator abstraction for document generation.

Phase 4 Infrastructure: Strategy pattern for PDF generation.

Provides multiple implementations:
- PyppeteerPDFGenerator: Chrome-based PDF generation (current)
- WeasyPrintPDFGenerator: Pure-Python PDF generation (alternative)

Usage:
    from core.infrastructure import IPDFGenerator, PyppeteerPDFGenerator

    generator: IPDFGenerator = PyppeteerPDFGenerator()
    pdf_path = await generator.generate_pdf(html_content, output_path)
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IPDFGenerator(ABC):
    """
    Abstract interface for PDF generation.

    Implementations must provide a method to generate PDF from HTML.
    This allows swapping PDF engines without changing business logic.
    """

    @abstractmethod
    async def generate_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        options: Optional[dict] = None,
    ) -> str:
        """
        Generate a PDF file from HTML content.

        Args:
            html_content: HTML string to convert to PDF
            output_path: Path where PDF should be saved
            options: Engine-specific options (optional)

        Returns:
            str: Path to the generated PDF file

        Raises:
            PDFGenerationError: If PDF generation fails
        """
        pass


class PyppeteerPDFGenerator(IPDFGenerator):
    """
    PDF generator using Pyppeteer (Chrome headless).

    Pros:
    - Excellent CSS support
    - Handles complex layouts
    - Supports modern web features

    Cons:
    - Requires Chrome/Chromium installed
    - Slower (3-5s per document)
    - Higher resource usage
    """

    def __init__(self, chrome_path: Optional[str] = None):
        """
        Initialize Pyppeteer PDF generator.

        Args:
            chrome_path: Path to Chrome/Chromium executable (optional)
        """
        self.chrome_path = chrome_path

    async def generate_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        options: Optional[dict] = None,
    ) -> str:
        """
        Generate PDF using Chrome headless via Pyppeteer.

        Args:
            html_content: HTML content to convert
            output_path: Output PDF file path
            options: Pyppeteer-specific options

        Returns:
            str: Path to generated PDF

        Raises:
            PDFGenerationError: If PDF generation fails
        """
        import tempfile

        from django.conf import settings

        from pyppeteer import launch

        logger.info(f"Generating PDF with Pyppeteer: {output_path}")

        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Use Windows event loop policy on Windows
            import sys

            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            # Get Chrome path from settings or constructor
            chrome_executable = self.chrome_path or getattr(settings, "CHROME_EXECUTABLE_PATH", None)

            if not chrome_executable:
                raise ValueError("Chrome executable path not configured")

            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name

            browser = None
            try:
                # Launch browser
                browser = await launch(
                    executablePath=chrome_executable,
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"],
                )

                # Create page and generate PDF
                page = await browser.newPage()
                await page.goto(
                    f"file://{temp_html_path}",
                    {"waitUntil": "networkidle0"},
                )

                # Merge default options with custom options
                # Centered margins for better layout
                pdf_options = {
                    "path": str(output_path),
                    "format": "A4",
                    "printBackground": True,
                    "preferCSSPageSize": False,
                    "margin": {
                        "top": "1cm",
                        "right": "1.5cm",
                        "bottom": "1cm",
                        "left": "1.5cm"
                    },
                }
                if options:
                    pdf_options.update(options)

                await page.pdf(pdf_options)

                logger.info(f"PDF generated successfully: {output_path}")
                return str(output_path)

            finally:
                # Close browser if it was launched
                if browser:
                    await browser.close()

                # Clean up temporary file
                import os

                try:
                    os.unlink(temp_html_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_html_path}: {e}")

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise PDFGenerationError(f"Pyppeteer PDF generation failed: {e}") from e


class WeasyPrintPDFGenerator(IPDFGenerator):
    """
    PDF generator using WeasyPrint (pure Python).

    Pros:
    - No Chrome dependency
    - Faster (500ms-1s per document)
    - Lower resource usage
    - Pure Python (easier deployment)

    Cons:
    - Limited CSS support (subset of CSS)
    - May not handle complex layouts as well
    - No JavaScript support

    Note: Requires WeasyPrint package (not installed by default).
    Install with: pip install weasyprint
    """

    async def generate_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        options: Optional[dict] = None,
    ) -> str:
        """
        Generate PDF using WeasyPrint.

        Args:
            html_content: HTML content to convert
            output_path: Output PDF file path
            options: WeasyPrint-specific options (e.g., stylesheets)

        Returns:
            str: Path to generated PDF

        Raises:
            PDFGenerationError: If PDF generation fails or WeasyPrint not installed
        """
        logger.info(f"Generating PDF with WeasyPrint: {output_path}")

        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            from weasyprint import CSS, HTML
        except ImportError:
            raise PDFGenerationError("WeasyPrint not installed. Install with: pip install weasyprint")

        try:
            # Prepare options
            stylesheets = []
            if options and "stylesheets" in options:
                for stylesheet_path in options["stylesheets"]:
                    stylesheets.append(CSS(filename=stylesheet_path))

            # Generate PDF
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(
                str(output_path),
                stylesheets=stylesheets,
            )

            logger.info(f"PDF generated successfully: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise PDFGenerationError(f"Failed to generate PDF: {e}") from e


class PDFGenerationError(Exception):
    """Exception raised when PDF generation fails."""

    pass
