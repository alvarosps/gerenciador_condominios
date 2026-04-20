# Comprehensive Review v3 — Sprint 1: Security & Critical Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all security gaps and critical infrastructure issues that block a safe production deployment. Every task in this sprint is a hard blocker — none are optional.

**Architecture:** 10 independent tasks. All tasks can be executed in parallel by separate agents. Each task is self-contained with no dependencies on other tasks in this sprint.

**Tech Stack:** Django 5.2, DRF, PostgreSQL 15, Redis, Next.js 14, React 18, TypeScript, Zod, pytest, python-decouple, isomorphic-dompurify

**Dependency Graph:**
```
Sprint 1 (Security & Critical — all independent):
  Task 1  (Backend env validation)        → independent
  Task 2  (Frontend env validation)       → independent
  Task 3  (Remove localhost fallbacks)    → depends on Task 2 (needs env.ts)
  Task 4  (Redis authentication)          → independent
  Task 5  (Frontend CSP headers)          → independent
  Task 6  (DOMPurify sanitization)        → independent
  Task 7  (X-Forwarded-For validation)    → independent
  Task 8  (Financial DB indexes)          → independent
  Task 9  (Database CheckConstraints)     → independent
  Task 10 (AuditMixin on missing models)  → independent
```

---

## Task 1: Backend Environment Variable Validation

**Context:** `condominios_manager/settings.py` uses `decouple.config()` for `SECRET_KEY`, `DB_PASSWORD`, and `REDIS_URL`, but there is no validation that these values are actually safe. If `SECRET_KEY` is missing or still set to a placeholder value like `"changeme"`, the app starts silently and Django's signing is compromised. If `DB_PASSWORD` is empty in production, the database connection may silently fall back to a passwordless auth method. Failing fast with a clear error at startup prevents obscure runtime failures.

**Files:**
- Modify: `condominios_manager/settings.py`
- Create: `tests/unit/test_settings_validation.py`

- [ ] **Step 1: Add validation block at the end of settings.py, after all config() calls**

In `condominios_manager/settings.py`, after the last `config()` call, add:

```python
from django.core.exceptions import ImproperlyConfigured

def _validate_settings() -> None:
    """Fail fast if critical settings are missing or insecure."""
    unsafe_secret_substrings = ("insecure", "changeme", "secret-key", "django-insecure")
    if not SECRET_KEY:
        raise ImproperlyConfigured("SECRET_KEY must be set.")
    if any(substr in SECRET_KEY.lower() for substr in unsafe_secret_substrings):
        raise ImproperlyConfigured(
            "SECRET_KEY contains an insecure placeholder value. "
            "Generate a real key with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )
    if not DEBUG:
        missing = [
            name
            for name, value in [
                ("DB_NAME", DATABASES["default"]["NAME"]),
                ("DB_USER", DATABASES["default"]["USER"]),
                ("DB_PASSWORD", DATABASES["default"]["PASSWORD"]),
            ]
            if not value
        ]
        if missing:
            raise ImproperlyConfigured(
                f"The following database settings must be set in production: {', '.join(missing)}"
            )
        allowed = ALLOWED_HOSTS
        if set(allowed) <= {"localhost", "127.0.0.1", ""}:
            raise ImproperlyConfigured(
                "ALLOWED_HOSTS must contain a real hostname in production, not only localhost."
            )


_validate_settings()
```

- [ ] **Step 2: Write tests for validation logic**

Create `tests/unit/test_settings_validation.py`:

```python
import pytest
from django.core.exceptions import ImproperlyConfigured


pytestmark = pytest.mark.unit


class TestSettingsValidation:
    """Tests for startup settings validation in _validate_settings()."""

    def test_unsafe_secret_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from condominios_manager import settings

        monkeypatch.setattr(settings, "SECRET_KEY", "django-insecure-abc123")
        with pytest.raises(ImproperlyConfigured, match="insecure placeholder"):
            settings._validate_settings()

    def test_empty_secret_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from condominios_manager import settings

        monkeypatch.setattr(settings, "SECRET_KEY", "")
        with pytest.raises(ImproperlyConfigured, match="SECRET_KEY must be set"):
            settings._validate_settings()

    def test_production_without_db_password_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from condominios_manager import settings

        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["myapp.example.com"])
        monkeypatch.setitem(settings.DATABASES["default"], "PASSWORD", "")
        with pytest.raises(ImproperlyConfigured, match="DB_PASSWORD"):
            settings._validate_settings()

    def test_production_localhost_only_allowed_hosts_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from condominios_manager import settings

        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["localhost"])
        with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
            settings._validate_settings()

    def test_valid_production_settings_pass(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from condominios_manager import settings

        monkeypatch.setattr(settings, "DEBUG", False)
        monkeypatch.setattr(settings, "SECRET_KEY", "a-real-50-char-secret-key-thats-not-a-placeholder!")
        monkeypatch.setattr(settings, "ALLOWED_HOSTS", ["myapp.example.com"])
        monkeypatch.setitem(settings.DATABASES["default"], "NAME", "condominios")
        monkeypatch.setitem(settings.DATABASES["default"], "USER", "dbuser")
        monkeypatch.setitem(settings.DATABASES["default"], "PASSWORD", "realpassword")
        # Should not raise
        settings._validate_settings()
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/unit/test_settings_validation.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 4: Run lint and type-check**

```bash
ruff check condominios_manager/settings.py && ruff format --check condominios_manager/settings.py
mypy condominios_manager/settings.py
```

---

## Task 2: Frontend Environment Variable Validation

**Context:** The Next.js frontend has no validation that `NEXT_PUBLIC_API_URL` is set at build time. Without it, 8 production files fall back to `http://localhost:8008/api`, which silently causes all API calls to fail in production. Creating a validated `env.ts` module that uses Zod makes this a hard build-time error instead of a silent runtime failure.

**Files:**
- Create: `frontend/lib/env.ts`
- Modify: `frontend/next.config.js` (import env validation so it runs at build time)

- [ ] **Step 1: Create `frontend/lib/env.ts`**

```typescript
import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z
    .string()
    .url("NEXT_PUBLIC_API_URL must be a valid URL (e.g. https://api.example.com/api)"),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
});
```

- [ ] **Step 2: Import env.ts in next.config.js so it runs at build time**

In `frontend/next.config.js`, add at the top (before any existing imports):

```javascript
// Validate env vars at build time — throws if NEXT_PUBLIC_API_URL is missing or invalid
import "./lib/env.ts";
```

Note: if `next.config.js` uses CommonJS (`require`/`module.exports`), use dynamic import pattern or convert to `next.config.mjs`. Check the existing file format first and match it.

- [ ] **Step 3: Run type-check to verify env.ts is valid**

```bash
cd frontend && npm run type-check
```

Expected: no type errors.

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint
```

---

## Task 3: Remove Hardcoded Localhost Fallbacks

**Context:** 8 production code files contain `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8008/api"` as a fallback. Now that Task 2 creates `frontend/lib/env.ts` which validates and exports the URL, the fallback is both unnecessary and dangerous — it masks missing configuration in production. Test files and MSW mock handlers are exempt.

**Files:**
- Modify: `frontend/lib/api/client.ts`
- Modify: `frontend/lib/api/hooks/use-auth.ts`
- Modify: `frontend/components/layouts/sidebar.tsx`
- Modify: `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx`
- Modify: `frontend/app/(dashboard)/tenants/_components/contract-view-modal.tsx`

**Depends on:** Task 2 (env.ts must exist first)

- [ ] **Step 1: Update `frontend/lib/api/client.ts`**

Add the import at the top of the file:
```typescript
import { env } from "@/lib/env";
```

Replace every occurrence of:
```typescript
process.env.NEXT_PUBLIC_API_URL || "http://localhost:8008/api"
```
and:
```typescript
process.env.NEXT_PUBLIC_API_URL || "http://localhost:8008"
```
with:
```typescript
env.NEXT_PUBLIC_API_URL
```

- [ ] **Step 2: Update `frontend/lib/api/hooks/use-auth.ts` line 121**

Same: import `env` from `@/lib/env` and replace the fallback expression with `env.NEXT_PUBLIC_API_URL`.

- [ ] **Step 3: Update `frontend/components/layouts/sidebar.tsx` line 123**

Same replacement.

- [ ] **Step 4: Update contract modals**

Apply the same replacement in:
- `frontend/app/(dashboard)/leases/_components/contract-generate-modal.tsx` (line 47)
- `frontend/app/(dashboard)/tenants/_components/contract-view-modal.tsx` (line 28)

- [ ] **Step 5: Verify no remaining fallbacks in production code**

The following grep should return zero results outside of test files and MSW handlers:
```bash
cd frontend && grep -r "localhost:8008" --include="*.ts" --include="*.tsx" \
  --exclude-dir=tests --exclude-dir=__tests__ --exclude="*.test.*" --exclude="handlers.ts"
```

Expected: no output.

- [ ] **Step 6: Run lint and type-check**

```bash
cd frontend && npm run lint && npm run type-check
```

---

## Task 4: Redis Authentication

**Context:** `docker-compose.prod.yml` starts Redis with `--requirepass ${REDIS_PASSWORD}`, but the Django settings connect to Redis using `REDIS_URL` which, in the current `.env.example`, does not include credentials. When deployed against a password-protected Redis, Django cache writes will fail with `NOAUTH Authentication required`, silently breaking all cached endpoints and causing performance degradation.

**Files:**
- Modify: `condominios_manager/settings.py`
- Modify: `.env.example` (if it exists)

- [ ] **Step 1: Add REDIS_URL format documentation and production validation to settings.py**

Find the `CACHES` configuration block in `condominios_manager/settings.py`. Add a comment above the REDIS_URL config call:

```python
# REDIS_URL format:
#   Without auth (development): redis://localhost:6379/1
#   With auth (production):     redis://:yourpassword@localhost:6379/1
# In production (DEBUG=False), the URL must include credentials.
REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/1")
```

- [ ] **Step 2: Add Redis URL validation in `_validate_settings()`**

Inside the `if not DEBUG:` block added in Task 1, add:

```python
        import re
        redis_url = config("REDIS_URL", default="")
        # redis://:password@host:port/db — the `:password@` part is required in production
        if redis_url and not re.search(r"redis://:[^@]+@", redis_url):
            raise ImproperlyConfigured(
                "REDIS_URL must include credentials in production. "
                "Format: redis://:yourpassword@host:port/db"
            )
```

- [ ] **Step 3: Update `.env.example` with correct format**

In `.env.example`, find the `REDIS_URL` line and update it to:

```
# Development (no auth):
REDIS_URL=redis://localhost:6379/1

# Production (with auth — must match --requirepass in docker-compose.prod.yml):
# REDIS_URL=redis://:your-redis-password@redis:6379/1
```

- [ ] **Step 4: Run lint and type-check**

```bash
ruff check condominios_manager/settings.py && ruff format --check condominios_manager/settings.py
mypy condominios_manager/settings.py
```

---

## Task 5: Frontend CSP Headers

**Context:** The Next.js application has no `Content-Security-Policy` or other security headers configured at the application layer. The nginx reverse proxy adds some headers, but the app itself provides no defense-in-depth. Without CSP, any XSS vulnerability has no mitigation. Without `X-Frame-Options: DENY`, clickjacking is possible. These headers must be set at the Next.js layer so they are present regardless of how the app is deployed (direct Node.js, Docker without nginx, etc.).

**Files:**
- Modify: `frontend/next.config.js`

- [ ] **Step 1: Read the existing `frontend/next.config.js`**

Read the file to understand its current structure (CommonJS vs ESM, existing exports, etc.) before modifying.

- [ ] **Step 2: Add security headers to `next.config.js`**

The CSP `connect-src` must include the API URL. Since `NEXT_PUBLIC_API_URL` is a build-time env var, extract just the origin. Add before the config object:

```javascript
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
// Extract origin only (e.g. "https://api.example.com") for CSP connect-src
const apiOrigin = apiUrl ? new URL(apiUrl).origin : "";

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      `connect-src 'self'${apiOrigin ? ` ${apiOrigin}` : ""}`,
      "font-src 'self'",
      "object-src 'none'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
    ].join("; "),
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    key: "X-Frame-Options",
    value: "DENY",
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];
```

Then add to the Next.js config object:

```javascript
async headers() {
  return [
    {
      source: "/(.*)",
      headers: securityHeaders,
    },
  ];
},
```

- [ ] **Step 3: Run build to verify headers config is valid**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint
```

---

## Task 6: DOMPurify Sanitization

**Context:** Three contract editor extension components render HTML from backend-stored templates without sanitization. While the content originates from admin-created templates, a compromised admin account could inject malicious HTML that executes in every user's browser when viewing a contract. Wrapping the HTML in `DOMPurify.sanitize()` before passing it to the renderer adds defense-in-depth with minimal performance cost.

**Files:**
- Install: `isomorphic-dompurify` (works in SSR + client)
- Create: `frontend/lib/utils/sanitize.ts`
- Modify: `frontend/components/contract-editor/extensions/template-table.tsx`
- Modify: `frontend/components/contract-editor/extensions/template-list.tsx`
- Modify: `frontend/components/contract-editor/extensions/template-signature.tsx`

- [ ] **Step 1: Install isomorphic-dompurify**

```bash
cd frontend && npm install isomorphic-dompurify && npm install --save-dev @types/dompurify
```

- [ ] **Step 2: Create `frontend/lib/utils/sanitize.ts`**

```typescript
import DOMPurify from "isomorphic-dompurify";

/**
 * Sanitizes HTML to prevent XSS. Safe for both SSR and client rendering.
 * Strips scripts, event handlers, and other dangerous constructs.
 */
export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "iframe", "object", "embed"],
    FORBID_ATTR: ["onerror", "onload", "onclick", "onmouseover"],
  });
}
```

- [ ] **Step 3: Read the 3 extension files**

Read each of the following files to understand their current structure:
- `frontend/components/contract-editor/extensions/template-table.tsx`
- `frontend/components/contract-editor/extensions/template-list.tsx`
- `frontend/components/contract-editor/extensions/template-signature.tsx`

- [ ] **Step 4: Update all 3 extension files**

In each file:
1. Add the import: `import { sanitizeHtml } from "@/lib/utils/sanitize";`
2. Find the `__html:` property inside the innerHTML prop (around line 51 in table/list, line 49 in signature)
3. Wrap the HTML value: change `__html: someHtmlVariable` to `__html: sanitizeHtml(someHtmlVariable)`

- [ ] **Step 5: Run lint and type-check**

```bash
cd frontend && npm run lint && npm run type-check
```

Expected: no errors.

---

## Task 7: X-Forwarded-For Validation

**Context:** `core/middleware/logging_middleware.py` extracts the client IP by taking the first entry in the `X-Forwarded-For` header. This header can be set by any client, allowing IP spoofing. An attacker can set `X-Forwarded-For: 1.2.3.4` to make their requests appear to originate from any IP. The correct approach is to trust only the Nth-from-right IP in the header, where N equals the number of trusted proxy layers in front of the app.

**Files:**
- Modify: `core/middleware/logging_middleware.py`
- Modify: `condominios_manager/settings.py` (add `NUM_PROXIES` setting)
- Modify: `condominios_manager/settings_production.py` (if it exists — verify first)

- [ ] **Step 1: Add `NUM_PROXIES` to settings.py**

```python
# Number of trusted reverse proxy layers in front of this app.
# Set to 1 if behind a single nginx/load balancer, 0 for direct connections.
# Used by logging middleware to extract the real client IP from X-Forwarded-For.
NUM_PROXIES: int = config("NUM_PROXIES", default=0, cast=int)
```

- [ ] **Step 2: Verify settings_production.py exists and set NUM_PROXIES there**

Check if `condominios_manager/settings_production.py` exists. If it does, add:
```python
NUM_PROXIES = 1  # One nginx reverse proxy in front of gunicorn
```

- [ ] **Step 3: Read the current IP extraction logic**

Read `core/middleware/logging_middleware.py` and locate the X-Forwarded-For handling (around line 115).

- [ ] **Step 4: Replace the IP extraction logic**

Replace the existing IP extraction with a new private function:

```python
from django.conf import settings as django_settings


def _get_client_ip(request: HttpRequest) -> str:
    """
    Extract the real client IP address.

    When behind a trusted proxy, use X-Forwarded-For by taking the
    Nth-from-right IP where N == NUM_PROXIES. This prevents IP spoofing
    because client-controlled headers are on the left; trusted proxy IPs
    are appended on the right.

    Falls back to REMOTE_ADDR when NUM_PROXIES is 0 (direct connection).
    """
    num_proxies: int = getattr(django_settings, "NUM_PROXIES", 0)
    if num_proxies == 0:
        return request.META.get("REMOTE_ADDR", "unknown")

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded_for:
        return request.META.get("REMOTE_ADDR", "unknown")

    ips = [ip.strip() for ip in forwarded_for.split(",")]
    # The rightmost num_proxies entries are added by trusted proxies.
    # The first untrusted (real client) IP is just to the left of those.
    index = max(len(ips) - num_proxies - 1, 0)
    return ips[index]
```

Replace the old call site with `_get_client_ip(request)`.

- [ ] **Step 5: Run lint and type-check**

```bash
ruff check core/middleware/logging_middleware.py && ruff format --check core/middleware/logging_middleware.py
mypy core/middleware/logging_middleware.py
```

- [ ] **Step 6: Run middleware-related tests**

```bash
python -m pytest tests/unit/ -v -k "middleware or logging" --no-header -q
```

---

## Task 8: Financial Database Indexes

**Context:** Multiple financial model date fields are used as filter and ordering targets in dashboard queries and cash flow projections, but lack `db_index=True`. On tables with thousands of rows, sequential scans on these fields degrade query performance significantly. PostgreSQL's query planner cannot use an index it doesn't have.

**Files:**
- Modify: `core/models.py`
- Create: new migration via `python manage.py makemigrations core`

- [ ] **Step 1: Read the relevant model definitions**

Read `core/models.py` and locate these models: `Income`, `EmployeePayment`, `MonthSnapshot`, `PersonIncome`, `PaymentProof`.

- [ ] **Step 2: Add db_index=True to the target fields**

For each field listed below, add `db_index=True` if not already present:

| Model | Field | Reason |
|---|---|---|
| `Income` | `income_date` | Used in date-range filters |
| `EmployeePayment` | `reference_month` | Used in monthly grouping |
| `MonthSnapshot` | `reference_month` | Used in timeline queries |
| `PersonIncome` | `start_date` | Used in effective-date range filters |
| `PersonIncome` | `end_date` | Used in effective-date range filters |
| `PaymentProof` | `reference_month` | Used in monthly filters |

Example for `Income`:
```python
income_date = models.DateField(db_index=True)
```

Note: `PaymentProof.lease` is a FK — Django automatically creates an index for FK fields, so no change is needed there.

- [ ] **Step 3: Generate migration**

```bash
python manage.py makemigrations core --name="financial_date_indexes"
```

Review the generated migration to confirm it only adds indexes (no `AlterField` that changes data type or nullability).

- [ ] **Step 4: Run tests to verify no model import errors**

```bash
python -m pytest tests/unit/ -v --co -q 2>&1 | head -20
```

Expected: collection succeeds with no import errors.

- [ ] **Step 5: Run lint and type-check**

```bash
ruff check core/models.py && ruff format --check core/models.py
mypy core/models.py
```

---

## Task 9: Database CheckConstraints

**Context:** Several financial models are missing database-level constraints that prevent logically invalid data from being persisted. `Expense` already has `amount > 0` as a reference — `Income` does not. `MonthSnapshot` monetary fields have no non-negativity constraint. `PersonPaymentSchedule.due_day` has no range constraint, allowing values like `99` which would cause runtime errors in any date calculation.

**Files:**
- Modify: `core/models.py`
- Create: new migration via `python manage.py makemigrations core`
- Create: `tests/unit/test_financial_constraints.py`

- [ ] **Step 1: Read the model definitions**

Read `core/models.py` and locate `Income`, `MonthSnapshot`, and `PersonPaymentSchedule`. Also check the existing `Expense` constraint as the reference pattern for how constraints are declared in this codebase.

- [ ] **Step 2: Add constraint to `Income`**

Inside the `Income` model's `Meta` class, add:

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(amount__gt=0),
            name="income_amount_positive",
        ),
    ]
```

- [ ] **Step 3: Add constraints to `MonthSnapshot`**

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(total_income__gte=0),
            name="monthsnapshot_total_income_non_negative",
        ),
        models.CheckConstraint(
            check=models.Q(total_expense__gte=0),
            name="monthsnapshot_total_expense_non_negative",
        ),
        models.CheckConstraint(
            check=models.Q(total_rent__gte=0),
            name="monthsnapshot_total_rent_non_negative",
        ),
    ]
```

Note: `balance` can be legitimately negative (expenses exceed income), so no constraint is added for it.

- [ ] **Step 4: Add constraint to `PersonPaymentSchedule`**

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(due_day__gte=1) & models.Q(due_day__lte=31),
            name="personpaymentschedule_due_day_valid_range",
        ),
    ]
```

- [ ] **Step 5: Generate migration**

```bash
python manage.py makemigrations core --name="financial_check_constraints"
```

- [ ] **Step 6: Write tests verifying constraints reject invalid data**

Create `tests/unit/test_financial_constraints.py`:

```python
import pytest
from django.db import IntegrityError

from model_bakery import baker

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestIncomeConstraints:
    def test_income_amount_must_be_positive(self) -> None:
        with pytest.raises(IntegrityError, match="income_amount_positive"):
            baker.make("core.Income", amount=-1)

    def test_income_zero_amount_rejected(self) -> None:
        with pytest.raises(IntegrityError, match="income_amount_positive"):
            baker.make("core.Income", amount=0)

    def test_income_positive_amount_accepted(self) -> None:
        income = baker.make("core.Income", amount=100)
        assert income.amount == 100


class TestMonthSnapshotConstraints:
    def test_negative_total_income_rejected(self) -> None:
        with pytest.raises(IntegrityError):
            baker.make("core.MonthSnapshot", total_income=-1)

    def test_negative_total_expense_rejected(self) -> None:
        with pytest.raises(IntegrityError):
            baker.make("core.MonthSnapshot", total_expense=-1)

    def test_negative_balance_accepted(self) -> None:
        # balance can be negative (expenses exceed income in a month)
        snapshot = baker.make("core.MonthSnapshot", balance=-500)
        assert snapshot.balance == -500


class TestPersonPaymentScheduleConstraints:
    def test_due_day_zero_rejected(self) -> None:
        with pytest.raises(IntegrityError, match="personpaymentschedule_due_day_valid_range"):
            baker.make("core.PersonPaymentSchedule", due_day=0)

    def test_due_day_32_rejected(self) -> None:
        with pytest.raises(IntegrityError, match="personpaymentschedule_due_day_valid_range"):
            baker.make("core.PersonPaymentSchedule", due_day=32)

    def test_due_day_1_accepted(self) -> None:
        schedule = baker.make("core.PersonPaymentSchedule", due_day=1)
        assert schedule.due_day == 1

    def test_due_day_31_accepted(self) -> None:
        schedule = baker.make("core.PersonPaymentSchedule", due_day=31)
        assert schedule.due_day == 31
```

- [ ] **Step 7: Run tests**

```bash
python -m pytest tests/unit/test_financial_constraints.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Run lint and type-check**

```bash
ruff check core/models.py && ruff format --check core/models.py
mypy core/models.py
```

---

## Task 10: AuditMixin on Missing Models

**Context:** 4 models lack `AuditMixin` (`created_at`, `updated_at`, `created_by`, `updated_by`) and `SoftDeleteMixin` (`is_deleted`, `deleted_at`, `deleted_by`): `FinancialSettings`, `IPCAIndex`, `WhatsAppVerification`, `OAuthExchangeCode`. All other domain models have these mixins. The inconsistency means changes to these 4 models are not auditable and deletions are permanent. Adding these mixins is safe — the migration adds nullable fields that default gracefully for existing rows.

**Files:**
- Modify: `core/models.py`
- Create: new migration via `python manage.py makemigrations core`

- [ ] **Step 1: Read the 4 model definitions**

Read `core/models.py` and locate `FinancialSettings`, `IPCAIndex`, `WhatsAppVerification`, `OAuthExchangeCode`. Note their current base classes. Also read the `AuditMixin` and `SoftDeleteMixin` definitions to understand what fields they add and whether there are any manager conflicts to watch for.

- [ ] **Step 2: Add mixins to all 4 models**

For each model, add `AuditMixin` and `SoftDeleteMixin` to its parent class list, before any other parents (mixins must come before `models.Model` in MRO):

```python
class FinancialSettings(AuditMixin, SoftDeleteMixin, models.Model):
    ...

class IPCAIndex(AuditMixin, SoftDeleteMixin, models.Model):
    ...

class WhatsAppVerification(AuditMixin, SoftDeleteMixin, models.Model):
    ...

class OAuthExchangeCode(AuditMixin, SoftDeleteMixin, models.Model):
    ...
```

- [ ] **Step 3: Verify SoftDeleteMixin manager compatibility**

`SoftDeleteMixin` provides a custom manager that filters out `is_deleted=True` records. Verify that none of the 4 models have custom `objects` managers that would conflict. If they do, the custom manager must inherit from or compose with the SoftDelete manager — follow the same pattern used by other models in the file.

- [ ] **Step 4: Generate migration**

```bash
python manage.py makemigrations core --name="audit_mixin_missing_models"
```

Review the generated migration. It should only add fields (`created_at`, `updated_at`, `created_by`, `updated_by`, `is_deleted`, `deleted_at`, `deleted_by`) — all nullable or with defaults. No data loss should occur.

- [ ] **Step 5: Verify migration applies cleanly**

```bash
python manage.py migrate --check
```

If `--check` reports pending migrations, run `python manage.py migrate` on the development database to apply.

- [ ] **Step 6: Run all unit tests to verify no regressions**

```bash
python -m pytest tests/unit/ -v -q --no-header
```

Expected: all tests pass.

- [ ] **Step 7: Run lint and type-check**

```bash
ruff check core/models.py && ruff format --check core/models.py
mypy core/models.py
```

---

## Verification Checklist

After all 10 tasks are complete, run the following checks to confirm the sprint is fully implemented.

**Backend:**
- [ ] `ruff check && ruff format --check` — zero errors
- [ ] `mypy core/` — zero errors
- [ ] `python -m pytest tests/unit/test_settings_validation.py -v` — all pass
- [ ] `python -m pytest tests/unit/test_financial_constraints.py -v` — all pass
- [ ] `python manage.py migrate --check` — no pending migrations
- [ ] `python manage.py check --deploy` — no critical warnings

**Frontend:**
- [ ] `cd frontend && npm run lint` — zero errors
- [ ] `cd frontend && npm run type-check` — zero errors
- [ ] `cd frontend && npm run build` — build succeeds (validates env.ts at build time)
- [ ] The following grep returns zero results:
  ```bash
  grep -r "localhost:8008" frontend/lib frontend/components frontend/app \
    --include="*.ts" --include="*.tsx" --exclude="*.test.*" --exclude="handlers.ts"
  ```

**Manual verification:**
- [ ] Start backend with `SECRET_KEY=django-insecure-test` — verify `ImproperlyConfigured` is raised immediately with a clear message
- [ ] Run `cd frontend && npm run build` without `NEXT_PUBLIC_API_URL` set — verify build fails with Zod validation error
- [ ] Review the 3 generated migrations (`financial_date_indexes`, `financial_check_constraints`, `audit_mixin_missing_models`) — confirm no destructive operations (no DROP, no column type changes)
