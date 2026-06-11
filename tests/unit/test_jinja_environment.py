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
