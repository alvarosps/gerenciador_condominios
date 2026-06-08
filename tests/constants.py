"""Shared test constants.

Passwords are generated once per test-run with ``secrets`` instead of being hardcoded string
literals. They carry no security relevance — they only drive user fixtures and auth flows — but
keeping them out of the source avoids false-positive "hardcoded secret" findings from scanners
(GitGuardian et al.). Generating them also guarantees ``WRONG_PASSWORD`` never accidentally equals
``TEST_PASSWORD``.

``TEST_PASSWORD`` is long, mixed-character and non-numeric, so it passes Django's default password
validators (used by registration / password-change endpoints).
"""

import secrets

TEST_PASSWORD = secrets.token_urlsafe(16)
TEST_PASSWORD_NEW = secrets.token_urlsafe(16)
WRONG_PASSWORD = secrets.token_urlsafe(16)
