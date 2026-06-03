---
paths:
  - "core/models.py"
  - "core/migrations/**"
  - "core/services/**"
---

# Database Rules

## Migrations
- Sequential numbering — run `python manage.py showmigrations core` for the current state (never hardcode the count in docs; it rots).
- Never manually edit existing migrations — create a new one via `python manage.py makemigrations` (the `pre-edit-scope.sh` hook blocks edits to existing `migrations/0*.py`).
- Test migrations forward and backward when feasible.

## Data Safety — CRITICAL
- ALWAYS back up before any destructive DB op (a `migrate` that drops/alters columns, `ALTER`, `DROP`, `TRUNCATE`): `python scripts/backup_db.py`.
- NEVER run `flush` / `sqlflush` / `reset_db` / destructive `dbshell` SQL on real data — condo + financial data is real. These are blocked by `permissions.deny` + the `pre-db-push-guard.sh` hook, but treat the rule as primary.

## Soft Delete
- All models use SoftDeleteMixin — `delete()` sets `is_deleted=True`
- Default querysets exclude deleted records automatically
- Use `Model.objects.with_deleted()` to include deleted
- Use `hard_delete=True` only when absolutely necessary (e.g., test cleanup)

## Query Performance
- Composite indexes exist on hot paths (Apartment, Lease, RentPayment, Expense) — check each model's `Meta.indexes` before adding new ones
- Use `select_related()` for FK joins, `prefetch_related()` for M2M
- Dashboard queries in `dashboard_service.py` use aggregation — keep them efficient

## M2M Relationships
- LeaseTenant: `db_table='core_lease_tenant_details'` — never change this table name
- Furniture ↔ Apartment and Furniture ↔ Tenant are standard M2M
