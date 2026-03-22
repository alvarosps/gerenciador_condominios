# Coding Standards

## Backend (Python/Django)
- Ruff formatting: 100 char line length, double quotes
- Ruff linting: 30+ rule categories enabled (see pyproject.toml [tool.ruff.lint.select])
- mypy: strict mode with django-stubs + djangorestframework-stubs
- snake_case for everything (variables, functions, files, URLs)
- Docstrings only where logic is non-obvious — don't add to simple CRUD
- Type hints on all functions (mypy strict enforces this)

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
