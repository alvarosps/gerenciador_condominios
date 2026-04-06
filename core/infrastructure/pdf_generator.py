"""
PDF Generator abstraction for document generation.

Phase 4 Infrastructure: Strategy pattern for PDF generation.

Provides:
- PlaywrightPDFGenerator: Chrome-based PDF generation via Playwright

Usage:
    from core.infrastructure import IPDFGenerator, PlaywrightPDFGenerator

    generator: IPDFGenerator = PlaywrightPDFGenerator()
    pdf_path = generator.generate_pdf(html_content, output_path)
"""

import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class IPDFGenerator(ABC):
    """
    Abstract interface for PDF generation.

    Implementations must provide a method to generate PDF from HTML.
    This allows swapping PDF engines without changing business logic.
    """

    @abstractmethod
    def generate_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        options: dict | None = None,
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


class PlaywrightPDFGenerator(IPDFGenerator):
    """PDF generator using Playwright (Chrome headless)."""

    def __init__(self, chrome_path: str | None = None):
        self.chrome_path = chrome_path

    def generate_pdf(
        self,
        html_content: str,
        output_path: str | Path,
        options: dict | None = None,
    ) -> str:
        chrome_executable = self.chrome_path or getattr(settings, "CHROME_EXECUTABLE_PATH", None)

        logger.info(f"Generating PDF with Playwright: {output_path}")

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False, encoding="utf-8"
            ) as temp_html:
                temp_html.write(html_content)
                temp_html_path = temp_html.name

            try:
                with sync_playwright() as p:
                    launch_args: dict = {
                        "headless": True,
                        "args": ["--no-sandbox", "--disable-setuid-sandbox"],
                    }
                    if chrome_executable:
                        launch_args["executable_path"] = chrome_executable

                    browser = p.chromium.launch(**launch_args)
                    try:
                        page = browser.new_page()
                        page.goto(
                            f"file:///{temp_html_path}",
                            wait_until="networkidle",
                        )

                        pdf_options: dict = {
                            "path": str(output_path),
                            "format": "A4",
                            "print_background": True,
                            "prefer_css_page_size": False,
                            "margin": {
                                "top": "1cm",
                                "right": "1.5cm",
                                "bottom": "1cm",
                                "left": "1.5cm",
                            },
                        }
                        if options:
                            pdf_options.update(options)

                        page.pdf(**pdf_options)
                    finally:
                        browser.close()

                logger.info(f"PDF generated successfully: {output_path}")
                return str(output_path)

            finally:
                try:
                    Path(temp_html_path).unlink()
                except OSError as cleanup_err:
                    logger.warning(
                        f"Failed to delete temporary file {temp_html_path}: {cleanup_err}"
                    )

        except PDFGenerationError:
            raise
        except Exception as e:
            logger.exception("PDF generation failed")
            msg = f"Playwright PDF generation failed: {e}"
            raise PDFGenerationError(msg) from e


# Backward compatibility alias
PyppeteerPDFGenerator = PlaywrightPDFGenerator


class PDFGenerationError(Exception):
    """Exception raised when PDF generation fails."""
