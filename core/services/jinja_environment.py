"""Shared, sandboxed Jinja2 environment factory for contract templates.

Single source of truth for how contract templates are compiled and rendered.
Both ContractService.render_contract_template (PDF generation) and
TemplateManagementService.preview_template (template editor preview) must use this
factory so that:

- Templates run inside a ``SandboxedEnvironment``, which blocks access to dangerous
  attributes/methods (``__class__``, ``__globals__``, ``__subclasses__``, ...). This
  neutralizes the SSTI/RCE escalation reachable via POST /api/templates/preview/.
- ``StrictUndefined`` turns a missing/misspelled variable into an ``UndefinedError``
  instead of silently rendering an empty string (which previously hid clause bugs).
- The custom ``currency``/``extenso`` filters used across the contract template are
  always registered, in exactly one place (DRY).
"""

from jinja2 import BaseLoader, StrictUndefined, select_autoescape
from jinja2.sandbox import SandboxedEnvironment

from core.utils import format_currency, number_to_words


def build_contract_jinja_env(loader: BaseLoader) -> SandboxedEnvironment:
    """Build the sandboxed Jinja environment used for contract templates.

    Args:
        loader: The Jinja loader (``BaseLoader`` for inline preview content,
            ``FileSystemLoader`` for the on-disk contract template).

    Returns:
        A ``SandboxedEnvironment`` with HTML autoescape, ``StrictUndefined`` and the
        ``currency``/``extenso`` filters registered.
    """
    env = SandboxedEnvironment(
        loader=loader,
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
    )
    env.filters["currency"] = format_currency
    env.filters["extenso"] = number_to_words
    return env
