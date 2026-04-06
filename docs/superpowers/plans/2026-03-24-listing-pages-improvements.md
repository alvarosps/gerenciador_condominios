# Listing Pages Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sortable columns, building accordions, tenant lease columns, and contract management actions (terminate, transfer, create) across the listing pages.

**Architecture:** Backend-first approach — model migration and new endpoints first, then frontend changes. The `Lease.apartment` field changes from `OneToOneField` to `ForeignKey` with a conditional unique constraint, enabling soft delete without blocking new leases. New service functions handle lease termination and transfer atomically. Frontend gains sorting in DataTable, building-grouped accordions, and new action modals.

**Tech Stack:** Django 5.2, DRF, PostgreSQL (migration), Next.js 14, React 18, TanStack Query v5, shadcn/ui Accordion, Zod.

**Spec:** `docs/superpowers/specs/2026-03-24-listing-pages-sort-accordion-columns-design.md`

---

## Task 1: Migration — Lease.apartment OneToOneField → ForeignKey

**Files:**
- Modify: `core/models.py:501` (Lease.apartment field + Meta.constraints)
- Create: `core/migrations/0017_lease_apartment_fk.py` (auto-generated)

- [ ] **Step 1: Change the model field**

In `core/models.py`, change line 501 from:
```python
apartment = models.OneToOneField(Apartment, on_delete=models.CASCADE, related_name="lease")
```
to:
```python
apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE, related_name="leases")
```

And add to `class Meta` (around line 556), inside the existing `constraints` list or alongside `indexes`:
```python
constraints = [
    models.UniqueConstraint(
        fields=["apartment"],
        condition=models.Q(is_deleted=False),
        name="unique_active_lease_per_apartment",
    )
]
```

Keep the existing `indexes` list as-is.

- [ ] **Step 2: Generate and review migration**

Run: `python manage.py makemigrations core --name lease_apartment_fk`
Expected: New migration file in `core/migrations/` with `AlterField` + `AddConstraint`

- [ ] **Step 3: Apply migration**

Run: `python manage.py migrate`
Expected: Migration applies successfully with no errors.

- [ ] **Step 4: Commit**

```bash
git add core/models.py core/migrations/
git commit -m "refactor(models): change Lease.apartment from OneToOneField to ForeignKey"
```

---

## Task 2: Update Signals

**Files:**
- Modify: `core/signals.py:154-163` (both signal handlers)
- Test: `tests/unit/test_signals.py`

- [ ] **Step 1: Write failing tests for new signal logic**

In `tests/unit/test_signals.py`, add tests that verify the query-based approach. If the file already has tests for `sync_apartment_is_rented`, update them. Add these test cases:

```python
@pytest.mark.django_db
class TestSyncApartmentIsRentedAfterFKChange:
    """Tests for signal logic after OneToOneField → ForeignKey migration."""

    def test_soft_delete_lease_marks_apartment_available(self, sample_building_data):
        """Soft-deleting the only active lease should set is_rented=False."""
        building = Building.objects.create(**sample_building_data)
        apartment = Apartment.objects.create(building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2)
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12,
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True

        lease.delete()  # soft delete
        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_soft_delete_with_historical_lease_still_available(self, sample_building_data):
        """Saving a historical soft-deleted lease should NOT mark apartment as rented."""
        building = Building.objects.create(**sample_building_data)
        apartment = Apartment.objects.create(building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2)
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        # Create and soft-delete a historical lease
        old_lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2025-01-01", validity_months=12,
        )
        old_lease.delete()  # soft delete
        apartment.refresh_from_db()
        assert apartment.is_rented is False

        # Re-save the historical lease (e.g., audit update) — should NOT mark as rented
        old_lease.is_deleted = True  # ensure still deleted
        old_lease.save()
        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_create_new_lease_after_soft_delete_marks_rented(self, sample_building_data):
        """Creating a new lease after soft-deleting old one should mark apartment rented."""
        building = Building.objects.create(**sample_building_data)
        apartment = Apartment.objects.create(building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2)
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        old_lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2025-01-01", validity_months=12,
        )
        old_lease.delete()  # soft delete

        # Create new lease for same apartment
        new_lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12,
        )
        apartment.refresh_from_db()
        assert apartment.is_rented is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_signals.py::TestSyncApartmentIsRentedAfterFKChange -v`
Expected: `test_soft_delete_with_historical_lease_still_available` FAILS (signal uses `not instance.is_deleted` which returns `False` since the instance IS deleted, so it sets `is_rented=False` — but that's actually the correct result for this case with the old code... let me reconsider).

Actually the test that will fail is the one where re-saving a deleted lease incorrectly triggers `is_rented = not True = False`, but if no active lease exists it's correct. The key failing test is `test_create_new_lease_after_soft_delete_marks_rented` — the unique constraint from Task 1 allows this now but the old signal logic still works. The real breakage is in the `_on_delete` handler. Run all tests to check baseline.

Run: `python -m pytest tests/unit/test_signals.py -v -x`

- [ ] **Step 3: Update signal handlers**

In `core/signals.py`, replace lines 154-163:

```python
@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented based on whether any active lease exists."""
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)


@receiver(post_delete, sender=Lease)
def sync_apartment_is_rented_on_delete(sender: type[Lease], instance: Lease, **kwargs: Any) -> None:
    """Sync apartment.is_rented when lease is hard-deleted."""
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_signals.py -v`
Expected: All signal tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/signals.py tests/unit/test_signals.py
git commit -m "refactor(signals): update sync_apartment_is_rented for ForeignKey lease model"
```

---

## Task 3: Update Serializers

**Files:**
- Modify: `core/serializers.py:110,128` (ApartmentSerializer lease field)
- Modify: `frontend/lib/schemas/apartment.schema.ts:22-33` (lease → active_lease)

- [ ] **Step 1: Update ApartmentSerializer**

In `core/serializers.py`, the `ApartmentSerializer` has `lease = LeaseNestedForApartmentSerializer(read_only=True)` at line 110 which uses the OneToOne reverse accessor `apartment.lease`. With ForeignKey, this becomes `apartment.leases` (QuerySet).

Change line 110 from:
```python
lease = LeaseNestedForApartmentSerializer(read_only=True)
```
to:
```python
active_lease = serializers.SerializerMethodField()
```

Add the method inside `ApartmentSerializer`:
```python
def get_active_lease(self, obj: Apartment) -> dict[str, Any] | None:
    """Return the active (non-deleted) lease for this apartment, if any."""
    # Use all() to leverage prefetch cache (first() bypasses it)
    lease = next(iter(obj.leases.all()), None)
    if lease is None:
        return None
    return LeaseNestedForApartmentSerializer(lease).data
```

Update `fields` in `Meta` (line 128): change `"lease"` to `"active_lease"`.

- [ ] **Step 2: Update ApartmentViewSet queryset optimization**

In `core/views.py`, in `ApartmentViewSet.get_queryset()` (around line 114-118), add `prefetch_related("leases")`:
```python
queryset = queryset.select_related(
    "building"
).prefetch_related(
    "furnitures",
    "leases",  # For active_lease serializer method
)
```

- [ ] **Step 3: Update frontend apartment schema**

In `frontend/lib/schemas/apartment.schema.ts`, change lines 22-33 from `lease` to `active_lease`:
```typescript
active_lease: z
    .object({
      id: z.number(),
      contract_generated: z.boolean(),
      contract_signed: z.boolean(),
      interfone_configured: z.boolean(),
      start_date: z.string(),
      validity_months: z.number(),
      responsible_tenant: z.object({ id: z.number(), name: z.string() }),
    })
    .nullable()
    .optional(),
```

- [ ] **Step 4: Update frontend references to `apartment.lease`**

Search all frontend files for `apartment.lease` or `.lease` on Apartment type and update to `apartment.active_lease`. Key files:
- `frontend/lib/api/hooks/use-apartments.ts` — if it strips `lease` on create/update, change to `active_lease`
- Any component rendering apartment lease info

Run: `cd frontend && npm run type-check`
Expected: No TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add core/serializers.py core/views.py frontend/lib/schemas/apartment.schema.ts
git commit -m "refactor(serializers): update ApartmentSerializer for ForeignKey lease model"
```

---

## Task 4: Update Backend References

**Files:**
- Modify: `core/services/simulation_service.py:237,263` (remove `select_related("lease")`)
- Modify: `core/views.py` (update comments)

- [ ] **Step 1: Fix simulation_service.py**

In `core/services/simulation_service.py`, lines 237 and 263 use `select_related("lease")` on Apartment. Since these functions only access `apartment.rental_value` (not the lease), simply remove the `select_related("lease")`:

Line 237: `apartment = Apartment.objects.select_related("lease").get(pk=apartment_id)` → `apartment = Apartment.objects.get(pk=apartment_id)`

Line 263: same change.

- [ ] **Step 1b: Fix cash_flow_service.py**

In `core/services/cash_flow_service.py`, search for `select_related("lease")` and `apt.lease` patterns. Change:
- `select_related("lease")` → remove (or change to `prefetch_related("leases")` if lease data is actually accessed)
- `apt.lease` → `next(iter(apt.leases.all()), None)` — guard with `None` check instead of `try/except Lease.DoesNotExist` (that exception pattern is OneToOne-specific)

- [ ] **Step 1c: Fix financial_dashboard_service.py**

In `core/services/financial_dashboard_service.py`, same pattern as cash_flow_service:
- `select_related("lease")` → remove or `prefetch_related("leases")`
- `apt.lease` → `next(iter(apt.leases.all()), None)` with `None` check

- [ ] **Step 2: Update view comments**

In `core/views.py`, update comments that reference "OneToOne" for the lease relationship to "ForeignKey". Around lines 109 and 293.

- [ ] **Step 3: Run full backend tests**

Run: `python -m pytest tests/ -x --timeout=30`
Expected: All tests pass. If any test references `apartment.lease` (singular), fix them to use `apartment.leases.filter(is_deleted=False).first()` or the serializer's `active_lease`.

- [ ] **Step 4: Run type checking**

Run: `mypy core/ && pyright`
Expected: No type errors from the model/serializer changes.

- [ ] **Step 5: Commit**

```bash
git add core/services/simulation_service.py core/views.py
git commit -m "refactor(services): update references for ForeignKey lease model"
```

---

## Task 5: Backend — terminate_lease Service + Endpoint

**Files:**
- Create: `core/services/lease_service.py` (new service)
- Modify: `core/views.py` (add `terminate` action to LeaseViewSet)
- Test: `tests/unit/test_lease_service.py` or add to existing test file

- [ ] **Step 1: Write failing tests**

Create tests for the terminate service:

```python
# tests/unit/test_lease_service.py
import pytest
from django.contrib.auth import get_user_model
from core.models import Building, Apartment, Tenant, Lease
from core.services.lease_service import terminate_lease

User = get_user_model()


@pytest.mark.django_db
class TestTerminateLease:
    def test_terminate_soft_deletes_lease(self, sample_building_data):
        building = Building.objects.create(**sample_building_data)
        apartment = Apartment.objects.create(
            building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2
        )
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12,
            contract_generated=True, contract_signed=True, interfone_configured=True,
        )
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)

        terminate_lease(lease.id, user)

        lease.refresh_from_db()
        assert lease.is_deleted is True
        assert lease.contract_generated is False
        assert lease.contract_signed is False
        assert lease.interfone_configured is False

    def test_terminate_marks_apartment_available(self, sample_building_data):
        building = Building.objects.create(**sample_building_data)
        apartment = Apartment.objects.create(
            building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2
        )
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        lease = Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12,
        )
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)

        terminate_lease(lease.id, user)

        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_terminate_nonexistent_lease_raises(self):
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)
        with pytest.raises(Lease.DoesNotExist):
            terminate_lease(99999, user)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_lease_service.py::TestTerminateLease -v`
Expected: FAIL with `ImportError: cannot import name 'terminate_lease'`

- [ ] **Step 3: Implement service**

Create `core/services/lease_service.py`:

```python
from django.db import transaction

from core.models import Lease


@transaction.atomic
def terminate_lease(lease_id: int, user: object) -> None:
    """Terminate a lease: reset contract fields, soft delete.

    The signal sync_apartment_is_rented handles setting apartment.is_rented = False.
    """
    lease = Lease.objects.get(pk=lease_id)
    # Use update() to reset fields without triggering signals, then soft delete
    Lease.objects.filter(pk=lease_id).update(
        contract_generated=False, contract_signed=False, interfone_configured=False,
    )
    lease.refresh_from_db()
    lease.delete(deleted_by=user)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_lease_service.py::TestTerminateLease -v`
Expected: All PASS.

- [ ] **Step 5: Add API endpoint**

In `core/views.py`, add a `terminate` action to `LeaseViewSet`:

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status
from core.services.lease_service import terminate_lease

# Inside LeaseViewSet:
@action(detail=True, methods=["post"], url_path="terminate")
def terminate(self, request, pk=None):
    """Terminate a lease contract."""
    if not request.user.is_staff:
        return Response(
            {"detail": "Apenas administradores podem encerrar contratos."},
            status=http_status.HTTP_403_FORBIDDEN,
        )
    lease = self.get_object()
    terminate_lease(lease.id, request.user)
    return Response({"detail": "Contrato encerrado com sucesso."}, status=http_status.HTTP_200_OK)
```

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -x --timeout=30`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add core/services/lease_service.py core/views.py tests/unit/test_lease_service.py
git commit -m "feat(lease): add terminate_lease service and API endpoint"
```

---

## Task 6: Backend — transfer_lease Service + Endpoint

**Files:**
- Modify: `core/services/lease_service.py` (add transfer function)
- Modify: `core/views.py` (add `transfer` action)
- Test: `tests/unit/test_lease_service.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_lease_service.py`:

```python
from core.services.lease_service import transfer_lease


@pytest.mark.django_db
class TestTransferLease:
    def test_transfer_creates_new_lease_on_target_apartment(self, sample_building_data):
        building = Building.objects.create(**sample_building_data)
        old_apt = Apartment.objects.create(
            building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2
        )
        new_apt = Apartment.objects.create(
            building=building, number=102, rental_value=1200, cleaning_fee=100, max_tenants=2
        )
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        old_lease = Lease.objects.create(
            apartment=old_apt, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12, tag_fee=50,
            contract_generated=True, contract_signed=True, interfone_configured=True,
        )
        old_lease.tenants.add(tenant)
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)

        new_lease = transfer_lease(
            lease_id=old_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
                "deposit_amount": None,
                "cleaning_fee_paid": False,
                "tag_deposit_paid": False,
            },
            user=user,
        )

        assert new_lease.apartment_id == new_apt.id
        assert new_lease.contract_generated is False
        assert new_lease.contract_signed is False
        assert new_lease.interfone_configured is False

    def test_transfer_soft_deletes_old_lease(self, sample_building_data):
        building = Building.objects.create(**sample_building_data)
        old_apt = Apartment.objects.create(
            building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2
        )
        new_apt = Apartment.objects.create(
            building=building, number=102, rental_value=1200, cleaning_fee=100, max_tenants=2
        )
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        old_lease = Lease.objects.create(
            apartment=old_apt, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12, tag_fee=50,
        )
        old_lease.tenants.add(tenant)
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)

        transfer_lease(
            lease_id=old_lease.id,
            payload={
                "apartment_id": new_apt.id,
                "responsible_tenant_id": tenant.id,
                "tenant_ids": [tenant.id],
                "start_date": "2026-01-01",
                "validity_months": 12,
                "tag_fee": 50,
            },
            user=user,
        )

        old_lease.refresh_from_db()
        assert old_lease.is_deleted is True
        old_apt.refresh_from_db()
        assert old_apt.is_rented is False
        new_apt.refresh_from_db()
        assert new_apt.is_rented is True

    def test_transfer_to_rented_apartment_raises(self, sample_building_data):
        building = Building.objects.create(**sample_building_data)
        old_apt = Apartment.objects.create(
            building=building, number=101, rental_value=1000, cleaning_fee=100, max_tenants=2
        )
        rented_apt = Apartment.objects.create(
            building=building, number=102, rental_value=1200, cleaning_fee=100, max_tenants=2,
            is_rented=True,
        )
        tenant = Tenant.objects.create(name="Test", cpf_cnpj="12345678901", phone="11999999999")
        tenant2 = Tenant.objects.create(name="Other", cpf_cnpj="98765432100", phone="11888888888")
        Lease.objects.create(
            apartment=rented_apt, responsible_tenant=tenant2,
            start_date="2026-01-01", validity_months=12, tag_fee=50,
        )
        old_lease = Lease.objects.create(
            apartment=old_apt, responsible_tenant=tenant,
            start_date="2026-01-01", validity_months=12, tag_fee=50,
        )
        user = User.objects.create_user(username="admin", password="pass", is_staff=True)

        with pytest.raises(ValueError, match="já está alugado"):
            transfer_lease(
                lease_id=old_lease.id,
                payload={
                    "apartment_id": rented_apt.id,
                    "responsible_tenant_id": tenant.id,
                    "tenant_ids": [tenant.id],
                    "start_date": "2026-01-01",
                    "validity_months": 12,
                    "tag_fee": 50,
                },
                user=user,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_lease_service.py::TestTransferLease -v`
Expected: FAIL with `ImportError: cannot import name 'transfer_lease'`

- [ ] **Step 3: Implement service**

Add to `core/services/lease_service.py`:

```python
from datetime import date
from decimal import Decimal


@transaction.atomic
def transfer_lease(lease_id: int, payload: dict, user: object) -> Lease:
    """Transfer a lease to a new apartment.

    Soft-deletes the old lease and creates a new one on the target apartment.
    Signals handle apartment.is_rented sync automatically.
    """
    old_lease = Lease.objects.select_related("apartment").get(pk=lease_id)
    new_apartment_id = payload["apartment_id"]

    # Extract all keys upfront — never mutate the caller's dict
    new_apartment_id: int = payload["apartment_id"]
    responsible_tenant_id: int = payload["responsible_tenant_id"]
    tenant_ids: list[int] = payload.get("tenant_ids", [])

    # Validate target apartment is not rented
    if Lease.objects.filter(apartment_id=new_apartment_id).exists():
        raise ValueError("O apartamento destino já está alugado.")

    # Terminate old lease — use update() to avoid extra signal fire, then soft delete
    Lease.objects.filter(pk=old_lease.pk).update(
        contract_generated=False, contract_signed=False, interfone_configured=False,
    )
    old_lease.refresh_from_db()
    old_lease.delete(deleted_by=user)

    # Create new lease
    new_lease = Lease.objects.create(
        apartment_id=new_apartment_id,
        responsible_tenant_id=responsible_tenant_id,
        start_date=payload.get("start_date", date.today()),
        validity_months=payload.get("validity_months", 12),
        tag_fee=Decimal(str(payload.get("tag_fee", 0))),
        deposit_amount=Decimal(str(payload["deposit_amount"])) if payload.get("deposit_amount") else None,
        cleaning_fee_paid=payload.get("cleaning_fee_paid", False),
        tag_deposit_paid=payload.get("tag_deposit_paid", False),
        contract_generated=False,
        contract_signed=False,
        interfone_configured=False,
    )
    if tenant_ids:
        new_lease.tenants.set(tenant_ids)

    return new_lease
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_lease_service.py::TestTransferLease -v`
Expected: All PASS.

- [ ] **Step 5: Add API endpoint**

In `core/views.py`, add `transfer` action to `LeaseViewSet`:

```python
from core.services.lease_service import transfer_lease

# Inside LeaseViewSet:
@action(detail=True, methods=["post"], url_path="transfer")
def transfer(self, request, pk=None):
    """Transfer a lease to a new apartment."""
    if not request.user.is_staff:
        return Response(
            {"detail": "Apenas administradores podem transferir contratos."},
            status=http_status.HTTP_403_FORBIDDEN,
        )
    lease = self.get_object()
    try:
        new_lease = transfer_lease(lease.id, request.data.copy(), request.user)
    except ValueError as e:
        return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    serializer = self.get_serializer(new_lease)
    return Response(serializer.data, status=http_status.HTTP_201_CREATED)
```

- [ ] **Step 6: Run full backend test suite**

Run: `python -m pytest tests/ -x --timeout=30`
Expected: All pass.

- [ ] **Step 7: Commit**

```bash
git add core/services/lease_service.py core/views.py tests/unit/test_lease_service.py
git commit -m "feat(lease): add transfer_lease service and API endpoint"
```

---

## Task 7: Frontend — DataTable Sorting with Dual Arrows

**Files:**
- Modify: `frontend/components/tables/data-table.tsx`

- [ ] **Step 1: Add sort state and logic**

In `data-table.tsx`, add state after the existing `useState` calls (around line 62):

```typescript
const [sortKey, setSortKey] = useState<string | null>(null);
const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null);
```

Add the sorted data `useMemo` before `paginatedData` (replace line 75):

```typescript
const sortedData = useMemo(() => {
  if (!sortKey || !sortDirection) return dataSource;
  const sorter = columns.find((c) => c.key === sortKey)?.sorter;
  if (!sorter) return dataSource;
  return [...dataSource].sort((a, b) =>
    sortDirection === 'desc' ? -sorter(a, b) : sorter(a, b)
  );
}, [dataSource, columns, sortKey, sortDirection]);

const total = paginationConfig.total ?? sortedData.length;
const totalPages = Math.ceil(total / pageSize);
const start = (currentPage - 1) * pageSize;
const end = start + pageSize;
const paginatedData = sortedData.slice(start, end);
```

Remove the old `total`, `totalPages`, `start`, `end`, `paginatedData` lines (73-75).

Add sort handler:
```typescript
const handleSort = (key: string, direction: 'asc' | 'desc'): void => {
  if (sortKey === key && sortDirection === direction) {
    setSortKey(null);
    setSortDirection(null);
  } else {
    setSortKey(key);
    setSortDirection(direction);
  }
  setCurrentPage(1);
};
```

- [ ] **Step 2: Render sort indicators in header**

Replace the column header rendering (around line 209) from:
```tsx
<TableHead key={column.key} style={{ width: column.width }}>
  {column.title}
</TableHead>
```
to:
```tsx
<TableHead key={column.key} style={{ width: column.width }}>
  {column.sorter ? (
    <div className="flex items-center gap-1">
      <span>{column.title}</span>
      <div className="flex flex-col -space-y-1 ml-1">
        <button
          type="button"
          onClick={() => handleSort(column.key, 'asc')}
          className={cn(
            'text-[10px] leading-none cursor-pointer hover:text-primary transition-colors',
            sortKey === column.key && sortDirection === 'asc'
              ? 'text-primary'
              : 'text-muted-foreground/30'
          )}
          aria-label={`Sort ${column.title} ascending`}
        >
          ▲
        </button>
        <button
          type="button"
          onClick={() => handleSort(column.key, 'desc')}
          className={cn(
            'text-[10px] leading-none cursor-pointer hover:text-primary transition-colors',
            sortKey === column.key && sortDirection === 'desc'
              ? 'text-primary'
              : 'text-muted-foreground/30'
          )}
          aria-label={`Sort ${column.title} descending`}
        >
          ▼
        </button>
      </div>
    </div>
  ) : (
    column.title
  )}
</TableHead>
```

Add `import { cn } from '@/lib/utils';` at the top if not already present. Also add `useMemo` to the React import.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/tables/data-table.tsx
git commit -m "feat(ui): add dual-arrow column sorting to DataTable"
```

---

## Task 8: Frontend — Install Accordion + Add Lease Sorters

**Files:**
- Create: `frontend/components/ui/accordion.tsx` (via shadcn CLI)
- Modify: `frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx` (add missing sorters)

- [ ] **Step 1: Install shadcn Accordion**

Run: `cd frontend && npx shadcn@latest add accordion`
Expected: Creates `components/ui/accordion.tsx` and adds `@radix-ui/react-accordion` to package.json.

- [ ] **Step 2: Add missing sorters to lease columns**

In `lease-table-columns.tsx`, add sorters to columns that don't have them yet.

Add to the "Inquilino Responsável" column (around line 119):
```typescript
sorter: (a: Lease, b: Lease) =>
  (a.responsible_tenant?.name ?? '').localeCompare(b.responsible_tenant?.name ?? ''),
```

Add to the "Status" column (around line 149):
```typescript
sorter: (a: Lease, b: Lease) => {
  const priority: Record<string, number> = { red: 0, orange: 1, green: 2, blue: 3 };
  const aColor = getLeaseStatus(a).color;
  const bColor = getLeaseStatus(b).color;
  return (priority[aColor] ?? 4) - (priority[bColor] ?? 4);
},
```

Add to the "Período Mínimo" column (around line 163):
```typescript
sorter: (a: Lease, b: Lease) => {
  const aStatus = getMinimumPeriodStatus(a);
  const bStatus = getMinimumPeriodStatus(b);
  const aVal = aStatus.completed ? -1 : aStatus.monthsRemaining;
  const bVal = bStatus.completed ? -1 : bStatus.monthsRemaining;
  return aVal - bVal;
},
```

Add to the "Contrato" column (around line 202):
```typescript
sorter: (a: Lease, b: Lease) => {
  const contractPriority = (l: Lease): number => {
    if (l.contract_signed) return 0;
    if (l.contract_generated) return 1;
    return 2;
  };
  return contractPriority(a) - contractPriority(b);
},
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/ui/accordion.tsx frontend/package.json frontend/package-lock.json frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx
git commit -m "feat(ui): install accordion component and add lease column sorters"
```

---

## Task 9: Frontend — Apartments Page with Accordions

**Files:**
- Modify: `frontend/app/(dashboard)/apartments/page.tsx` (major refactor)

- [ ] **Step 1: Refactor apartments page**

Rewrite `apartments/page.tsx` to:
1. Remove the building filter (redundant)
2. Remove the "Prédio" column
3. Group apartments by `building_id` using `useMemo`
4. Render one `AccordionItem` per building with filters + DataTable inside
5. State for filters: `Record<number, FilterState>` keyed by building_id
6. Each accordion closed by default (`type="multiple"`, no `defaultValue`)

Key changes:
- Import `Accordion, AccordionContent, AccordionItem, AccordionTrigger` from `@/components/ui/accordion`
- Group data: `const groupedApartments = useMemo(() => { ... }, [apartments])`
- Per-building filter state: `const [filtersByBuilding, setFiltersByBuilding] = useState<Record<number, ApartmentFilters>>({})`
- Remove `building_id` from the API call filters (fetch all apartments at once)
- Columns: remove the "Prédio" column, keep Apto↕, Valor↕, Taxa Limpeza, Status↕, Inquilinos, Móveis, Ações
- Add `sorter` to Status column: `(a, b) => Number(a.is_rented) - Number(b.is_rented)`
- Pass same `crud.bulkOps.rowSelection` to all DataTable instances

The full implementation is significant — the implementer should follow the existing page structure but wrap the table section in accordions. Refer to the spec Section 2 "Página de Apartamentos" for the exact layout.

- [ ] **Step 2: Verify build and visual test**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No errors. Manually verify the page at http://localhost:4000/apartments shows accordions.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/(dashboard)/apartments/page.tsx
git commit -m "feat(apartments): group listings by building with accordion layout"
```

---

## Task 10: Frontend — Leases Page with Accordions + Terminate Action

**Files:**
- Modify: `frontend/app/(dashboard)/leases/page.tsx` (major refactor)
- Delete: `frontend/app/(dashboard)/leases/_components/lease-filters.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/lease-table-columns.tsx` (column "Prédio/Apto" → "Apto" + add terminate button)
- Modify: `frontend/lib/api/hooks/use-leases.ts` (add useTerminateLease hook)

- [ ] **Step 1: Add useTerminateLease hook**

In `use-leases.ts`, add:

```typescript
export function useTerminateLease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (leaseId: number) => {
      const response = await api.post(`/leases/${leaseId}/terminate/`);
      return response.data as { detail: string };
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['leases'] });
      void queryClient.invalidateQueries({ queryKey: ['apartments'] });
    },
  });
}
```

- [ ] **Step 2: Update lease-table-columns.tsx**

Change "Prédio / Apto" column to "Apto" — show only `record.apartment?.number`.

Add "Encerrar" button to the actions column (after the delete button):
```typescript
// Add to LeaseActionHandlers interface:
onTerminate: (lease: Lease) => void;

// Add button in actions column render:
<Tooltip>
  <TooltipTrigger asChild>
    <Button
      variant="ghost"
      size="icon"
      onClick={() => handlers.onTerminate(record)}
    >
      <XCircle className="h-4 w-4" />
    </Button>
  </TooltipTrigger>
  <TooltipContent>Encerrar Contrato</TooltipContent>
</Tooltip>
```

Import `XCircle` from lucide-react.

- [ ] **Step 3: Refactor leases page with accordions**

Similar to apartments page:
1. Remove `LeaseFiltersCard` import and usage
2. Delete `lease-filters.tsx` file
3. Group leases by `apartment.building.id`
4. Render accordions with inline filters (Inquilino Responsável, Status)
5. Per-building filter state
6. Add terminate modal (AlertDialog) and handler

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/(dashboard)/leases/ frontend/lib/api/hooks/use-leases.ts
git commit -m "feat(leases): add accordion layout and terminate contract action"
```

---

## Task 11: Frontend — Tenants Page Columns + Actions

**Files:**
- Modify: `frontend/app/(dashboard)/tenants/page.tsx` (columns + filters + action buttons)
- Create: `frontend/app/(dashboard)/tenants/_components/tenant-lease-modal.tsx` (new modal)
- Modify: `frontend/lib/api/hooks/use-leases.ts` (add useTransferLease hook)
- Modify: `frontend/lib/hooks/use-export.ts` (update tenantExportColumns)

- [ ] **Step 1: Add useTransferLease hook**

In `use-leases.ts`, add:

```typescript
export function useTransferLease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ leaseId, ...payload }: { leaseId: number } & Record<string, unknown>) => {
      const response = await api.post(`/leases/${leaseId}/transfer/`, payload);
      return leaseSchema.parse(response.data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['leases'] });
      void queryClient.invalidateQueries({ queryKey: ['apartments'] });
    },
  });
}
```

- [ ] **Step 2: Update tenants page — remove columns and filters**

In `tenants/page.tsx`:
- Remove columns: email, profession, marital_status, dependents, furnitures
- Remove filters: has_dependents, has_furniture
- Remove related imports (Users, User icons for dependents/furnitures)

- [ ] **Step 3: Add lease-related columns**

In `tenants/page.tsx`:
- Import `useLeases` from hooks
- Fetch all non-deleted leases: `const { data: allLeases, isLoading: leasesLoading } = useLeases()`
- Build `leaseByTenantId` map with `useMemo`
- Add 4 new columns: Contrato Ativo, Contrato Assinado, Interfone, Contrato (Ver button)
- Add "Trocar de kitnet" / "Criar contrato" buttons to Ações column (conditional on lease existence)
- Use `useRouter` for "Ver" navigation

- [ ] **Step 4: Create TenantLeaseModal component**

Create `tenants/_components/tenant-lease-modal.tsx`:
- Props: `mode: 'create' | 'transfer'`, `tenant: Tenant`, `currentLease?: Lease`, `open`, `onClose`
- Reuse same form structure as `LeaseFormModal` (same fields, same validation)
- `responsible_tenant_id` shown as static text (not editable Select)
- Pre-fill based on mode:
  - `create`: start_date = today, defaults for other fields
  - `transfer`: copy from currentLease, apartment_id empty
- On submit:
  - `create`: call `useCreateLease` mutation
  - `transfer`: call `useTransferLease` mutation
- Use `useAvailableApartments()` for apartment select (only unrented)

- [ ] **Step 5: Update export columns**

In `lib/hooks/use-export.ts`, update `tenantExportColumns`:
- Remove: email, profession, marital_status, dependents count, furnitures count
- Keep: name, cpf_cnpj, phone, is_company

- [ ] **Step 6: Verify build**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/app/(dashboard)/tenants/ frontend/lib/api/hooks/use-leases.ts frontend/lib/hooks/use-export.ts
git commit -m "feat(tenants): restructure columns, add lease actions and tenant-lease modal"
```

---

## Task 12: Final Verification

- [ ] **Step 1: Run backend linting and type checks**

Run: `ruff check && ruff format --check && mypy core/`
Expected: No errors.

- [ ] **Step 2: Run frontend linting and type checks**

Run: `cd frontend && npm run lint && npm run type-check`
Expected: No errors.

- [ ] **Step 3: Run backend tests**

Run: `python -m pytest tests/ --timeout=30`
Expected: All pass.

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Clean build, no errors.

- [ ] **Step 5: Manual smoke test**

Start both servers and verify:
- [ ] Apartments page shows accordions grouped by building
- [ ] Apartment columns are sortable (Apto, Valor, Status)
- [ ] Leases page shows accordions grouped by building
- [ ] Lease columns are sortable (all 6 specified columns)
- [ ] "Encerrar Contrato" button opens confirmation modal and works
- [ ] Tenants page shows new columns (Contrato Ativo, Assinado, Interfone, Ver)
- [ ] "Criar contrato" opens modal with correct defaults
- [ ] "Trocar de kitnet" opens modal pre-filled from current lease
- [ ] Filters inside each accordion work independently
