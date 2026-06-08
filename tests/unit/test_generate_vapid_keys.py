"""Unit test for the generate_vapid_keys management command.

Exercises the real command (no internal mocks) — py_vapid generates a real key pair and the command
prints them as env-ready strings.
"""

from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.unit
class TestGenerateVapidKeysCommand:
    def test_prints_env_ready_key_pair(self):
        out = StringIO()
        call_command("generate_vapid_keys", stdout=out)
        output = out.getvalue()

        assert "VAPID_PUBLIC_KEY=" in output
        assert "VAPID_PRIVATE_KEY=" in output
        assert "VAPID_SUBJECT=mailto:" in output

        public_line = next(
            line for line in output.splitlines() if line.startswith("VAPID_PUBLIC_KEY=")
        )
        public_value = public_line.split("=", 1)[1]
        # base64url, padding stripped — non-trivial length, no '=' padding.
        assert len(public_value) > 20
        assert "=" not in public_value
