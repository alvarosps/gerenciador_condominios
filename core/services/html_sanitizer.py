"""Sanitization for admin-entered HTML rendered into contracts.

``ContractRule`` text is HTML authored by an admin and rendered into the contract
with Jinja's ``| safe`` (it must keep inline formatting like bold/italic/lists).
Without sanitization that is a stored-XSS vector: a ``<script>`` in a rule would
run in the template preview iframe and in the headless Chromium that renders the
PDF. We sanitize at the single source — when the rules are placed in the contract
context — so the value reaching ``| safe`` is already a safe formatting-only subset.
"""

import nh3

# Inline formatting + lists only. No attributes are allowed (drops href/style/on*
# handlers); nh3 removes the content of script/style tags entirely.
_ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "s", "br", "p", "ul", "ol", "li", "span"}
_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {}


def sanitize_contract_html(value: str) -> str:
    """Return ``value`` reduced to a safe formatting-only HTML subset."""
    return nh3.clean(value, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRIBUTES)
