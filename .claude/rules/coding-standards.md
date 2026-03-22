# Coding Standards

## Backend (Python/Django)
- Black formatting: 120 char line length
- isort: black profile, 120 line length
- flake8: max line 120, ignore E203, W503
- snake_case for everything (variables, functions, files, URLs)
- Docstrings only where logic is non-obvious — don't add to simple CRUD
- Type hints on service layer functions, not on views/serializers

## Frontend (TypeScript/React)
- camelCase for variables/functions, PascalCase for components/types
- Functional components only — no class components
- Named exports preferred over default exports
- Absolute imports via `@/` alias (maps to frontend/)
- File naming: kebab-case for files, PascalCase for component folders

## Both
- No commented-out code in commits
- No console.log/print statements in production code
- Error messages in Portuguese (user-facing), English (developer-facing/logs)
