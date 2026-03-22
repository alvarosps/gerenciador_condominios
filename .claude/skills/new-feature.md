---
name: new-feature
description: Structured workflow for implementing a new feature end-to-end (backend + frontend)
---

# New Feature Workflow

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
8. **Tests** — Unit tests in `tests/unit/`, integration in `tests/integration/`
9. **Verify** — `python -m pytest && pre-commit run --all-files`

## 3. Frontend
1. **Types** — Define in Zod schema at `frontend/lib/schemas/<resource>.ts`
2. **API Hook** — TanStack Query hook at `frontend/lib/api/hooks/use-<resource>.ts`
3. **Page** — CRUD page at `frontend/app/(dashboard)/<resource>/page.tsx` using `useCrudPage`
4. **Components** — Reusable pieces in `frontend/components/` or page-level `_components/`
5. **Tests** — Hook tests at `frontend/lib/api/hooks/__tests__/`
6. **Verify** — `cd frontend && npm run lint && npm run type-check && npm run test:unit`

## 4. Finalize
- Run full test suite: backend + frontend
- Commit with conventional format: `feat(scope): description`
