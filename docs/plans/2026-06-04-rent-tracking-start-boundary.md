# Rent Tracking-Start Boundary — Implementation Plan

**Date:** 2026-06-04
**Branch:** `fix/rent-tracking-start-boundary`
**Status:** approved (design), executing

## Problem

The dashboard "Pagamentos em Atraso" widget shows absurd values (e.g. "36649 dias de
atraso", "66724 dias", "Total em Multas R$ 404.123,36").

Root cause (confirmed in current `master`):
`DashboardService.get_late_payment_summary` (`core/services/dashboard_service.py:298-415`)
back-scans **every month from `lease.start_date` to the current month** and **accumulates**
`late_days`/`late_fee` across all of them. Since commit `0127c55` leases **auto-renew**
(`RentScheduleService.collectible_leases` has **no upper date bound**), every active lease is
collectible for every month since its `start_date`. A lease started years ago, with no
`RentPayment` rows for historical months, accumulates hundreds of months of "late" days.

There is **no notion of a tracking-start date** in the system — historical months simply
have no payment rows and are therefore treated as unpaid.

## Goal

- The system considers **all rent up to 2026-05-31 as settled** (out of tracking scope).
- The system only **marks/tracks rent from 2026-06-01 onward**, system-wide.
- Apply the change to **PROD (Supabase)** as well.

## Design (approved)

- **Boundary = a single nullable field** on the `FinancialSettings` singleton:
  `rent_tracking_start_date`. It is the single source of truth for the boundary.
- **No-op when `None`** → identical to today's behavior. Activates only once set to
  `2026-06-01`. Fully reversible (set back to `None`).
- **System-wide gate inside `RentScheduleService`** (the rent-collectibility SSOT), so the
  rent calendar, daily-control, cash-flow, month-stats, toggle-payment AND the late-payment
  widget all honor it through one chokepoint.
- **Response contract unchanged** → zero frontend change for the dashboard widget.
- **`late_days` semantics kept as the current sum** (deviation from the original design's
  "oldest unpaid month" idea): the boundary already removes the absurdity, and keeping the
  sum maintains full compatibility with the just-merged SSOT tests. "Oldest" is an optional
  cosmetic follow-up, not part of this plan.

### Compatibility notes (current code)

- Existing late-payment tests do **not** create a `FinancialSettings` row →
  `FinancialSettings.objects.first()` is `None` → boundary helper returns `None` → gate is a
  no-op → all existing tests stay green.
- Tests use **freezegun** (`@freeze_time`) and the `freeze_time` fixture (conftest).
- `RentScheduleService` methods are **not** `@cache_result`-decorated; the only relevant
  service cache is `dashboard-late-payment*`. Financial caches use the
  `daily-control* / cash-flow* / financial-dashboard*` patterns (`core/signals.py`).
- `FinancialSettingsSerializer` is a `ModelSerializer` (`core/serializers.py:1180`).

---

## Task 1 — `FinancialSettings.rent_tracking_start_date` field + migration + serializer

**Files:** `core/models.py`, `core/migrations/`, `core/serializers.py`, tests.

1. Add to `FinancialSettings` (`core/models.py:1413`):
   ```python
   rent_tracking_start_date = models.DateField(
       null=True,
       blank=True,
       help_text=(
           "Sistema rastreia aluguéis (cobrança/atraso) a partir desta data; "
           "meses anteriores são considerados quitados."
       ),
   )
   ```
2. `python manage.py makemigrations core` → a new migration with a single `AddField`
   (nullable). Confirm it is purely additive (no data loss, no alter on existing columns).
3. Ensure the field is exposed by `FinancialSettingsSerializer` (`core/serializers.py:1180`).
   If `Meta.fields` is an explicit list, add `rent_tracking_start_date`; if `"__all__"`, it is
   already included — confirm via a test.

**Acceptance:**
- Migration applies cleanly; `migrate` + `migrate` (re-run) idempotent.
- A `FinancialSettings` instance accepts and round-trips `rent_tracking_start_date`; default
  is `None`.
- The serializer includes `rent_tracking_start_date` (read + write) — assert in a test.

**Tests:** model field default `None`; serializer round-trips the date.

**Gates:** `ruff check && ruff format --check && mypy core/ && pyright` and the relevant
pytest files.

---

## Task 2 — Boundary gate in `RentScheduleService` (the SSOT)

**Files:** `core/services/rent_schedule_service.py`, tests
(`tests/unit/test_financial/test_rent_schedule_service.py`).

1. Import `FinancialSettings` from `core.models`.
2. Add two static helpers (single source of truth for the boundary):
   ```python
   @staticmethod
   def rent_tracking_start_month() -> date | None:
       """First day of the month from which rent is tracked, or None if unbounded.

       Driven by the FinancialSettings singleton; None means no boundary (every month
       is tracked, i.e. legacy behavior).
       """
       financial_settings = FinancialSettings.objects.first()
       if financial_settings is None or financial_settings.rent_tracking_start_date is None:
           return None
       return financial_settings.rent_tracking_start_date.replace(day=1)

   @staticmethod
   def is_month_tracked(year: int, month: int) -> bool:
       """Whether the system tracks rent for (year, month). Months before the
       configured tracking-start are considered settled and are never collectible."""
       start = RentScheduleService.rent_tracking_start_month()
       return start is None or date(year, month, 1) >= start
   ```
3. Gate `collectible_leases(reference_month, ...)` — at the very top, after computing
   `year, month`:
   ```python
   if not RentScheduleService.is_month_tracked(year, month):
       return Lease.objects.none()
   ```
4. Gate `is_collectible_for_month(lease, year, month)` — fold the boundary into the predicate:
   ```python
   started = lease.start_date <= date(year, month, days_in_month)
   return (
       started
       and RentScheduleService.is_month_tracked(year, month)
       and not RentScheduleService.is_prepaid_for_month(lease, year, month)
   )
   ```

**Acceptance:**
- With a `FinancialSettings.rent_tracking_start_date = 2026-06-01`:
  - `collectible_leases(date(2026, 5, 1))` → empty; `collectible_leases(date(2026, 6, 1))` →
    unchanged (same set as before for that month).
  - `is_collectible_for_month(lease, 2026, 5)` → `False`; `(lease, 2026, 6)` → `True`
    (for an otherwise-collectible lease).
- With **no** `FinancialSettings` row, or `rent_tracking_start_date = None`: behavior is
  **identical to before** for all months (no gating).
- `displayable_leases`, `get_month_schedule`, `get_month_stats`, `toggle_payment`,
  `daily_control_service` all inherit the gate via `collectible_leases` (no extra change).

**Tests:** boundary set → pre-boundary month empty / non-collectible; boundary month
unchanged; `None` boundary → unchanged. Use `freeze_time` + a `FinancialSettings` row.

**Gates:** full backend gate set + `tests/unit/test_financial/test_rent_schedule_service.py`,
`tests/unit/test_financial/test_daily_control_service.py`,
`tests/integration/test_rent_calendar_api.py`.

---

## Task 3 — Bound the dashboard back-scan to tracked months

**Files:** `core/services/dashboard_service.py`, tests
(`tests/unit/test_dashboard_service.py`).

Correctness is already guaranteed by Task 2's `is_collectible_for_month` gate (pre-boundary
months are skipped in the `while` loop). This task removes the wasteful pre-boundary
iterations (otherwise a 2015 lease loops ~130 times, each calling
`is_collectible_for_month` → a `FinancialSettings` query per iteration).

In `get_late_payment_summary` (`core/services/dashboard_service.py:341-377`):
1. Fetch the boundary once, before the per-lease loop:
   ```python
   tracking_start = RentScheduleService.rent_tracking_start_month()
   ```
2. Start the scan at the later of lease-start and boundary:
   ```python
   start_month = lease.start_date.replace(day=1)
   if tracking_start is not None and tracking_start > start_month:
       start_month = tracking_start
   curr_month_iter = start_month
   ```
   (Keep the existing `is_collectible_for_month` check inside the loop as defense in depth.)

**Acceptance (with `freeze_time`):**
- Lease `start_date = 2024-01-01`, no `RentPayment` rows, `rent_tracking_start_date =
  2026-06-01`, frozen at `2026-06-15`, `due_day = 10`: the lease appears once with
  `late_months == 1` and a **small** `late_days` (≈5), **not** thousands. `total_late_fees`
  is a small, sane value.
- Same lease with **no boundary**: behavior unchanged from current `master` (still
  accumulates — documents the contrast; assert it is large / many months).
- Frozen at `2026-05-15` with `rent_tracking_start_date = 2026-06-01`: summary is **empty**
  (nothing tracked yet — current month is before the boundary, so
  `collectible_leases(month_start)` is empty).
- All existing `TestGetLatePaymentSummary` / `TestLatePaymentSummarySSOT` tests still pass
  (they set no boundary).

**Gates:** full backend gate set + `tests/unit/test_dashboard_service.py`,
`tests/integration/test_core_views.py`.

---

## Task 4 — Cache invalidation on `FinancialSettings` change

**Files:** `core/signals.py`, tests.

Changing `rent_tracking_start_date` alters collectibility everywhere, so the dependent
caches must be invalidated.

1. Add `FinancialSettings` to the `core.models` import block in `core/signals.py`.
2. Add a `post_save` receiver for `FinancialSettings` that invalidates the affected caches:
   ```python
   @receiver(post_save, sender=FinancialSettings)
   def invalidate_financial_settings_cache_on_save(
       sender: type[FinancialSettings], instance: FinancialSettings, **kwargs: Any
   ) -> None:
       logger.info("FinancialSettings changed, invalidating dashboard + financial caches")
       _invalidate_financial_caches("FinancialSettings", instance.pk)
       CacheManager.invalidate_pattern("dashboard-late-payment*")
   ```
   (`_invalidate_financial_caches` already covers `daily-control* / cash-flow* /
   financial-dashboard*`.)

**Acceptance:** saving a `FinancialSettings` triggers invalidation of the
`dashboard-late-payment*` and financial cache patterns. Keep the test light (exercise the
receiver via a real save; assert it runs without error and clears a seeded key).

**Gates:** full backend gate set + the signals/cache test module.

---

## Task 5 (controller, not a subagent) — Set the boundary locally + verify

After Tasks 1-4 merge on the branch:
1. Set `FinancialSettings.rent_tracking_start_date = 2026-06-01` locally (Django shell /
   admin / API).
2. Confirm `DashboardService.get_late_payment_summary()` returns sane numbers locally
   (only June+ scanned).

## Task 6 (controller + user) — PROD rollout via Supabase MCP

Per CLAUDE.md data-safety rule, **backup first**.
1. `python scripts/backup_db.py` against PROD `DATABASE_URL` (pg_dump).
2. Deploy code; run `python manage.py migrate` against PROD (additive column).
   - Fallback if direct Django migrate to PROD is not viable: apply
     `ALTER TABLE core_financialsettings ADD COLUMN rent_tracking_start_date date NULL`
     via Supabase MCP, then `manage.py migrate --fake` to sync Django's state.
3. Via Supabase MCP: `UPDATE core_financialsettings SET rent_tracking_start_date = '2026-06-01'
   WHERE id = 1;` (or get-or-create if the singleton row is missing). Run read-only
   verification queries.
4. Invalidate caches (handled by the Task 4 signal on the row save, or clear manually).
5. Verify the dashboard shows sane numbers in PROD.

## Out of scope / follow-ups
- Frontend FinancialSettings form field for `rent_tracking_start_date` (only if a settings
  form already exists; otherwise admin/API is enough).
- Changing `late_days` to "days since oldest unpaid month" (optional cosmetic).
