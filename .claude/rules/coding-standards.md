# Coding Standards

## Backend (Python/Django)
- Ruff formatting: 100 char line length, double quotes
- Ruff linting: 30+ rule categories enabled (see pyproject.toml [tool.ruff.lint.select])
- mypy: strict mode with django-stubs + djangorestframework-stubs
- Pyright: strict mode (see pyrightconfig.json) — catches type errors, unbound variables, optional access issues
- snake_case for everything (variables, functions, files, URLs)
- Docstrings only where logic is non-obvious — don't add to simple CRUD
- Type hints on all functions (mypy strict enforces this)
- CRITICAL: When adding a new dependency, it MUST be added to ALL three places: `requirements.txt` (runtime) or `requirements-dev.txt` (dev/test only), AND `pyproject.toml` `[project.dependencies]` or `[project.optional-dependencies.dev]`. Never add to just one.
- CRITICAL: No optional dependencies — all dependencies in requirements.txt are always loaded. Never use `try/except ImportError` patterns or `HAS_*` flags for imports. Import directly at the top of the file.
- CRITICAL: Never use `from __future__ import annotations` — Python 3.14 has PEP 649 lazy annotations natively. Import types directly (e.g., `from django.db.models import QuerySet`), never under `if TYPE_CHECKING:` blocks.

## Frontend (TypeScript/React)
- ESLint: strict-type-checked + stylistic-type-checked rules
- TypeScript: strict mode + noUncheckedIndexedAccess
- camelCase for variables/functions, PascalCase for components/types
- Functional components only — no class components
- Named exports preferred over default exports
- Absolute imports via `@/` alias (maps to frontend/)
- File naming: kebab-case for files, PascalCase for component folders
- Use `import type` for type-only imports

## Both
- No commented-out code in commits
- No console.log/print statements in production code
- Error messages in Portuguese (user-facing), English (developer-facing/logs)
- CRITICAL: Never use `# noqa`, `# type: ignore`, `eslint-disable`, or `@ts-ignore` — always fix the actual code
- CRITICAL: Never mock internal application methods or library code in tests — mock only external boundaries
- CRITICAL: Zero tolerance for warnings — all linter, type-checker, and test warnings must be resolved. Warnings can hide bugs and fail silently. This applies to Ruff, mypy, Pyright, ESLint, TypeScript, and pytest warnings.
- CRITICAL: No re-exports — import from the source module, never create barrel files or re-export wrappers
- CRITICAL: No backwards compatibility shims — when refactoring, update all consumers and remove old code completely
- CRITICAL: No workarounds or quick wins — fix problems at the root cause, properly and completely
- CRITICAL: Follow SOLID, DRY, KISS, YAGNI, and Clean Code at all times — see `.claude/rules/design-principles.md`
