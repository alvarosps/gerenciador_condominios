"""Unit tests for core/services/contract_service.py."""

from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from core.models import ContractRule, Landlord
from core.services.contract_service import ContractService
from core.utils import format_currency
from tests.factories import (
    make_apartment,
    make_building,
    make_furniture,
    make_lease,
    make_tenant,
)


@pytest.fixture
def building(admin_user):
    return make_building(
        street_number=6601,
        user=admin_user,
        name="Contract Test Building",
        address="Rua Contract, 6601",
    )


@pytest.fixture
def apartment(building, admin_user):
    return make_apartment(
        building=building,
        number=101,
        user=admin_user,
        cleaning_fee=Decimal("200.00"),
        max_tenants=3,
        rental_value=Decimal("1500.00"),
    )


@pytest.fixture
def tenant(admin_user):
    return make_tenant(
        cpf_cnpj="71286955084",
        user=admin_user,
        name="Contract Tenant",
        phone="11966660001",
        marital_status="Casado(a)",
        profession="Médico",
        due_day=10,
    )


@pytest.fixture
def second_tenant(admin_user):
    return make_tenant(
        cpf_cnpj="98765432100",
        user=admin_user,
        name="Second Contract Tenant",
        phone="11966660002",
        marital_status="Solteiro(a)",
        profession="Enfermeiro",
        due_day=10,
    )


@pytest.fixture
def lease(apartment, tenant, admin_user):
    lease_obj = make_lease(
        apartment=apartment,
        tenant=tenant,
        user=admin_user,
        start_date="2026-01-01",
        validity_months=12,
        tag_fee=Decimal("20.00"),
        rental_value=Decimal("1500.00"),
    )
    lease_obj.tenants.add(tenant)
    return lease_obj


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
    def test_returns_apartment_furniture_minus_tenant_furniture(
        self, apartment, tenant, lease, admin_user
    ):
        fridge = make_furniture(name="Geladeira Test CF", user=admin_user)
        tv = make_furniture(name="TV Test CF", user=admin_user)
        apartment.furnitures.add(fridge, tv)
        tenant.furnitures.add(tv)  # TV belongs to tenant

        result = ContractService.calculate_lease_furniture(lease)
        names = [f.name for f in result]
        assert "Geladeira Test CF" in names
        assert "TV Test CF" not in names

    def test_empty_when_tenant_has_all_furniture(self, apartment, tenant, lease, admin_user):
        stove = make_furniture(name="Fogão Test CF", user=admin_user)
        apartment.furnitures.add(stove)
        tenant.furnitures.add(stove)

        result = ContractService.calculate_lease_furniture(lease)
        assert result == []

    def test_returns_all_apt_furniture_when_no_tenant_furniture(self, apartment, lease, admin_user):
        chair = make_furniture(name="Cadeira Test CF", user=admin_user)
        apartment.furnitures.add(chair)

        result = ContractService.calculate_lease_furniture(lease)
        assert any(f.name == "Cadeira Test CF" for f in result)

    def test_subtracts_furniture_from_all_tenants(
        self, apartment, tenant, second_tenant, lease, admin_user
    ):
        lease.tenants.add(second_tenant)
        sofa = make_furniture(name="Sofá Test CF", user=admin_user)
        wardrobe = make_furniture(name="Guarda-roupa Test CF", user=admin_user)
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
            "tenant",
            "building_number",
            "apartment_number",
            "furnitures",
            "validity",
            "start_date",
            "final_date",
            "rental_value",
            "next_month_date",
            "tag_fee",
            "cleaning_fee",
            "valor_total",
            "lease",
            "valor_tags",
            "tag_unit_price",
            "rules",
            "landlord",
        ]
        for key in required_keys:
            assert key in context, f"Missing key: {key}"

    def test_tag_unit_price_is_single_tag_fee(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["tag_unit_price"] == Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))

    def test_raises_when_no_active_landlord(self, lease):
        assert Landlord.get_active() is None

        with pytest.raises(ValidationError) as exc_info:
            ContractService.prepare_contract_context(lease)

        assert "locador" in str(exc_info.value).lower()

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

    def test_contract_rules_are_sanitized_in_context(self, lease, landlord, admin_user):
        """Admin-entered rule HTML is sanitized before reaching the template (anti stored-XSS)."""
        ContractRule.objects.create(
            content="Silêncio após 22h <script>fetch('//evil')</script>",
            order=1,
            created_by=admin_user,
        )
        ContractRule.objects.create(
            content='<b onclick="x()">Não fumar</b>', order=2, created_by=admin_user
        )

        context = ContractService.prepare_contract_context(lease)
        joined = " ".join(context["rules"])

        assert "<script>" not in joined
        assert "fetch" not in joined
        assert "onclick" not in joined
        # legitimate text and inline formatting survive
        assert "Silêncio após 22h" in joined
        assert "<b>Não fumar</b>" in joined


@pytest.mark.unit
class TestPrepareContractContextFurnitureNames:
    def test_context_includes_furniture_names(self, lease, apartment, landlord, admin_user):
        chair = make_furniture(name="Cadeira FN", user=admin_user)
        table = make_furniture(name="Mesa FN", user=admin_user)
        apartment.furnitures.add(chair, table)

        context = ContractService.prepare_contract_context(lease)

        assert "furniture_names" in context
        assert isinstance(context["furniture_names"], list)
        assert all(isinstance(name, str) for name in context["furniture_names"])
        assert set(context["furniture_names"]) == {"Cadeira FN", "Mesa FN"}

    def test_furniture_names_empty_when_no_furniture(self, lease, landlord):
        context = ContractService.prepare_contract_context(lease)
        assert context["furniture_names"] == []

    def test_furniture_names_mirror_furniture_objects(self, lease, apartment, landlord, admin_user):
        sofa = make_furniture(name="Sofá FN", user=admin_user)
        apartment.furnitures.add(sofa)

        context = ContractService.prepare_contract_context(lease)

        object_names = sorted(f.name for f in context["furnitures"])
        assert sorted(context["furniture_names"]) == object_names


@pytest.mark.unit
class TestDepositClauseRendering:
    """Deposit clause uses lease.deposit_amount (regression: it used tenant.deposit_amount,
    a field that does not exist on Tenant, so the clause was always omitted)."""

    def test_deposit_clause_rendered_when_lease_has_deposit(self, lease, landlord):
        lease.deposit_amount = Decimal("500.00")
        lease.save(update_fields=["deposit_amount"])

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        assert "caução adicional" in html
        assert format_currency(Decimal("500.00")) in html

    def test_deposit_clause_omitted_when_no_deposit(self, lease, landlord):
        assert lease.deposit_amount is None

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        # Omitted, and StrictUndefined does not blow up on the None deposit branch
        assert "caução adicional" not in html

    def test_deposit_clause_omitted_when_zero(self, lease, landlord):
        lease.deposit_amount = Decimal("0.00")
        lease.save(update_fields=["deposit_amount"])

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        assert "caução adicional" not in html


@pytest.mark.unit
class TestBotijaoClauseRendering:
    """Botijão clause matches against furniture_names (regression: `in furnitures` compared a
    string against a list of Furniture objects, so it was always False)."""

    def test_botijao_clause_rendered_when_furniture_present(
        self, lease, apartment, landlord, admin_user
    ):
        botijao = make_furniture(name="Botijão de gás", user=admin_user)
        apartment.furnitures.add(botijao)

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        assert "BOTIJÃO DE GÁS" in html
        assert "casco" in html

    def test_botijao_clause_omitted_when_absent(self, lease, apartment, landlord, admin_user):
        chair = make_furniture(name="Cadeira sem botijão", user=admin_user)
        apartment.furnitures.add(chair)

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        assert "BOTIJÃO DE GÁS" not in html


@pytest.mark.unit
class TestRenderContractTemplateSandbox:
    def test_full_embedded_template_renders_without_undefined_error(
        self, lease, apartment, landlord, admin_user
    ):
        """The embedded contract template must render fully under StrictUndefined — every
        variable it references must exist in prepare_contract_context."""
        botijao = make_furniture(name="Botijão de gás", user=admin_user)
        apartment.furnitures.add(botijao)
        lease.deposit_amount = Decimal("750.00")
        lease.save(update_fields=["deposit_amount"])

        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        assert "<html" in html
        assert landlord.name in html

    def test_render_uses_sandboxed_env_blocks_ssti_in_disk_template(
        self, lease, landlord, monkeypatch, tmp_path
    ):
        """Defense in depth: an SSTI payload placed in the on-disk template is blocked by the
        sandbox at render time (it never executes)."""
        from jinja2.exceptions import SecurityError

        template_dir = tmp_path / "core" / "templates"
        template_dir.mkdir(parents=True)
        (template_dir / "contract_template.html").write_text(
            "<html>{{ ''.__class__.__mro__ }}</html>", encoding="utf-8"
        )
        monkeypatch.setattr(settings, "BASE_DIR", str(tmp_path))

        context = ContractService.prepare_contract_context(lease)
        with pytest.raises(SecurityError):
            ContractService.render_contract_template(context)


@pytest.mark.unit
class TestGetContractRelativePath:
    def test_path_format(self, lease, apartment, building):
        path = ContractService.get_contract_relative_path(lease)
        expected = f"{building.street_number}/contract_apto_{apartment.number}_{lease.id}.pdf"
        assert path == expected


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

    def test_renders_tag_as_tenant_property_not_caucao(self, lease, landlord):
        """The tag is the tenant's non-refundable property; old caução wording is gone."""
        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        # New rule: the tag becomes the tenant's property (non-refundable)
        assert "propriedade do LOCATÁRIO" in html
        assert "não reembolsável" in html
        # Lost-tag replacement price renders from tag_unit_price (= single-tag fee)
        assert format_currency(Decimal(str(settings.DEFAULT_TAG_FEE_SINGLE))) in html

        # Old refundable-caução tag wording must be absent (regression guard)
        assert "caução da(s) tag" not in html
        assert "devolvê-las" not in html

    def test_renders_tenant_due_day(self, lease, landlord):
        """Due day is shown from the responsible tenant (the Lease model has no due_day field)."""
        context = ContractService.prepare_contract_context(lease)
        html = ContractService.render_contract_template(context)

        due_day = lease.responsible_tenant.due_day
        assert f"até o dia {due_day} de cada" in html
        assert f"(dia {due_day})" in html
        # Regression: the old {{ lease.due_day }} (no such field) rendered an empty "(dia )"
        assert "(dia )" not in html


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
class TestGeneratePdfWithInfrastructureCleanup:
    """Error and temp-file cleanup paths of generate_pdf_with_infrastructure."""

    def test_generate_pdf_with_infrastructure_cleans_up_temp_on_error(
        self, tmp_path, mocker, lease, landlord
    ):
        """Covers lines 354-357: temp PDF cleanup in finally block."""
        mock_gen = mocker.MagicMock()
        mock_storage = mocker.MagicMock()

        # Simulate generator writing a file then raising
        def gen_raises(html_content, output_path, options):
            Path(output_path).write_bytes(b"partial PDF")
            msg = "PDF generation failed"
            raise RuntimeError(msg)

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
