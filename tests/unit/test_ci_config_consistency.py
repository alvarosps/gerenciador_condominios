"""P6.3 — pin CI/config consistency so the canonical gate can't silently drift.

Boundary = the filesystem (the config files are read directly; nothing is mocked). These are
the regression tests the plan requires: they were RED before P6.3 and lock the final state.
"""

import tomllib
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_CI = _ROOT / ".github" / "workflows" / "ci.yml"
_PYPROJECT = _ROOT / "pyproject.toml"
_PYRIGHT = _ROOT / "pyrightconfig.json"
_PYTHON_VERSION = _ROOT / ".python-version"
_REQ_DEV = _ROOT / "requirements-dev.txt"

_PYRIGHT_PIN = "pyright==1.1.408"

pytestmark = pytest.mark.unit


def _ci_text() -> str:
    return _CI.read_text(encoding="utf-8")


def _pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))


def test_ci_ruff_lints_whole_repo() -> None:
    text = _ci_text()
    assert "ruff check ." in text
    assert "ruff format --check ." in text
    assert "ruff check core/ condominios_manager/" not in text


def test_ci_mypy_includes_finances() -> None:
    assert "mypy core/ condominios_manager/ finances/" in _ci_text()


def test_ci_runs_pyright() -> None:
    text = _ci_text()
    assert "Type check with pyright" in text
    assert "run: pyright" in text
    # pyright must come from the pinned requirements-dev.txt, not an unpinned ad-hoc install.
    assert "pip install pyright" not in text


def test_pyright_is_pinned_in_manifests() -> None:
    # Every gate tool must be declared (pinned) in BOTH requirements-dev.txt and the pyproject dev
    # extras (coding-standards.md). pyright strict-mode rules drift between minor releases, so the
    # version is locked exactly and asserted here so a future edit that unpins it turns this RED.
    assert _PYRIGHT_PIN in _REQ_DEV.read_text(encoding="utf-8")
    dev_deps = _pyproject()["project"]["optional-dependencies"]["dev"]
    assert _PYRIGHT_PIN in dev_deps


def test_ci_bandit_includes_finances() -> None:
    text = _ci_text()
    assert "bandit -r core/ condominios_manager/ finances/" in text
    # The bandit step must NOT carry continue-on-error (hard gate).
    bandit_block = text.split("Run Bandit security linter", 1)[1].split("- name:", 1)[0]
    assert "continue-on-error" not in bandit_block


def test_ci_security_is_a_real_gate() -> None:
    assert "needs.security.result" in _ci_text()


def test_ci_uses_safety_scan_not_check() -> None:
    text = _ci_text()
    assert "safety scan" in text
    assert "safety check" not in text


def test_ci_postgres_matches_prod_major() -> None:
    text = _ci_text()
    assert "image: postgres:17" in text
    assert "postgres:15" not in text


def test_ci_uses_current_actions() -> None:
    text = _ci_text()
    assert "actions/checkout@v4" in text
    assert "actions/checkout@v3" not in text
    assert "actions/setup-python@v5" in text
    assert "actions/setup-python@v4" not in text


def test_python_target_is_consistent() -> None:
    pyproject = _pyproject()
    assert pyproject["project"]["requires-python"] == ">=3.14"
    assert pyproject["tool"]["mypy"]["python_version"] == "3.14"
    assert pyproject["tool"]["ruff"]["target-version"] == "py314"

    # pyrightconfig.json is JSONC (carries // comments), so assert via text not json.loads.
    assert '"pythonVersion": "3.14"' in _PYRIGHT.read_text(encoding="utf-8")

    assert _PYTHON_VERSION.read_text(encoding="utf-8").strip() == "3.14"

    ci = _ci_text()
    assert "python-version: '3.14'" in ci
    assert "python-version: '3.12'" not in ci


def test_ruff_finances_is_first_party() -> None:
    ruff = _pyproject()["tool"]["ruff"]
    assert "finances" in ruff["src"]
    assert "tests" in ruff["src"]
    assert "finances" in ruff["lint"]["isort"]["known-first-party"]


def test_python_version_file_exists() -> None:
    assert _PYTHON_VERSION.exists()
    assert _PYTHON_VERSION.read_text(encoding="utf-8").strip() == "3.14"
