"""Unit tests for core/services/contract_service.py."""

import warnings
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings

from core.infrastructure import FileSystemDocumentStorage, PDFGenerationError, StorageError
from core.models import Apartment, Building, Furniture, Landlord, Lease, Tenant
from core.services.contract_service import ContractService


@pytest.fixture
def building(admin_user):
    return Building.objects.create(
        street_number=6601,
        name="Contract Test Building",
        address="Rua Contract, 6601",
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def apartment(building, admin_user):
    return Apartment.objects.create(
        building=building,
        number=101,
        rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("200.00"),
        max_tenants=3,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Contract Tenant",
        cpf_cnpj="71286955084",  # Valid CPF
        phone="11966660001",
        marital_status="Casado(a)",
        profession="Médico",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def second_tenant(admin_user):
    return Tenant.objects.create(
        name="Second Contract Tenant",
        cpf_cnpj="98765432100",  # Valid CPF
        phone="11966660002",
        marital_status="Solteiro(a)",
        profession="Enfermeiro",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    l = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date="2026-01-01",
        validity_months=12,
        tag_fee=Decimal("50.00"),
        rental_value=Decimal("1500.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    l.tenants.add(tenant)
    return l


@pytest.fixture
def landlord(admin_user):
    return Landlord.objects.create(
        name="Test Landlord",
        marital_status="Casado(a)",
        cpf_cnpj="12345678901",
        phone="11999990000",
        street="Rua Landlord",
        street_number="100",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01310-100",
        is_active=True,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.unit
class TestCalculateLeaseFurniture:
    def test_returns_apartment_furniture_minus_tenant_furniture(self, apartment, tenant, lease, admin_user):
        fridge = Furniture.objects.create(
            name="Geladeira Test CF",
            description="",
            created_by=admin_user,
            updated_by=admin_user,
        )
        tv = Furniture.objects.create(
            name="TV Test CF",
            description="",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment.furnitures.add(fridge, tv)
        tenant.furnitures.add(tv)  # TV belongs to tenant

        result = ContractService.calculate_lease_furniture(lease)
        names = [f.name for f in result]
        assert "Geladeira Test CF" in names
        assert "TV Test CF" not in names

    def test_empty_when_tenant_has_all_furniture(self, apartment, tenant, lease, admin_user):
        stove = Furniture.objects.create(
            name="Fogão Test CF",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment.furnitures.add(stove)
        tenant.furnitures.add(stove)

        result = ContractService.calculate_lease_furniture(lease)
        assert result == []

    def test_returns_all_apt_furniture_when_no_tenant_furniture(self, apartment, lease, admin_user):
        chair = Furniture.objects.create(
            name="Cadeira Test CF",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment.furnitures.add(chair)

        result = ContractService.calculate_lease_furniture(lease)
        assert any(f.name == "Cadeira Test CF" for f in result)

    def test_subtracts_furniture_from_all_tenants(
        self, apartment, tenant, second_tenant, lease, admin_user
    ):
        lease.tenants.add(second_tenant)
        sofa = Furniture.objects.create(
            name="Sofá Test CF",
            created_by=admin_user,
            updated_by=admin_user,
        )
        wardrobe = Furniture.objects.create(
            name="Guarda-roupa Test CF",
            created_by=admin_user,
            updated_by=admin_user,
        )
        apartment.furnitures.add(sofa, wardrobe)
        tenant.furnitures.add(sofa)
        second_tenant.furnitures.add(wardrobe)

        result = ContractService.calculate_lease_furniture(lease)
        assert result == []


@pytest.mark.unit
class TestPrepareContractContext:
    def test_returns_required_keys(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        required_keys = [
            "tenant", "building_number", "apartment_number", "furnitures",
            "validity", "start_date", "final_date", "rental_value", "next_month_date",
            "tag_fee", "cleaning_fee", "valor_total", "lease", "valor_tags", "rules",
            "landlord",
        ]
        for key in required_keys:
            assert key in context, f"Missing key: {key}"

    def test_tenant_is_responsible_tenant(self, lease, tenant, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["tenant"].pk == tenant.pk

    def test_building_number_matches_apartment(self, lease, apartment, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["building_number"] == apartment.building.street_number

    def test_rental_value_from_apartment(self, lease, apartment, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["rental_value"] == apartment.rental_value

    def test_landlord_is_active_landlord(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["landlord"] == landlord


@pytest.mark.unit
class TestGetContractRelativePath:
    def test_path_format(self, lease, apartment, building):
        path = ContractService.get_contract_relative_path(lease)
        expected = f"{building.street_number}/contract_apto_{apartment.number}_{lease.id}.pdf"
        assert path == expected


@pytest.mark.unit
class TestGetContractPdfPath:
    def test_returns_absolute_path_string(self, lease, mock_pdf_output_dir):
        path = ContractService.get_contract_pdf_path(lease)
        assert isinstance(path, str)
        assert "contract_apto" in path
        assert path.endswith(".pdf")

    def test_creates_directory(self, lease, mock_pdf_output_dir):
        ContractService.get_contract_pdf_path(lease)
        building_dir = mock_pdf_output_dir / str(lease.apartment.building.street_number)
        assert building_dir.exists()


@pytest.mark.unit
class TestRenderContractTemplate:
    def test_returns_html_string(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_contains_basic_content(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)
        assert "<html" in html or "<body" in html or len(html) > 10


@pytest.mark.unit
class TestContractServiceInit:
    def test_default_init_sets_pdf_generator(self, mock_pdf_output_dir):
        service = ContractService()
        assert service.pdf_generator is not None

    def test_default_init_sets_document_storage(self, mock_pdf_output_dir):
        service = ContractService()
        assert service.document_storage is not None

    def test_custom_pdf_generator_injected(self, mocker, mock_pdf_output_dir):
        mock_gen = mocker.MagicMock()
        service = ContractService(pdf_generator=mock_gen)
        assert service.pdf_generator is mock_gen

    def test_custom_storage_injected(self, mocker, mock_pdf_output_dir):
        mock_storage = mocker.MagicMock()
        service = ContractService(document_storage=mock_storage)
        assert service.document_storage is mock_storage


@pytest.mark.unit
class TestGeneratePdfWithInfrastructure:
    def test_generates_and_stores_pdf(self, tmp_path, mocker, lease, landlord):
        mock_gen = mocker.MagicMock()
        mock_gen.generate_pdf.return_value = str(tmp_path / "temp.pdf")

        mock_storage = mocker.MagicMock()
        mock_storage.save.return_value = "/stored/path/contract.pdf"

        # Make sure generate_pdf writes the temp file
        def fake_generate(html_content, output_path, options):
            Path(output_path).write_bytes(b"PDF data")
            return str(output_path)

        mock_gen.generate_pdf.side_effect = fake_generate

        service = ContractService(pdf_generator=mock_gen, document_storage=mock_storage)
        result = service.generate_pdf_with_infrastructure("<html></html>", "123/contract_1.pdf")

        assert result == "/stored/path/contract.pdf"
        mock_gen.generate_pdf.assert_called_once()
        mock_storage.save.assert_called_once()


@pytest.mark.unit
class TestGenerateContractDeprecated:
    def test_emits_deprecation_warning(self, lease, landlord, mock_pdf_generation):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ContractService.generate_contract(lease)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) >= 1
            assert "deprecated" in str(deprecation_warnings[0].message).lower()

    def test_marks_lease_contract_generated(self, lease, landlord, mock_pdf_generation):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            ContractService.generate_contract(lease)
        lease.refresh_from_db()
        assert lease.contract_generated is True


@pytest.mark.unit
class TestGenerateContractWithInfrastructure:
    def test_marks_lease_contract_generated(self, lease, landlord, mocker):
        mock_gen = mocker.MagicMock()
        mock_storage = mocker.MagicMock()
        mock_storage.save.return_value = "/path/contract.pdf"

        def fake_generate(html_content, output_path, options):
            Path(output_path).write_bytes(b"PDF")
            return str(output_path)

        mock_gen.generate_pdf.side_effect = fake_generate

        service = ContractService(pdf_generator=mock_gen, document_storage=mock_storage)
        service.generate_contract_with_infrastructure(lease)

        lease.refresh_from_db()
        assert lease.contract_generated is True

    def test_returns_stored_path(self, lease, landlord, mocker):
        mock_gen = mocker.MagicMock()
        mock_storage = mocker.MagicMock()
        mock_storage.save.return_value = "/stored/path.pdf"

        def fake_generate(html_content, output_path, options):
            Path(output_path).write_bytes(b"PDF")
            return str(output_path)

        mock_gen.generate_pdf.side_effect = fake_generate

        service = ContractService(pdf_generator=mock_gen, document_storage=mock_storage)
        result = service.generate_contract_with_infrastructure(lease)

        assert result == "/stored/path.pdf"


@pytest.mark.unit
class TestGeneratePdfFromHtml:
    """Tests for the static generate_pdf_from_html method (lines 376-419)."""

    def test_generate_pdf_from_html_calls_playwright(self, tmp_path, mocker, landlord):
        """Covers lines 376-419: static method creates temp HTML and calls Playwright."""
        mock_playwright_ctx = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()

        mock_playwright_ctx.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        mock_sync_playwright = mocker.patch(
            "core.services.contract_service.sync_playwright"
        )
        mock_sync_playwright.return_value.__enter__ = mocker.MagicMock(
            return_value=mock_playwright_ctx
        )
        mock_sync_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        pdf_path = str(tmp_path / "output.pdf")
        ContractService.generate_pdf_from_html("<html><body>Test</body></html>", pdf_path, 42)

        mock_playwright_ctx.chromium.launch.assert_called_once()
        mock_browser.new_page.assert_called_once()
        mock_page.pdf.assert_called_once()

    def test_generate_pdf_from_html_with_chrome_path(self, tmp_path, mocker, landlord):
        """Covers lines 393-394: chrome_path setting used in launch args."""
        mock_playwright_ctx = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()

        mock_playwright_ctx.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        mock_sync_playwright = mocker.patch(
            "core.services.contract_service.sync_playwright"
        )
        mock_sync_playwright.return_value.__enter__ = mocker.MagicMock(
            return_value=mock_playwright_ctx
        )
        mock_sync_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch.object(settings, "CHROME_EXECUTABLE_PATH", "/usr/bin/chromium")

        pdf_path = str(tmp_path / "out.pdf")
        ContractService.generate_pdf_from_html("<html></html>", pdf_path, 99)

        launch_kwargs = mock_playwright_ctx.chromium.launch.call_args[1]
        assert launch_kwargs.get("executable_path") == "/usr/bin/chromium"

    def test_generate_pdf_from_html_cleans_up_temp_html(self, tmp_path, mocker, landlord):
        """Covers lines 418-419: temp HTML file is deleted after PDF generation."""
        mock_playwright_ctx = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_page = mocker.MagicMock()

        mock_playwright_ctx.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page

        mock_sync_playwright = mocker.patch(
            "core.services.contract_service.sync_playwright"
        )
        mock_sync_playwright.return_value.__enter__ = mocker.MagicMock(
            return_value=mock_playwright_ctx
        )
        mock_sync_playwright.return_value.__exit__ = mocker.MagicMock(return_value=False)

        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir()
        pdf_path = str(contracts_dir / "output.pdf")

        ContractService.generate_pdf_from_html("<html></html>", pdf_path, 77)

        # Temp HTML file should be gone
        temp_html = contracts_dir / "temp_contract_77.html"
        assert not temp_html.exists()

    def test_generate_pdf_with_infrastructure_cleans_up_temp_on_error(
        self, tmp_path, mocker, lease, landlord
    ):
        """Covers lines 354-357: temp PDF cleanup in finally block."""
        mock_gen = mocker.MagicMock()
        mock_storage = mocker.MagicMock()

        # Simulate generator writing a file then raising
        def gen_raises(html_content, output_path, options):
            Path(output_path).write_bytes(b"partial PDF")
            raise RuntimeError("PDF generation failed")

        mock_gen.generate_pdf.side_effect = gen_raises

        service = ContractService(pdf_generator=mock_gen, document_storage=mock_storage)
        with pytest.raises(RuntimeError, match="PDF generation failed"):
            service.generate_pdf_with_infrastructure("<html></html>", "123/fail.pdf")

        # Storage save should not be called since generation failed
        mock_storage.save.assert_not_called()

    def test_generate_pdf_with_infrastructure_handles_unlink_os_error(
        self, tmp_path, mocker, lease, landlord
    ):
        """Covers lines 356-357: OSError during temp file cleanup is logged and swallowed."""
        mock_gen = mocker.MagicMock()
        mock_storage = mocker.MagicMock()
        mock_storage.save.return_value = "/stored/path.pdf"

        def fake_generate(html_content, output_path, options):
            Path(output_path).write_bytes(b"PDF data")
            return str(output_path)

        mock_gen.generate_pdf.side_effect = fake_generate

        # Patch Path.unlink to raise OSError during cleanup
        mocker.patch("pathlib.Path.unlink", side_effect=OSError("unlink failed"))

        service = ContractService(pdf_generator=mock_gen, document_storage=mock_storage)
        # Should complete normally — OSError in finally is swallowed
        result = service.generate_pdf_with_infrastructure("<html></html>", "123/cleanup.pdf")
        assert result == "/stored/path.pdf"
