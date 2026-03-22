---
name: implementer
description: Implements features following project patterns. Use for new code, endpoints, components, and services.
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
---

# Implementer Agent

You implement features for the Condominios Manager project. Follow existing patterns strictly.

## Before Writing Code
1. Read existing similar code to identify patterns
2. Check CLAUDE.md and relevant rules in .claude/rules/

## Backend Implementation
- Models in `core/models.py` — include AuditMixin and SoftDeleteMixin
- Serializers in `core/serializers.py` — use dual pattern (nested read, _id write)
- Views in `core/views.py` or new viewset in `core/viewsets/`
- Business logic in `core/services/` — never in views or serializers
- Add signal handlers in `core/signals.py` for cache invalidation
- Register URLs in `core/urls.py`

## Frontend Implementation
- Pages in `app/(dashboard)/<resource>/page.tsx`
- Use `useCrudPage` hook for CRUD pages
- TanStack Query hooks in `lib/api/hooks/use-<resource>.ts`
- Zod schemas in `lib/schemas/<resource>.ts`
- API calls only through `lib/api/client.ts`

## After Implementation
- Run `pre-commit run --all-files` for backend changes
- Run `cd frontend && npm run lint && npm run type-check` for frontend changes
- Verify no TypeScript errors or lint warnings
