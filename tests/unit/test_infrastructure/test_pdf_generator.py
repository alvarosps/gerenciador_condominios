"""
Unit tests for PDF generator implementations.

Tests both PyppeteerPDFGenerator and WeasyPrintPDFGenerator to ensure
they correctly implement the IPDFGenerator interface.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from core.infrastructure.pdf_generator import (
    IPDFGenerator,
    PDFGenerationError,
    PyppeteerPDFGenerator,
)

try:
    from core.infrastructure.pdf_generator import WeasyPrintPDFGenerator

    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


@pytest.mark.unit
@pytest.mark.infrastructure
class TestPyppeteerPDFGenerator:
    """Test suite for PyppeteerPDFGenerator."""

    @pytest.fixture
    def pdf_generator(self):
        """Create a PyppeteerPDFGenerator instance."""
        return PyppeteerPDFGenerator(chrome_path=None)

    @pytest.fixture
    def temp_output_file(self):
        """Create a temporary output file path."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_implements_interface(self, pdf_generator):
        """Test that PyppeteerPDFGenerator implements IPDFGenerator."""
        assert isinstance(pdf_generator, IPDFGenerator)

    def test_init_with_custom_chrome_path(self):
        """Test initialization with custom Chrome path."""
        chrome_path = "/custom/chrome/path"
        generator = PyppeteerPDFGenerator(chrome_path=chrome_path)
        assert generator.chrome_path == chrome_path

    def test_init_without_chrome_path(self):
        """Test initialization without Chrome path."""
        generator = PyppeteerPDFGenerator()
        assert generator.chrome_path is None

    @pytest.mark.asyncio
    async def test_generate_pdf_success(self, pdf_generator, temp_output_file):
        """Test successful PDF generation with mocked pyppeteer."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"

        # Mock pyppeteer browser and page
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.pdf = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.newPage = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        with patch("pyppeteer.launch", AsyncMock(return_value=mock_browser)):
            result = await pdf_generator.generate_pdf(html_content, temp_output_file)

            assert result == str(temp_output_file)
            mock_browser.newPage.assert_called_once()
            mock_page.goto.assert_called_once()
            mock_page.pdf.assert_called_once()
            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_pdf_with_options(self, pdf_generator, temp_output_file):
        """Test PDF generation with custom options."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"
        options = {"format": "A4", "margin": {"top": "1cm"}}

        # Mock pyppeteer
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.newPage = AsyncMock(return_value=mock_page)

        with patch("pyppeteer.launch", AsyncMock(return_value=mock_browser)):
            await pdf_generator.generate_pdf(html_content, temp_output_file, options=options)

            # Verify options were passed to pdf method
            call_args = mock_page.pdf.call_args
            assert call_args is not None
            assert "format" in call_args[0][0] or "format" in call_args[1]

    @pytest.mark.asyncio
    async def test_generate_pdf_browser_error(self, pdf_generator, temp_output_file):
        """Test PDF generation handles browser launch errors."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"

        with patch(
            "pyppeteer.launch",
            AsyncMock(side_effect=Exception("Browser launch failed")),
        ):
            with pytest.raises(PDFGenerationError, match="Pyppeteer PDF generation failed"):
                await pdf_generator.generate_pdf(html_content, temp_output_file)

    @pytest.mark.asyncio
    async def test_generate_pdf_cleans_up_on_error(self, pdf_generator, temp_output_file):
        """Test that browser is closed even if PDF generation fails."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"

        mock_page = AsyncMock()
        mock_page.pdf = AsyncMock(side_effect=Exception("PDF generation failed"))

        mock_browser = AsyncMock()
        mock_browser.newPage = AsyncMock(return_value=mock_page)

        with patch("pyppeteer.launch", AsyncMock(return_value=mock_browser)):
            with pytest.raises(PDFGenerationError):
                await pdf_generator.generate_pdf(html_content, temp_output_file)

            # Verify browser was closed despite error
            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_pdf_creates_directory(self, pdf_generator):
        """Test that parent directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "test.pdf"
            html_content = "<html><body><h1>Test PDF</h1></body></html>"

            # Mock pyppeteer
            mock_page = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.newPage = AsyncMock(return_value=mock_page)

            with patch("pyppeteer.launch", AsyncMock(return_value=mock_browser)):
                await pdf_generator.generate_pdf(html_content, str(output_path))

                # Verify directory was created
                assert output_path.parent.exists()


@pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint not installed")
@pytest.mark.unit
@pytest.mark.infrastructure
class TestWeasyPrintPDFGenerator:
    """Test suite for WeasyPrintPDFGenerator."""

    @pytest.fixture
    def pdf_generator(self):
        """Create a WeasyPrintPDFGenerator instance."""
        return WeasyPrintPDFGenerator()

    @pytest.fixture
    def temp_output_file(self):
        """Create a temporary output file path."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    def test_implements_interface(self, pdf_generator):
        """Test that WeasyPrintPDFGenerator implements IPDFGenerator."""
        assert isinstance(pdf_generator, IPDFGenerator)

    @pytest.mark.asyncio
    async def test_generate_pdf_success(self, pdf_generator, temp_output_file):
        """Test successful PDF generation with mocked WeasyPrint."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"

        # Mock WeasyPrint HTML object
        mock_document = MagicMock()
        mock_html = MagicMock()
        mock_html.render = MagicMock(return_value=[mock_document])

        with patch("weasyprint.HTML", return_value=mock_html):
            result = await pdf_generator.generate_pdf(html_content, temp_output_file)

            assert result == str(temp_output_file)
            mock_html.render.assert_called_once()
            mock_document.write_pdf.assert_called_once_with(str(temp_output_file))

    @pytest.mark.asyncio
    async def test_generate_pdf_weasyprint_error(self, pdf_generator, temp_output_file):
        """Test PDF generation handles WeasyPrint errors."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"

        with patch(
            "weasyprint.HTML", side_effect=Exception("WeasyPrint failed")
        ):
            with pytest.raises(PDFGenerationError, match="WeasyPrint PDF generation failed"):
                await pdf_generator.generate_pdf(html_content, temp_output_file)

    @pytest.mark.asyncio
    async def test_generate_pdf_creates_directory(self, pdf_generator):
        """Test that parent directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "subdir" / "test.pdf"
            html_content = "<html><body><h1>Test PDF</h1></body></html>"

            # Mock WeasyPrint
            mock_document = MagicMock()
            mock_html = MagicMock()
            mock_html.render = MagicMock(return_value=[mock_document])

            with patch("weasyprint.HTML", return_value=mock_html):
                await pdf_generator.generate_pdf(html_content, str(output_path))

                # Verify directory was created
                assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_generate_pdf_with_base_url(self, pdf_generator, temp_output_file):
        """Test PDF generation with base URL option."""
        html_content = "<html><body><h1>Test PDF</h1></body></html>"
        options = {"base_url": "https://example.com"}

        # Mock WeasyPrint
        mock_document = MagicMock()
        mock_html = MagicMock()
        mock_html.render = MagicMock(return_value=[mock_document])

        with patch("weasyprint.HTML", return_value=mock_html) as mock_html_class:
            await pdf_generator.generate_pdf(html_content, temp_output_file, options=options)

            # Verify base_url was passed to HTML constructor
            call_args = mock_html_class.call_args
            assert "base_url" in call_args[1]
            assert call_args[1]["base_url"] == "https://example.com"


@pytest.mark.unit
@pytest.mark.infrastructure
class TestPDFGeneratorComparison:
    """Comparison tests between PDF generators."""

    @pytest.fixture
    def pyppeteer_generator(self):
        """Create a PyppeteerPDFGenerator instance."""
        return PyppeteerPDFGenerator()

    @pytest.fixture
    def weasyprint_generator(self):
        """Create a WeasyPrintPDFGenerator instance."""
        return WeasyPrintPDFGenerator()

    def test_both_implement_interface(self, pyppeteer_generator, weasyprint_generator):
        """Test that both generators implement the same interface."""
        assert isinstance(pyppeteer_generator, IPDFGenerator)
        assert isinstance(weasyprint_generator, IPDFGenerator)

    def test_both_have_generate_pdf_method(self, pyppeteer_generator, weasyprint_generator):
        """Test that both generators have generate_pdf method with same signature."""
        assert hasattr(pyppeteer_generator, "generate_pdf")
        assert hasattr(weasyprint_generator, "generate_pdf")

        # Check method signatures are compatible
        import inspect

        pyppeteer_sig = inspect.signature(pyppeteer_generator.generate_pdf)
        weasyprint_sig = inspect.signature(weasyprint_generator.generate_pdf)

        assert len(pyppeteer_sig.parameters) == len(weasyprint_sig.parameters)
