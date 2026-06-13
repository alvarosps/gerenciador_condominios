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
- New tables MUST enable Row Level Security in the same migration (Supabase Data API exposure) — see `.claude/rules/security.md` › Row Level Security and the `core/migrations/0047_enable_row_level_security.py` pattern.

## Data Safety — CRITICAL
- ALWAYS back up before any destructive DB op (a `migrate` that drops/alters columns, `ALTER`, `DROP`, `TRUNCATE`): `python scripts/backup_db.py`.
- NEVER run `flush` / `sqlflush` / `reset_db` / destructive `dbshell` SQL on real data — condo + financial data is real. These are blocked by `permissions.deny` + the `pre-db-push-guard.sh` hook, but treat the rule as primary.

## Production = Supabase + backup/sync
- Prod DB is Supabase (project `kaukiwhbmvnjjekodcmq`, region us-west-2, Postgres 17); local dev is Postgres on `localhost:5433`, DB `condominio`. Backend (Render) and local both connect as the `postgres` role.
- The Supabase MCP can run SQL / DDL on prod (`execute_sql`, `apply_migration`) and read advisors, but it **cannot `pg_dump` and never exposes the DB password**. A true backup/mirror needs the connection string (Dashboard → Connect) fed to `pg_dump`/`pg_restore` directly. Never read `.env` for it (blocked by policy) — ask the user for a temp file and delete it after use.
- **Backup prod / sync local to prod:** `pg_dump "<prod-uri>" --schema=public --no-owner --no-acl -F p -f backups/backup_PROD_<ts>.sql` (only `public` — Supabase's auth/storage/vault schemas don't exist locally), then `python scripts/restore_db.py backups/backup_PROD_<ts>.sql --yes` (drops + recreates local `condominio`, restores). A full `public` dump carries schema + data + `django_migrations`, so local becomes an exact mirror; do NOT run `migrate` afterward (it would push local ahead of prod).
- Verify after restore: compare per-table row counts vs prod. Note ids are PG IDENTITY columns (`column_default` is NULL — normal). Never run DB write-tests outside an atomic block — Django autocommit makes them persist.

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
- `Lease.tenants` is a plain auto M2M (no `through`/`db_table`); `Lease.responsible_tenant` is the responsible tenant (FK). The old `LeaseTenant`/`core_lease_tenant_details` model was deleted in migration 0004 — it no longer exists.
- Furniture ↔ Apartment and Furniture ↔ Tenant are standard M2M
