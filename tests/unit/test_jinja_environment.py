"""Unit tests for core/services/jinja_environment.build_contract_jinja_env.

The shared Jinja environment is a SandboxedEnvironment with StrictUndefined and the
contract filters (currency/extenso). It is used by both ContractService.render_contract_template
and TemplateManagementService.preview_template, so it must:
- block dunder/attribute escalation (anti-SSTI/RCE),
- raise on unknown variables (StrictUndefined),
- keep range() available (furniture table loop),
- expose the currency/extenso filters.
"""

from decimal import Decimal

import pytest
from jinja2 import BaseLoader, StrictUndefined
from jinja2.exceptions import SecurityError, UndefinedError
from jinja2.sandbox import SandboxedEnvironment

from core.services.html_sanitizer import sanitize_contract_html
from core.services.jinja_environment import build_contract_jinja_env
from core.utils import format_currency, number_to_words


@pytest.mark.unit
class TestBuildContractJinjaEnv:
    def test_env_is_sandboxed(self):
        env = build_contract_jinja_env(BaseLoader())
        assert isinstance(env, SandboxedEnvironment)

    def test_uses_strict_undefined(self):
        env = build_contract_jinja_env(BaseLoader())
        assert env.undefined is StrictUndefined

    def test_blocks_dunder_access(self):
        """{{ ''.__class__.__mro__ }} must raise SecurityError (anti-RCE)."""
        env = build_contract_jinja_env(BaseLoader())
        template = env.from_string("{{ ''.__class__.__mro__ }}")
        with pytest.raises(SecurityError):
            template.render()

    def test_blocks_subclasses_escalation(self):
        """The classic subclasses() RCE gadget must be blocked by the sandbox."""
        env = build_contract_jinja_env(BaseLoader())
        template = env.from_string("{{ ''.__class__.__mro__[1].__subclasses__() }}")
        with pytest.raises(SecurityError):
            template.render()

    def test_strict_undefined_raises(self):
        env = build_contract_jinja_env(BaseLoader())
        template = env.from_string("{{ inexistente }}")
        with pytest.raises(UndefinedError):
            template.render()

    def test_currency_filter_registered(self):
        env = build_contract_jinja_env(BaseLoader())
        rendered = env.from_string("{{ value | currency }}").render(value=Decimal(1500))
        assert rendered == format_currency(Decimal(1500))

    def test_extenso_filter_registered(self):
        env = build_contract_jinja_env(BaseLoader())
        rendered = env.from_string("{{ value | extenso }}").render(value=1500)
        assert rendered == number_to_words(1500)

    def test_range_available_for_furniture_loop(self):
        """range() must stay available for the furniture-table loop regression."""
        env = build_contract_jinja_env(BaseLoader())
        rendered = env.from_string("{% for i in range(0, 4, 2) %}{{ i }}{% endfor %}").render()
        assert rendered == "02"

    def test_autoescape_enabled_for_html(self):
        """HTML autoescape stays on so injected values are escaped."""
        env = build_contract_jinja_env(BaseLoader())
        rendered = env.from_string("{{ value }}").render(value="<script>")
        assert "&lt;script&gt;" in rendered


@pytest.mark.unit
class TestSanitizeContractHtml:
    """sanitize_contract_html reduces admin-entered ContractRule HTML to a safe
    formatting-only subset (anti stored-XSS), preserving inline formatting."""

    def test_strips_script_tag_and_content(self):
        cleaned = sanitize_contract_html("Regra <script>alert('x')</script> importante")
        assert "<script>" not in cleaned
        assert "alert" not in cleaned
        assert "Regra" in cleaned
        assert "importante" in cleaned

    def test_strips_event_handler_attributes(self):
        cleaned = sanitize_contract_html('<b onclick="steal()">Texto</b>')
        assert "onclick" not in cleaned
        assert "steal" not in cleaned
        assert "<b>Texto</b>" in cleaned

    def test_strips_href_and_style_attributes(self):
        cleaned = sanitize_contract_html(
            '<span style="x:expression()">a</span><a href="javascript:b()">link</a>'
        )
        assert "style=" not in cleaned
        assert "href=" not in cleaned
        assert "javascript:" not in cleaned

    def test_preserves_inline_formatting_tags(self):
        cleaned = sanitize_contract_html("<b>Negrito</b> e <i>itálico</i> e <u>sublinhado</u>")
        assert "<b>Negrito</b>" in cleaned
        assert "<i>itálico</i>" in cleaned
        assert "<u>sublinhado</u>" in cleaned

    def test_preserves_lists(self):
        cleaned = sanitize_contract_html("<ul><li>um</li><li>dois</li></ul>")
        assert "<ul>" in cleaned
        assert "<li>um</li>" in cleaned

    def test_disallowed_tag_stripped_but_text_kept(self):
        cleaned = sanitize_contract_html("<iframe src='evil'></iframe>ok")
        assert "<iframe" not in cleaned
        assert "ok" in cleaned
