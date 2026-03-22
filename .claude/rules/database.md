---
paths:
  - "core/models.py"
  - "core/migrations/**"
  - "core/services/**"
---

# Database Rules

## Migrations
- Sequential numbering: currently at 0012 (financial module)
- Never manually edit existing migrations — create new ones
- Always run `python manage.py makemigrations` then `python manage.py migrate`
- Test migrations both forward and backward when possible

## Soft Delete
- All models use SoftDeleteMixin — `delete()` sets `is_deleted=True`
- Default querysets exclude deleted records automatically
- Use `Model.objects.with_deleted()` to include deleted
- Use `hard_delete=True` only when absolutely necessary (e.g., test cleanup)

## Query Performance
- Composite indexes exist (migration 0005) — check before adding new ones
- Use `select_related()` for FK joins, `prefetch_related()` for M2M
- Dashboard queries in `dashboard_service.py` use aggregation — keep them efficient

## M2M Relationships
- LeaseTenant: `db_table='core_lease_tenant_details'` — never change this table name
- Furniture ↔ Apartment and Furniture ↔ Tenant are standard M2M
