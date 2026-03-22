---
name: new-feature
description: Structured workflow for implementing a new feature end-to-end (backend + frontend)
argument-hint: "[feature-description]"
---

# New Feature Workflow

Current branch: !`git branch --show-current`
Recent migrations: !`ls -1 core/migrations/0*.py | tail -3`

## 0. Parallel Strategy Decision

Before starting, decide the execution strategy:

- **Sequential** (default): backend first, then frontend. Use when feature is small or layers depend on each other.
- **Parallel with subagents**: Use `@implementer` (worktree-isolated) for backend and frontend simultaneously. Use when backend and frontend are independent (different files).
- **Agent team**: Use when the feature spans 3+ independent areas (e.g., backend models + API + frontend page + tests). Each teammate owns a set of files.

## 1. Setup
- Create feature branch: `git checkout -b feat/<feature-name>`
- Understand the scope: what models, endpoints, and UI are needed?

## 2. Backend
1. **Models** — Add/modify in `core/models.py` (include AuditMixin + SoftDeleteMixin)
2. **Migration** — `python manage.py makemigrations && python manage.py migrate`
3. **Serializer** — Add in `core/serializers.py` (dual pattern: nested read, _id write)
4. **Service** — Business logic in `core/services/<service>.py`
5. **Views** — ViewSet in `core/views.py` or `core/viewsets/`
6. **URLs** — Register in `core/urls.py`
7. **Cache signals** — Add invalidation in `core/signals.py`
8. **Tests** — Integration tests in `tests/integration/`, unit for complex logic in `tests/unit/`
9. **Verify** — `ruff check && ruff format --check && mypy core/ && python -m pytest`

## 3. Frontend
1. **Types** — Define in Zod schema at `frontend/lib/schemas/<resource>.ts`
2. **API Hook** — TanStack Query hook at `frontend/lib/api/hooks/use-<resource>.ts`
3. **Page** — CRUD page at `frontend/app/(dashboard)/<resource>/page.tsx` using `useCrudPage`
4. **Components** — Reusable pieces in `frontend/components/` or page-level `_components/`
5. **Tests** — Hook tests at `frontend/lib/api/hooks/__tests__/`
6. **Verify** — `cd frontend && npm run lint && npm run type-check && npm run test:unit`

## 4. Review & Finalize
- Use `@reviewer` agent to review all changes before committing
- Run full verification: backend lint + tests, frontend lint + type-check + tests
- Commit with conventional format: `feat(scope): description`

## Mock Policy
- Mock ONLY external boundaries (Chrome/PDF, external HTTP APIs, file system I/O)
- NEVER mock Django ORM, services, serializers, model methods, or library code
