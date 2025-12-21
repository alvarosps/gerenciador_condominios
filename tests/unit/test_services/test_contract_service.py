"""
Unit tests for ContractService.

Tests all contract generation business logic with mocked PDF generation.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, call, MagicMock
import os

from core.services.contract_service import ContractService
from core.models import Building, Apartment, Tenant, Lease, Furniture


@pytest.fixture
def building():
    """Create a test building."""
    return Building.objects.create(
        street_number=836,
        name="Test Building",
        address="Test Street, 836"
    )


@pytest.fixture
def furniture_items():
    """Create test furniture items."""
    bed = Furniture.objects.create(name="Bed")
    table = Furniture.objects.create(name="Table")
    chair = Furniture.objects.create(name="Chair")
    sofa = Furniture.objects.create(name="Sofa")
    return {'bed': bed, 'table': table, 'chair': chair, 'sofa': sofa}


@pytest.fixture
def apartment(building, furniture_items):
    """Create a test apartment with furniture."""
    apt = Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        max_tenants=2
    )
    # Apartment has bed, table, chair
    apt.furnitures.add(furniture_items['bed'], furniture_items['table'], furniture_items['chair'])
    return apt


@pytest.fixture
def tenant(furniture_items):
    """Create a test tenant with own furniture."""
    tenant = Tenant.objects.create(
        name="John Doe",
        cpf_cnpj="12345678901",
        phone="11999999999",
        marital_status="Single",
        profession="Engineer"
    )
    # Tenant brings their own chair
    tenant.furnitures.add(furniture_items['chair'])
    return tenant


@pytest.fixture
def lease(apartment, tenant):
    """Create a test lease."""
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2025, 1, 15),
        validity_months=12,
        due_day=10,
        rental_value=Decimal('1500.00'),
        cleaning_fee=Decimal('200.00'),
        tag_fee=Decimal('50.00'),
        contract_generated=False
    )
    lease.tenants.add(tenant)
    return lease


@pytest.mark.django_db
class TestCalculateLeaseFurniture:
    """Test furniture calculation for leases."""

    def test_calculate_lease_furniture_standard(self, lease, furniture_items):
        """Test furniture calculation with standard case."""
        # Apartment has: bed, table, chair
        # Tenant has: chair
        # Lease should have: bed, table
        furniture = ContractService.calculate_lease_furniture(lease)
        furniture_names = [f.name for f in furniture]

        assert len(furniture) == 2
        assert 'Bed' in furniture_names
        assert 'Table' in furniture_names
        assert 'Chair' not in furniture_names

    def test_calculate_lease_furniture_tenant_no_furniture(self, lease, tenant, furniture_items):
        """Test when tenant brings no furniture."""
        # Remove tenant's furniture
        tenant.furnitures.clear()

        # All apartment furniture should be in lease
        furniture = ContractService.calculate_lease_furniture(lease)
        furniture_names = [f.name for f in furniture]

        assert len(furniture) == 3
        assert 'Bed' in furniture_names
        assert 'Table' in furniture_names
        assert 'Chair' in furniture_names

    def test_calculate_lease_furniture_tenant_has_all(self, lease, apartment, tenant, furniture_items):
        """Test when tenant brings all apartment furniture."""
        # Tenant has all apartment furniture
        tenant.furnitures.add(furniture_items['bed'], furniture_items['table'])

        # No apartment furniture in lease
        furniture = ContractService.calculate_lease_furniture(lease)

        assert len(furniture) == 0

    def test_calculate_lease_furniture_empty_apartment(self, lease, apartment):
        """Test when apartment has no furniture."""
        # Remove all apartment furniture
        apartment.furnitures.clear()

        furniture = ContractService.calculate_lease_furniture(lease)

        assert len(furniture) == 0


@pytest.mark.django_db
class TestPrepareContractContext:
    """Test contract context preparation."""

    def test_prepare_contract_context_standard(self, lease):
        """Test context preparation with standard lease."""
        context = ContractService.prepare_contract_context(lease)

        # Verify all required keys are present
        assert 'tenant' in context
        assert 'building_number' in context
        assert 'apartment_number' in context
        assert 'furnitures' in context
        assert 'validity' in context
        assert 'start_date' in context
        assert 'final_date' in context
        assert 'rental_value' in context
        assert 'next_month_date' in context
        assert 'tag_fee' in context
        assert 'cleaning_fee' in context
        assert 'valor_total' in context
        assert 'rules' in context
        assert 'lease' in context
        assert 'valor_tags' in context

    def test_prepare_contract_context_values(self, lease):
        """Test context values are correct."""
        context = ContractService.prepare_contract_context(lease)

        # Verify basic values
        assert context['tenant'] == lease.responsible_tenant
        assert context['building_number'] == 836
        assert context['apartment_number'] == 101
        assert context['validity'] == 12
        assert context['rental_value'] == Decimal('1500.00')
        assert context['tag_fee'] == Decimal('50.00')
        assert context['cleaning_fee'] == Decimal('200.00')

    def test_prepare_contract_context_date_formatting(self, lease):
        """Test that dates are formatted correctly."""
        context = ContractService.prepare_contract_context(lease)

        # Verify Brazilian date format (DD/MM/YYYY)
        assert context['start_date'] == "15/01/2025"
        assert context['next_month_date'] == "15/02/2025"
        assert context['final_date'] == "15/01/2026"

    def test_prepare_contract_context_fee_calculations(self, lease):
        """Test that fees are calculated correctly."""
        context = ContractService.prepare_contract_context(lease)

        # Tag fee for 1 tenant should be 50
        assert context['valor_tags'] == Decimal('50.00')

        # Total = rental + cleaning + tags = 1500 + 200 + 50 = 1750
        assert context['valor_total'] == Decimal('1750.00')

    def test_prepare_contract_context_multiple_tenants(self, lease, tenant):
        """Test context with multiple tenants."""
        # Add another tenant
        tenant2 = Tenant.objects.create(
            name="Jane Doe",
            cpf_cnpj="98765432109",
            phone="11988888888",
            marital_status="Single",
            profession="Doctor"
        )
        lease.tenants.add(tenant2)

        context = ContractService.prepare_contract_context(lease)

        # Tag fee for 2+ tenants should be 80
        assert context['valor_tags'] == Decimal('80.00')

        # Total = 1500 + 200 + 80 = 1780
        assert context['valor_total'] == Decimal('1780.00')


@pytest.mark.django_db
class TestGetContractPdfPath:
    """Test PDF path calculation."""

    def test_get_contract_pdf_path_format(self, lease, settings, tmp_path):
        """Test PDF path format is correct."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        pdf_path = ContractService.get_contract_pdf_path(lease)

        # Verify path components rather than exact match (handles Windows/Linux differences)
        assert "contracts" in pdf_path
        assert "836" in pdf_path
        assert f"contract_apto_101_{lease.id}.pdf" in pdf_path

    def test_get_contract_pdf_path_creates_directory(self, lease, settings, tmp_path):
        """Test that directory is created if it doesn't exist."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        pdf_path = ContractService.get_contract_pdf_path(lease)

        # Verify directory was created
        contracts_dir = tmp_path / "contracts" / "836"
        assert contracts_dir.exists()
        assert contracts_dir.is_dir()

    def test_get_contract_pdf_path_different_buildings(self, lease, settings):
        """Test PDF paths for different buildings."""
        settings.BASE_DIR = "/base"
        settings.PDF_OUTPUT_DIR = "contracts"

        # Change building number
        lease.apartment.building.street_number = 850
        lease.apartment.building.save()

        pdf_path = ContractService.get_contract_pdf_path(lease)

        assert "850" in pdf_path
        assert "836" not in pdf_path


@pytest.mark.django_db
class TestRenderContractTemplate:
    """Test contract template rendering."""

    @patch('core.services.contract_service.Environment')
    def test_render_contract_template_standard(self, mock_env_class, lease):
        """Test template rendering with standard context."""
        # Mock the Jinja2 environment
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Contract</html>"
        mock_env.get_template.return_value = mock_template
        # Make filters a dict-like object
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        # Verify template was loaded and rendered
        mock_env.get_template.assert_called_once_with('contract_template.html')
        mock_template.render.assert_called_once_with(context)
        assert html == "<html>Contract</html>"

    @patch('core.services.contract_service.Environment')
    def test_render_contract_template_filters_registered(self, mock_env_class):
        """Test that custom filters are registered."""
        mock_env = Mock()
        mock_template = Mock()
        mock_template.render.return_value = "<html>Test</html>"
        mock_env.get_template.return_value = mock_template
        # Make filters a dict-like object
        mock_env.filters = {}
        mock_env_class.return_value = mock_env

        ContractService.render_contract_template({})

        # Verify filters were set
        assert 'currency' in mock_env.filters
        assert 'extenso' in mock_env.filters


@pytest.mark.django_db
@pytest.mark.asyncio
class TestGeneratePdfFromHtml:
    """Test PDF generation from HTML."""

    async def test_generate_pdf_from_html_mocked(self, tmp_path):
        """Test PDF generation with mocked pyppeteer."""
        # Mock pyppeteer
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            html_content = "<html><body>Test Contract</body></html>"
            pdf_path = str(tmp_path / "test_contract.pdf")

            await ContractService.generate_pdf_from_html(html_content, pdf_path, 1)

            # Verify browser was launched
            mock_browser.newPage.assert_called_once()

            # Verify page operations
            mock_page.goto.assert_called_once()
            mock_page.pdf.assert_called_once()

            # Verify browser was closed
            mock_browser.close.assert_called_once()

    async def test_generate_pdf_from_html_browser_args(self, tmp_path, settings):
        """Test that browser is launched with correct arguments."""
        settings.CHROME_EXECUTABLE_PATH = '/usr/bin/chrome'

        mock_launch = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page
        mock_launch.return_value = mock_browser

        with patch('pyppeteer.launch', mock_launch):
            html_content = "<html>Test</html>"
            pdf_path = str(tmp_path / "test.pdf")

            await ContractService.generate_pdf_from_html(html_content, pdf_path, 1)

            # Verify launch was called with correct args
            mock_launch.assert_called_once()
            call_kwargs = mock_launch.call_args[1]

            assert call_kwargs['handleSIGINT'] is False
            assert call_kwargs['handleSIGTERM'] is False
            assert call_kwargs['handleSIGHUP'] is False
            assert call_kwargs['options']['executablePath'] == '/usr/bin/chrome'
            assert call_kwargs['options']['headless'] is True
            assert '--no-sandbox' in call_kwargs['options']['args']

    async def test_generate_pdf_from_html_temp_file_cleanup(self, tmp_path):
        """Test that temporary HTML file is created and cleaned up."""
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            html_content = "<html>Test</html>"
            pdf_path = str(tmp_path / "test.pdf")

            await ContractService.generate_pdf_from_html(html_content, pdf_path, 123)

            # Verify temp file was created and deleted
            # (Since it's deleted in the function, we can't check existence)
            # Instead, verify that open was called with temp path
            mock_page.goto.assert_called_once()
            goto_url = mock_page.goto.call_args[0][0]
            assert 'temp_contract_123.html' in goto_url

    async def test_generate_pdf_from_html_browser_closes_on_error(self, tmp_path):
        """Test that browser is closed even if PDF generation fails."""
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.pdf.side_effect = Exception("PDF generation failed")
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            html_content = "<html>Test</html>"
            pdf_path = str(tmp_path / "test.pdf")

            with pytest.raises(Exception, match="PDF generation failed"):
                await ContractService.generate_pdf_from_html(html_content, pdf_path, 1)

            # Verify browser was closed despite error
            mock_browser.close.assert_called_once()


@pytest.mark.django_db
class TestGenerateContract:
    """Test complete contract generation flow."""

    def test_generate_contract_integration(self, lease, tmp_path, settings):
        """Test complete contract generation with mocked PDF."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        # Mock PDF generation and template rendering
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            with patch('core.services.contract_service.ContractService.render_contract_template', return_value="<html>Test</html>"):
                pdf_path = ContractService.generate_contract(lease)

                # Verify PDF path is correct
                assert "contract_apto_101" in pdf_path
                assert "836" in pdf_path

                # Verify lease status was updated
                lease.refresh_from_db()
                assert lease.contract_generated is True

                # Verify PDF generation was called
                mock_page.pdf.assert_called_once()

    def test_generate_contract_updates_lease_status(self, lease, tmp_path, settings):
        """Test that contract generation updates lease status."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        # Verify initial state
        assert lease.contract_generated is False

        # Mock PDF generation and template rendering
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            with patch('core.services.contract_service.ContractService.render_contract_template', return_value="<html>Test</html>"):
                ContractService.generate_contract(lease)

                # Verify status changed
                lease.refresh_from_db()
                assert lease.contract_generated is True

    def test_generate_contract_calls_services(self, lease, tmp_path, settings):
        """Test that contract generation uses other services."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        # Mock PDF generation and template rendering
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.newPage.return_value = mock_page

        with patch('pyppeteer.launch', return_value=mock_browser):
            with patch('core.services.contract_service.ContractService.render_contract_template', return_value="<html>Test</html>"):
                with patch('core.services.contract_service.DateCalculatorService.format_lease_dates_for_contract') as mock_date_service:
                    with patch('core.services.contract_service.FeeCalculatorService.calculate_tag_fee') as mock_fee_service:
                        # Set up return values
                        mock_date_service.return_value = {
                            'start_date_formatted': '15/01/2025',
                            'next_month_date_formatted': '15/02/2025',
                            'final_date_formatted': '15/01/2026'
                        }
                        mock_fee_service.return_value = Decimal('50.00')

                        ContractService.generate_contract(lease)

                        # Verify services were called
                        mock_date_service.assert_called_once()
                        mock_fee_service.assert_called_once()


@pytest.mark.django_db
class TestContractServiceIntegration:
    """Integration tests for ContractService."""

    def test_complete_contract_context_flow(self, lease, furniture_items):
        """Test complete flow from lease to contract context."""
        # This tests the integration of all context preparation methods
        context = ContractService.prepare_contract_context(lease)

        # Verify tenant information
        assert context['tenant'].name == "John Doe"
        assert context['building_number'] == 836
        assert context['apartment_number'] == 101

        # Verify dates are formatted
        assert '/' in context['start_date']
        assert '/' in context['next_month_date']
        assert '/' in context['final_date']

        # Verify fees are calculated
        assert context['valor_tags'] == Decimal('50.00')
        assert context['valor_total'] == Decimal('1750.00')

        # Verify furniture calculation
        furniture_names = [f.name for f in context['furnitures']]
        assert 'Bed' in furniture_names
        assert 'Table' in furniture_names
        assert 'Chair' not in furniture_names  # Tenant's furniture

    def test_pdf_path_consistency(self, lease, settings, tmp_path):
        """Test that PDF path is consistent across calls."""
        settings.BASE_DIR = str(tmp_path)
        settings.PDF_OUTPUT_DIR = "contracts"

        path1 = ContractService.get_contract_pdf_path(lease)
        path2 = ContractService.get_contract_pdf_path(lease)

        assert path1 == path2

    def test_context_contains_all_lease_data(self, lease):
        """Test that context contains all necessary lease data."""
        context = ContractService.prepare_contract_context(lease)

        # Verify all critical lease data is present
        assert context['lease'].id == lease.id
        assert context['rental_value'] == lease.rental_value
        assert context['cleaning_fee'] == lease.cleaning_fee
        assert context['tag_fee'] == lease.tag_fee
        assert context['validity'] == lease.validity_months
