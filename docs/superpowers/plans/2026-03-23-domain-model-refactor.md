# Domain Model Refactor — Single Source of Truth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate field duplication across Apartment, Lease, and Tenant models by establishing a single source of truth for each field.

**Architecture:** Each field lives in exactly one model (the source of truth). No synchronization needed because there's nothing to sync. The API reflects the domain model directly — nested serializers expose related data read-only.

**Tech Stack:** Django 5.2, DRF, PostgreSQL 15, Next.js 14, React 18, TanStack Query, Zod

**Spec:** `docs/superpowers/specs/2026-03-23-domain-model-refactor.md`

---

## File Map

### Backend — Create
- `core/migrations/0017_add_new_fields.py` — Add destination fields before data migration
- `core/migrations/0018_migrate_data_and_rename.py` — Data migration + rename rent_due_day → due_day
- `core/migrations/0019_remove_old_fields.py` — Remove source fields + stale index

### Backend — Modify
- `core/models.py` — Remove/add/rename fields on Apartment, Lease, Tenant
- `core/serializers.py` — Update ApartmentSerializer, TenantSerializer, LeaseSerializer, PersonIncomeSerializer
- `core/views.py` — Update change_due_date, calculate_late_fee, generate_contract actions + get_queryset
- `core/signals.py` — Add is_rented sync signal for Lease → Apartment
- `core/services/contract_service.py` — Update field access paths + template context
- `core/services/fee_calculator.py` — Update rental_value access
- `core/services/cash_flow_service.py` — Update 8+ field access paths
- `core/services/dashboard_service.py` — Update field access paths
- `core/services/daily_control_service.py` — Update field access paths
- `core/services/financial_dashboard_service.py` — Update field access paths
- `core/services/simulation_service.py` — Simplify apartment.lease.rental_value → apartment.rental_value

### Frontend — Modify
- `frontend/lib/schemas/apartment.schema.ts` — Remove lease fields, add nested lease
- `frontend/lib/schemas/lease.schema.ts` — Remove duplicated fields, add moved fields
- `frontend/lib/schemas/tenant.schema.ts` — Rename rent_due_day, add warning_count, remove moved fields
- `frontend/lib/api/hooks/use-leases.ts` — Update cache invalidation
- `frontend/lib/api/hooks/use-apartments.ts` — Update cache invalidation (not currently done)
- `frontend/lib/api/hooks/use-tenants.ts` — Update cache invalidation
- `frontend/lib/api/hooks/use-furniture.ts` — Update cache invalidation
- `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx` — Remove lease-specific fields
- `frontend/app/(dashboard)/apartments/page.tsx` — Update table columns
- `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` — Multi-model save pattern
- `frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx` — Update field paths
- `frontend/app/(dashboard)/leases/_components/late-fee-modal.tsx` — Update field paths
- `frontend/app/(dashboard)/leases/_components/due-date-modal.tsx` — Update field paths
- `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx` — Update field paths
- `frontend/app/(dashboard)/tenants/_components/wizard/index.tsx` — Remove moved fields, rename due_day
- `frontend/app/(dashboard)/tenants/_components/wizard/types.ts` — Update types
- `frontend/app/(dashboard)/tenants/_components/dependent-form-list.tsx` — Update local type
- `frontend/app/(dashboard)/contract-template/page.tsx` — Update template variables
- `frontend/components/contract-editor/variable-inserter.tsx` — Update variable list
- `frontend/components/search/global-search.tsx` — Update field paths
- `frontend/lib/hooks/use-export.ts` — Update export field mappings

### Tests — Create
- `tests/integration/test_lease_actions.py` — NEW: Integration tests for change_due_date, calculate_late_fee, generate_contract

### Tests — Modify
- `tests/conftest.py` — Update fixtures (sample lease/tenant data)
- `tests/e2e/test_financial_workflow.py` — Update field references throughout
- `tests/integration/test_cash_flow_api.py` — Update payloads
- `tests/integration/test_financial_dashboard_api.py` — Update payloads
- `tests/integration/test_financial_api_simple.py` — Update payloads
- `tests/integration/test_income_payment_api.py` — Update payloads
- `tests/integration/test_expense_api.py` — Update payloads
- `tests/unit/test_financial/test_daily_control_service.py` — Update field references
- `tests/unit/test_financial/test_financial_dashboard_service.py` — Update field references
- `frontend/tests/mocks/data/apartments.ts` — Remove lease fields from mock data
- `frontend/tests/mocks/data/leases.ts` — Update mock data structure
- `frontend/tests/mocks/data/tenants.ts` — Update mock data structure
- `frontend/tests/mocks/handlers.ts` — Update MSW handler responses
- `frontend/lib/api/hooks/__tests__/use-apartments.test.tsx` — Update test expectations
- `frontend/lib/api/hooks/__tests__/use-leases.test.tsx` — Update test expectations
- `frontend/lib/api/hooks/__tests__/use-tenants.test.tsx` — Update test expectations
- `frontend/lib/api/hooks/__tests__/use-dashboard.test.tsx` — Update test expectations

---

## Task 1: Django Migrations — Add New Fields

**Files:**
- Create: `core/migrations/0017_add_new_fields.py`

- [ ] **Step 0: Remove `from __future__ import annotations` from `core/models.py`**

Line 13 of `core/models.py` has `from __future__ import annotations` which violates project coding standards. Remove it. Also check and remove from `core/validators/model_validators.py`, `core/signals.py`, and any `if TYPE_CHECKING:` import guards — replace with direct imports.

- [ ] **Step 1: Update models — add new fields (without removing old ones yet)**

In `core/models.py`, add to `Tenant`:
```python
warning_count = models.PositiveIntegerField(help_text="Quantidade de avisos do inquilino", default=0)
```

In `core/models.py`, add to `Lease`:
```python
deposit_amount = models.DecimalField(
    max_digits=10, decimal_places=2, null=True, blank=True, help_text="Valor da caução"
)
cleaning_fee_paid = models.BooleanField(default=False, help_text="Taxa de limpeza paga")
tag_deposit_paid = models.BooleanField(default=False, help_text="Caução de tags paga")
```

- [ ] **Step 2: Generate migration**

Run: `python manage.py makemigrations core --name add_new_fields`
Expected: Migration `0017_add_new_fields.py` created

- [ ] **Step 3: Apply migration**

Run: `python manage.py migrate core 0017`
Expected: Migration applied successfully

- [ ] **Step 4: Commit**

```bash
git add core/models.py core/migrations/0017_*.py
git commit -m "feat(core): add destination fields for domain model refactor (migration 0017)"
```

---

## Task 2: Data Migration — Copy Data + Rename

**Files:**
- Create: `core/migrations/0018_migrate_data_and_rename.py`

- [ ] **Step 1: Create data migration file**

Run: `python manage.py makemigrations core --empty --name migrate_data_and_rename`

- [ ] **Step 2: Write migration code**

Edit the generated migration file. Operations (order matters):

```python
from django.db import migrations, models
from core.validators import validate_due_day


def migrate_data_forward(apps, schema_editor):
    Lease = apps.get_model("core", "Lease")
    Tenant = apps.get_model("core", "Tenant")
    Apartment = apps.get_model("core", "Apartment")

    # 1. Lease → Tenant: warning_count (aggregate MAX across all leases including soft-deleted)
    from django.db.models import Max

    tenant_warnings = Lease.objects.values("responsible_tenant_id").annotate(
        max_warnings=Max("warning_count")
    )
    for entry in tenant_warnings:
        Tenant.objects.filter(pk=entry["responsible_tenant_id"]).update(
            warning_count=entry["max_warnings"]
        )

    # 2. Tenant → Lease: deposit_amount, cleaning_fee_paid, tag_deposit_paid
    for lease in Lease.objects.select_related("responsible_tenant").iterator():
        tenant = lease.responsible_tenant
        lease.deposit_amount = tenant.deposit_amount
        lease.cleaning_fee_paid = tenant.cleaning_fee_paid
        lease.tag_deposit_paid = tenant.tag_deposit_paid
        lease.save(update_fields=["deposit_amount", "cleaning_fee_paid", "tag_deposit_paid"])

    # 3. Sync is_rented (only active leases)
    Apartment.objects.update(is_rented=False)
    active_apartment_ids = (
        Lease.objects.filter(is_deleted=False).values_list("apartment_id", flat=True)
    )
    Apartment.objects.filter(pk__in=active_apartment_ids).update(is_rented=True)


def migrate_data_reverse(apps, schema_editor):
    Lease = apps.get_model("core", "Lease")
    Tenant = apps.get_model("core", "Tenant")

    # Reverse: Lease → Tenant: deposit_amount, cleaning_fee_paid, tag_deposit_paid
    for lease in Lease.objects.select_related("responsible_tenant").iterator():
        tenant = lease.responsible_tenant
        tenant.deposit_amount = lease.deposit_amount
        tenant.cleaning_fee_paid = lease.cleaning_fee_paid
        tenant.tag_deposit_paid = lease.tag_deposit_paid
        tenant.save(update_fields=["deposit_amount", "cleaning_fee_paid", "tag_deposit_paid"])

    # Reverse: Tenant → Lease: warning_count (copy back to most recent lease)
    for tenant in Tenant.objects.iterator():
        Lease.objects.filter(responsible_tenant=tenant).order_by("-start_date").update(
            warning_count=tenant.warning_count
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0017_add_new_fields"),
    ]

    operations = [
        migrations.RunPython(migrate_data_forward, migrate_data_reverse),
        migrations.RenameField(
            model_name="tenant",
            old_name="rent_due_day",
            new_name="due_day",
        ),
        migrations.AlterField(
            model_name="tenant",
            name="due_day",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Dia do vencimento do aluguel",
                validators=[validate_due_day],
            ),
        ),
    ]
```

- [ ] **Step 3: Apply migration**

Run: `python manage.py migrate core 0018`
Expected: Data migrated, `rent_due_day` renamed to `due_day` with validator

- [ ] **Step 4: Verify data integrity**

Run a quick check in Django shell:
```bash
python manage.py shell -c "
from core.models import Lease, Tenant, Apartment
# Check warning_count was migrated
for t in Tenant.objects.all():
    print(f'Tenant {t.name}: due_day={t.due_day}, warning_count={t.warning_count}')
# Check deposit_amount was migrated
for l in Lease.objects.all():
    print(f'Lease {l.id}: deposit={l.deposit_amount}, clean_paid={l.cleaning_fee_paid}, tag_paid={l.tag_deposit_paid}')
# Check is_rented sync
for a in Apartment.objects.all():
    has_lease = hasattr(a, 'lease') and not a.lease.is_deleted
    print(f'Apt {a.number}: is_rented={a.is_rented}, has_active_lease={has_lease}')
"
```

- [ ] **Step 5: Commit**

```bash
git add core/migrations/0018_*.py
git commit -m "feat(core): data migration — copy fields + rename rent_due_day (migration 0018)"
```

---

## Task 3: Update Models — Remove Old Fields + Add Signal

**Files:**
- Modify: `core/models.py`
- Modify: `core/signals.py`

- [ ] **Step 1: Update Apartment model — remove fields**

In `core/models.py`, remove from Apartment:
- `contract_generated` field
- `contract_signed` field
- `interfone_configured` field
- `lease_date` field

Also make `is_rented` explicitly non-editable via API (the signal manages it):
```python
is_rented = models.BooleanField(default=False, help_text="Atualizado automaticamente via signal de Lease")
```

Check if `validate_rental_value` from `core/validators/` should be applied to `Apartment.rental_value` (now the single source of truth). If `Apartment.rental_value` only has `MinValueValidator`, consider adding `validate_rental_value` for stricter validation. If the validator is dead code, remove it.

- [ ] **Step 2: Update Tenant model — remove moved fields**

In `core/models.py`, remove from Tenant:
- `deposit_amount` field
- `cleaning_fee_paid` field
- `tag_deposit_paid` field

Rename the existing `rent_due_day` reference in the model class (already renamed in DB via migration 0018 — model code must match).

- [ ] **Step 3: Update Lease model — remove duplicated fields + index**

In `core/models.py`, remove from Lease:
- `rental_value` field
- `cleaning_fee` field
- `due_day` field
- `warning_count` field
- Remove `models.Index(fields=["due_day", "start_date"], name="lease_due_date_idx")` from Meta.indexes

- [ ] **Step 4: Update `Lease.clean()` — check validate_lease_dates**

Read `core/validators/model_validators.py` → `validate_lease_dates`. If it accesses `self.due_day`, change to `self.responsible_tenant.due_day`.

- [ ] **Step 5: Add is_rented signal to `core/signals.py`**

```python
@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender, instance, **kwargs):
    """Sync apartment.is_rented when lease is created, updated, or soft-deleted."""
    is_rented = not instance.is_deleted
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=is_rented)


@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender, instance, **kwargs):
    """Sync apartment.is_rented when lease is hard-deleted."""
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=False)
```

Also update `disconnect_all_signals()` to include receiver-specific disconnection for the new handlers:
```python
post_save.disconnect(sync_apartment_is_rented, sender=Lease)
post_delete.disconnect(sync_apartment_is_rented_on_delete, sender=Lease)
```

Remove `from __future__ import annotations` from `core/signals.py` if present.

- [ ] **Step 6: Generate removal migration**

Run: `python manage.py makemigrations core --name remove_old_fields`
Expected: Migration `0019_remove_old_fields.py` created with RemoveField and RemoveIndex operations

- [ ] **Step 7: Apply migration**

Run: `python manage.py migrate core 0019`
Expected: Old fields and stale index removed

- [ ] **Step 8: Run type checking**

Run: `mypy core/ && pyright`
Expected: Many errors (references to removed fields in serializers/views/services). This is expected — we fix those in the next tasks.

**WARNING:** Backend tests (`pytest`) WILL FAIL from this point until Task 7 completes. Do NOT run `pytest` between Task 3 and Task 7. Only run `mypy`/`pyright` for incremental validation.

- [ ] **Step 9: Commit**

```bash
git add core/models.py core/signals.py core/validators/ core/migrations/0019_*.py
git commit -m "feat(core): remove duplicated fields + add is_rented signal (migration 0019)"
```

---

## Task 4: Update Serializers

**Files:**
- Modify: `core/serializers.py`

- [ ] **Step 1: Create TenantSimpleSerializer + LeaseNestedForApartmentSerializer**

First, create `TenantSimpleSerializer` (does NOT exist yet — do not reuse the full `TenantSerializer` which includes dependents/furnitures):

```python
class TenantSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name"]
        read_only_fields = fields
```

Then create the nested serializer for lease info in apartments:

```python
class LeaseNestedForApartmentSerializer(serializers.ModelSerializer):
    responsible_tenant = TenantSimpleSerializer(read_only=True)

    class Meta:
        model = Lease
        fields = [
            "id", "contract_generated", "contract_signed", "interfone_configured",
            "start_date", "validity_months", "responsible_tenant",
        ]
        read_only_fields = fields
```

- [ ] **Step 2: Update ApartmentSerializer**

Remove from `fields`:
- `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`

Add to `fields`:
- `lease` (nested, read-only, uses `LeaseNestedForApartmentSerializer`)

Make `is_rented` read-only (remove from writable fields).

Remove the sync logic from `update()` method — the bidirectional sync between Apartment↔Lease is no longer needed since `rental_value` only lives on Apartment.

- [ ] **Step 3: Update TenantSerializer**

Rename field reference: `rent_due_day` → `due_day`
Remove from `fields`: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`
Add to `fields`: `warning_count`

- [ ] **Step 4: Update LeaseSerializer**

Remove from `fields`: `rental_value`, `cleaning_fee`, `due_day`, `warning_count`
Add to `fields`: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`

Remove the sync logic from `create()` and `update()` methods — no more `Apartment.objects.filter().update(rental_value=...)`.

- [ ] **Step 5: Update PersonIncomeSerializer**

In `get_current_value` method, change `lease.rental_value` → `lease.apartment.rental_value`. Ensure the queryset uses `select_related('apartment')`.

- [ ] **Step 6: Run type checking**

Run: `mypy core/serializers.py`
Expected: No errors in serializers (errors may persist in views/services — fixed in next tasks)

- [ ] **Step 7: Commit**

```bash
git add core/serializers.py
git commit -m "refactor(core): update serializers for single source of truth"
```

---

## Task 5: Update Views

**Files:**
- Modify: `core/views.py`

- [ ] **Step 1: Update LeaseViewSet.get_queryset()**

Ensure `select_related('apartment', 'responsible_tenant')` is applied for ALL actions (not just list/retrieve). This prevents N+1 queries when accessing `lease.apartment.rental_value` or `lease.responsible_tenant.due_day`.

- [ ] **Step 2: Update `change_due_date` action**

```python
# Update fee calculation call
fee = FeeCalculatorService.calculate_due_date_change_fee(
    rental_value=lease.apartment.rental_value,
    current_due_day=lease.responsible_tenant.due_day,
    new_due_day=new_due_day,
)
# Write to Tenant instead of Lease
tenant = lease.responsible_tenant
tenant.due_day = new_due_day
tenant.save(update_fields=["due_day"])
```

- [ ] **Step 3: Update `calculate_late_fee` action**

```python
FeeCalculatorService.calculate_late_fee(
    rental_value=lease.apartment.rental_value,
    due_day=lease.responsible_tenant.due_day,
    ...
)
```

- [ ] **Step 4: Update `generate_contract` action**

Ensure `self.get_object()` returns a lease with `apartment` and `responsible_tenant` loaded. Override `get_object()` if needed, or ensure `get_queryset()` applies `select_related` for all actions.

- [ ] **Step 5: Update ApartmentViewSet**

Remove any sync logic in the viewset. `is_rented` is now signal-managed — remove any code that manually sets it.

- [ ] **Step 6: Run type checking**

Run: `mypy core/views.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add core/views.py
git commit -m "refactor(core): update views for single source of truth"
```

---

## Task 6: Update Services

**Files:**
- Modify: `core/services/contract_service.py`
- Modify: `core/services/fee_calculator.py`
- Modify: `core/services/cash_flow_service.py`
- Modify: `core/services/dashboard_service.py`
- Modify: `core/services/daily_control_service.py`
- Modify: `core/services/financial_dashboard_service.py`
- Modify: `core/services/simulation_service.py`

- [ ] **Step 1: Update contract_service.py**

Replace all:
```
lease.rental_value  →  lease.apartment.rental_value
lease.cleaning_fee  →  lease.apartment.cleaning_fee
lease.due_day       →  lease.responsible_tenant.due_day
```

Also update the template context dict to pass `deposit_amount` from lease instead of tenant:
```python
# ANTES: "deposit_amount": tenant.deposit_amount
# DEPOIS: "deposit_amount": lease.deposit_amount
```

- [ ] **Step 2: Update fee_calculator.py**

Search for any direct references to `lease.rental_value` or `lease.due_day`. The service likely receives these as parameters (not accessing the lease directly), so check if the callers pass the correct values. If the service accesses lease fields directly, update them.

- [ ] **Step 3: Update cash_flow_service.py**

This service has 8+ references. Replace all:
```
lease.rental_value  →  lease.apartment.rental_value
lease.cleaning_fee  →  lease.apartment.cleaning_fee
lease.due_day       →  lease.responsible_tenant.due_day
```

Verify all queryset methods in this service that load leases use `select_related("apartment", "responsible_tenant")`.

- [ ] **Step 4: Update dashboard_service.py**

Same replacements. **CRITICAL:** Also update ORM annotation paths:
- Line ~89: `Sum("rental_value")` on Lease queryset → `Sum("apartment__rental_value")`
- Line ~242: `Sum("apartments__lease__rental_value", ...)` on Building queryset → `Sum("apartments__rental_value", ...)`

These are string-based ORM traversal expressions, not Python attribute access — easy to miss in a search-and-replace.

Check querysets for select_related.

- [ ] **Step 5: Update daily_control_service.py**

Same replacements. Lines ~45, 243, 248, 439.

- [ ] **Step 6: Update financial_dashboard_service.py**

Same replacements. Lines ~641, 688, 870, 874, 1716, 1723.

- [ ] **Step 7: Update simulation_service.py**

Simplify: `apartment.lease.rental_value` → `apartment.rental_value` (data is already on Apartment).

- [ ] **Step 8: Remove `from __future__ import annotations` from all modified service files**

Check each service file touched in this task. Remove the import and fix any `if TYPE_CHECKING:` guards by replacing with direct imports.

- [ ] **Step 9: Run type checking on all services**

Run: `mypy core/services/`
Expected: No errors

- [ ] **Step 10: Commit**

```bash
git add core/services/
git commit -m "refactor(core): update all services for single source of truth"
```

---

## Task 7: Update Backend Tests

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/e2e/test_financial_workflow.py`
- Modify: `tests/integration/test_cash_flow_api.py`
- Modify: `tests/integration/test_financial_dashboard_api.py`
- Modify: `tests/integration/test_financial_api_simple.py`
- Modify: `tests/integration/test_income_payment_api.py`
- Modify: `tests/integration/test_expense_api.py`
- Modify: `tests/unit/test_financial/test_daily_control_service.py`
- Modify: `tests/unit/test_financial/test_financial_dashboard_service.py`

- [ ] **Step 1: Update conftest.py fixtures**

Update `sample_lease_data` — remove `rental_value`, `cleaning_fee`, `due_day`, `warning_count`. Add `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`.

Update `sample_tenant_data` — rename `rent_due_day` → `due_day`, add `warning_count`. Remove `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`.

- [ ] **Step 2: Update E2E test**

In `test_financial_workflow.py`, update all references to `lease.rental_value` → access via apartment, and `tenant.deposit_amount` → access via lease. This is the largest test file — update all ~30+ references.

- [ ] **Step 3: Update integration tests**

Update all integration test files to use new field locations in API request/response payloads.

- [ ] **Step 4: Update unit tests**

Update service test files to use new field access paths.

- [ ] **Step 5: Create integration tests for lease actions**

Create `tests/integration/test_lease_actions.py` with tests for:
- `change_due_date` — verifies it writes to `Tenant.due_day` (not Lease), reads correct `rental_value` from apartment
- `calculate_late_fee` — verifies correct `rental_value` and `due_day` sources
- `generate_contract` — verifies all template context values come from the new field locations
- Signal test: creating a Lease sets `apartment.is_rented = True`, soft-deleting sets it to `False`

These are the most critical behavioral changes and had NO pre-existing tests.

- [ ] **Step 6: Run all backend tests**

Run: `python -m pytest tests/ -x -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add tests/
git commit -m "test(core): update all backend tests for domain model refactor"
```

---

## Task 8: Update Frontend Schemas

**Files:**
- Modify: `frontend/lib/schemas/apartment.schema.ts`
- Modify: `frontend/lib/schemas/lease.schema.ts`
- Modify: `frontend/lib/schemas/tenant.schema.ts`

- [ ] **Step 1: Update apartment.schema.ts**

Remove fields: `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`
Add nested `lease` field (optional, for when apartment has an active lease):
```typescript
lease: z.object({
  id: z.number(),
  contract_generated: z.boolean(),
  contract_signed: z.boolean(),
  interfone_configured: z.boolean(),
  start_date: z.string(),
  validity_months: z.number(),
  responsible_tenant: z.object({ id: z.number(), name: z.string() }),
}).nullable().optional(),
```

- [ ] **Step 2: Update lease.schema.ts**

Remove fields: `rental_value`, `cleaning_fee`, `due_day`, `warning_count`
Add fields: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`

The `apartment` nested object in the lease response now includes `rental_value` and `cleaning_fee` (it already should).
The `responsible_tenant` nested object now includes `due_day`.

- [ ] **Step 3: Update tenant.schema.ts**

Rename: `rent_due_day` → `due_day`
Add: `warning_count: z.number()`
Remove: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`

- [ ] **Step 4: Run type checking**

Run (in `frontend/`): `npm run type-check`
Expected: Many errors in components that reference old fields. Expected — we fix those next.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/schemas/
git commit -m "refactor(frontend): update Zod schemas for domain model refactor"
```

---

## Task 9: Update Frontend Hooks + Cache Invalidation

**Files:**
- Modify: `frontend/lib/api/hooks/use-apartments.ts`
- Modify: `frontend/lib/api/hooks/use-leases.ts`
- Modify: `frontend/lib/api/hooks/use-tenants.ts`
- Modify: `frontend/lib/api/hooks/use-furniture.ts`

- [ ] **Step 1: Update use-apartments.ts — add cross-invalidation**

All apartment mutations should also invalidate `['leases']` and `['dashboard']`:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['apartments'] });
  queryClient.invalidateQueries({ queryKey: ['leases'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard'] });
},
```

- [ ] **Step 2: Update use-leases.ts — update cache invalidation**

Lease mutations should invalidate `['leases']`, `['apartments']`, `['dashboard']`:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['leases'] });
  queryClient.invalidateQueries({ queryKey: ['apartments'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard'] });
},
```

Remove any sync logic that was previously in the mutation (e.g., updating apartment rental_value client-side).

- [ ] **Step 3: Update use-tenants.ts — add cross-invalidation**

Tenant mutations should also invalidate `['leases']`:
```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: ['tenants'] });
  queryClient.invalidateQueries({ queryKey: ['leases'] });
},
```

- [ ] **Step 4: Update use-furniture.ts — add cross-invalidation**

Furniture mutations should invalidate `['furniture']`, `['apartments']`, `['tenants']`, `['leases']`.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api/hooks/
git commit -m "refactor(frontend): update hooks cache invalidation for domain model refactor"
```

---

## Task 10: Update Frontend — Apartment Page + Form

**Files:**
- Modify: `frontend/app/(dashboard)/apartments/_components/apartment-form-modal.tsx`
- Modify: `frontend/app/(dashboard)/apartments/page.tsx`

- [ ] **Step 1: Update apartment-form-modal.tsx**

Remove form fields: `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`
Make `is_rented` a display-only field (badge/indicator), not an editable input.
Remove the old sync logic in the form submission handler.

- [ ] **Step 2: Update apartments page table columns**

Remove columns: `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`
Optionally show these as `apartment.lease?.contract_generated` etc.
`is_rented` stays as a badge column (read-only).

- [ ] **Step 3: Run type checking**

Run (in `frontend/`): `npm run type-check`
Expected: Apartment-related errors resolved

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/apartments/
git commit -m "refactor(frontend): update apartment page for domain model refactor"
```

---

## Task 11: Update Frontend — Lease Page + Form

**Files:**
- Modify: `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/late-fee-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/due-date-modal.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx`

- [ ] **Step 1: Update lease-form-modal.tsx — multi-model save**

The form still shows `rental_value`, `cleaning_fee`, `due_day` — but saving them now calls different endpoints:

```typescript
const onSubmit = async (data: LeaseFormData) => {
  // 1. Update Apartment fields if changed
  if (apartmentFieldsChanged) {
    await updateApartment({
      id: lease.apartment.id,
      rental_value: data.rental_value,
      cleaning_fee: data.cleaning_fee,
    });
  }

  // 2. Update Tenant fields if changed
  if (tenantFieldsChanged) {
    await updateTenant({
      id: lease.responsible_tenant.id,
      due_day: data.due_day,
    });
  }

  // 3. Update Lease's own fields
  await updateLease({ id: lease.id, ...leaseOnlyFields });
};
```

Remove the old `rental_value`, `cleaning_fee`, `due_day` from the lease mutation payload.
Add `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid` to the lease form.

- [ ] **Step 2: Update lease-table-columns.tsx**

Update column accessors:
```typescript
// ANTES: row.rental_value
// DEPOIS: row.apartment.rental_value

// ANTES: row.due_day
// DEPOIS: row.responsible_tenant.due_day
```

- [ ] **Step 3: Update late-fee-modal.tsx**

Update field access paths from `lease.rental_value` → `lease.apartment.rental_value` and `lease.due_day` → `lease.responsible_tenant.due_day`.

- [ ] **Step 4: Update due-date-modal.tsx**

Update field access paths for `due_day` → `lease.responsible_tenant.due_day`.

- [ ] **Step 5: Update contract-generate-modal.tsx**

Update any field paths that reference lease fields moved to apartment or tenant.

- [ ] **Step 6: Run type checking**

Run (in `frontend/`): `npm run type-check`
Expected: Lease-related errors resolved

- [ ] **Step 7: Commit**

```bash
git add frontend/app/\(dashboard\)/leases/
git commit -m "refactor(frontend): update lease page for domain model refactor"
```

---

## Task 12: Update Frontend — Tenant Page + Wizard

**Files:**
- Modify: `frontend/app/(dashboard)/tenants/_components/wizard/index.tsx`
- Modify: `frontend/app/(dashboard)/tenants/_components/wizard/types.ts`
- Modify: `frontend/app/(dashboard)/tenants/_components/dependent-form-list.tsx`

- [ ] **Step 1: Update wizard/types.ts**

Remove: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`
Rename: `rent_due_day` → `due_day`

- [ ] **Step 2: Update wizard/index.tsx**

Update payload construction — remove moved fields, use `due_day` instead of `rent_due_day`.

- [ ] **Step 3: Update dependent-form-list.tsx**

Update local `TenantFormData` type — remove `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`, rename `rent_due_day` → `due_day`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/tenants/
git commit -m "refactor(frontend): update tenant wizard for domain model refactor"
```

---

## Task 13: Update Frontend — Contract Template + Other Components

**Files:**
- Modify: `frontend/app/(dashboard)/contract-template/page.tsx`
- Modify: `frontend/components/contract-editor/variable-inserter.tsx`
- Modify: `frontend/components/search/global-search.tsx`
- Modify: `frontend/lib/hooks/use-export.ts`

- [ ] **Step 1: Update contract-template/page.tsx**

Update template variable references:
```
tenant.deposit_amount → lease.deposit_amount
tenant.rent_due_day → tenant.due_day
```

- [ ] **Step 2: Update variable-inserter.tsx**

Update the variable list to reflect new field locations. Variables like `rental_value` are now under apartment, `due_day` under tenant, `deposit_amount` under lease.

- [ ] **Step 3: Update global-search.tsx**

Update any field references used for search result display.

- [ ] **Step 4: Update use-export.ts**

Update export field mappings — `rental_value` comes from apartment, `due_day` from tenant, etc.

- [ ] **Step 5: Run full type checking**

Run (in `frontend/`): `npm run type-check`
Expected: No errors remaining

- [ ] **Step 6: Commit**

```bash
git add frontend/components/ frontend/lib/hooks/ frontend/app/\(dashboard\)/contract-template/
git commit -m "refactor(frontend): update remaining components for domain model refactor"
```

---

## Task 14: Update Frontend Tests + Mock Data

**Files:**
- Modify: `frontend/tests/mocks/data/apartments.ts`
- Modify: `frontend/tests/mocks/data/leases.ts`
- Modify: `frontend/tests/mocks/data/tenants.ts`
- Modify: `frontend/tests/mocks/handlers.ts`
- Modify: `frontend/lib/api/hooks/__tests__/use-apartments.test.tsx`
- Modify: `frontend/lib/api/hooks/__tests__/use-leases.test.tsx`
- Modify: `frontend/lib/api/hooks/__tests__/use-tenants.test.tsx`
- Modify: `frontend/lib/api/hooks/__tests__/use-dashboard.test.tsx`

- [ ] **Step 1: Update mock data — apartments.ts**

Remove: `contract_generated`, `contract_signed`, `interfone_configured`, `lease_date`
Add: `lease` nested object (or `null`)

- [ ] **Step 2: Update mock data — leases.ts**

Remove: `rental_value`, `cleaning_fee`, `due_day`, `warning_count`
Add: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`
Ensure `apartment` nested object has `rental_value` and `cleaning_fee`.
Ensure `responsible_tenant` nested object has `due_day`.

- [ ] **Step 3: Update mock data — tenants.ts**

Rename: `rent_due_day` → `due_day`
Add: `warning_count`
Remove: `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`

- [ ] **Step 4: Update MSW handlers**

Update response shapes in `handlers.ts` to match new API structure.

- [ ] **Step 5: Update hook test files**

Update assertions in all test files to expect new field locations.

- [ ] **Step 6: Run frontend tests**

Run (in `frontend/`): `npm run test:unit`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add frontend/tests/ frontend/lib/api/hooks/__tests__/
git commit -m "test(frontend): update frontend tests for domain model refactor"
```

---

## Task 15: Full Audit + Final Verification

**Files:** All

- [ ] **Step 1: Run backend audit grep**

```bash
rg "lease\.(rental_value|cleaning_fee|due_day|warning_count)" core/ tests/
rg "apartment\.(contract_generated|contract_signed|interfone_configured|lease_date)" core/ tests/
rg "tenant\.(deposit_amount|cleaning_fee_paid|tag_deposit_paid|rent_due_day)" core/ tests/
```
Expected: No matches (except in migration files, which is OK)

- [ ] **Step 2: Run frontend audit grep**

```bash
rg "(rent_due_day|lease_date)" frontend/
rg "lease\.(rental_value|cleaning_fee|due_day)" frontend/
```
Expected: No matches

- [ ] **Step 3: Run full backend test suite**

Run: `python -m pytest tests/ -x -v`
Expected: All tests pass

- [ ] **Step 4: Run backend lint + type check**

Run: `ruff check && mypy core/`
Expected: No errors

- [ ] **Step 5: Run frontend build**

Run (in `frontend/`): `npm run build`
Expected: Build succeeds

- [ ] **Step 6: Run frontend lint + type check**

Run (in `frontend/`): `npm run lint && npm run type-check`
Expected: No errors

- [ ] **Step 7: Run frontend tests**

Run (in `frontend/`): `npm run test:unit`
Expected: All tests pass

- [ ] **Step 8: Verify import script**

Run: `rg "(rent_due_day|deposit_amount|cleaning_fee_paid|tag_deposit_paid)" scripts/`
Confirm that `scripts/import_financial_data.py` does not reference any removed/renamed fields. Update if needed.

- [ ] **Step 9: Manual smoke test**

Start both servers and verify:
1. Apartment list page loads — shows `is_rented` badge, no old columns
2. Edit apartment `rental_value` — lease page reflects new value
3. Lease list page loads — shows `rental_value` from nested apartment
4. Edit `due_day` via lease form — tenant record updates
5. Create new lease — `is_rented` flips to true automatically
6. Generate contract PDF — all values render correctly

- [ ] **Step 10: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "fix(core): address audit findings from domain model refactor"
```
