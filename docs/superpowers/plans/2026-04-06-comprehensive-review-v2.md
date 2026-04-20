# Comprehensive Review — Implementation Plan v2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all verified issues from the comprehensive application audit — security gaps, data integrity risks, architecture violations, frontend quality, and testing gaps.

**Architecture:** 30 tasks organized in 8 sprints. Each sprint is independently deployable. Backend fixes first (security, integrity), then frontend quality, cleanup, auth hardening, tenant portal, full test coverage. TDD where applicable.

**Tech Stack:** Django 5.2, DRF, PostgreSQL 15, Redis, Next.js 14, React 18, TypeScript, TanStack Query, Zustand, Zod, Vitest, MSW, pytest

**Key corrections from audit verification:**
- FinancialReadOnly on ExpenseViewSet.rebuild is NOT a security issue — POST requires `is_staff` (verified in `core/permissions.py:118-121`)
- Dashboard methods (financial_summary, lease_metrics, etc.) are NOT orphan — frontend hooks use them (verified via grep)
- `change_due_date` and `adjust_rent` are NOT orphan — called from `use-leases.ts:206` and `use-rent-adjustments.ts:22`

**Dependency Graph:**
```
Sprint 1 (Security & Critical):
  Task 1 (Auth endpoints) → independent
  Task 2 (Security headers) → independent
  Task 3 (Rebuild refactor) → independent
  Task 4 (Axios timeout) → independent
  Task 5 (DB connection pooling) → independent

Sprint 2 (Data Integrity & Performance):
  Task 6 (full_clean) → independent
  Task 7 (Signal race condition) → independent
  Task 8 (DB indexes) → independent
  Task 9 (Date helpers DRY) → independent

Sprint 5 (Auth Hardening — HttpOnly Cookies):
  Task 17 (Backend cookie auth) → depends on Task 1
  Task 18 (Frontend cookie migration) → depends on Task 17
  Task 19 (OAuth cookie flow) → depends on Task 17

Sprint 6 (Tenant Portal UI):
  Task 20 (Tenant auth + layout) → depends on Sprint 5
  Task 21 (Tenant dashboard + profile) → depends on Task 20
  Task 22 (Tenant payments + PIX) → depends on Task 20
  Task 23 (Tenant proof upload + notifications) → depends on Task 20

Sprint 7 (Full Component Tests):
  Task 24 (P0 form modal tests) → depends on Sprint 3
  Task 25 (P1 dashboard widget tests) → depends on Sprint 3
  Task 26 (P2 layout + auth-gated tests) → depends on Sprint 5
  Task 27 (P3 utility component tests) → independent

Sprint 8 (Full Baker Migration):
  Task 28 (Baker factories + conftest) → independent
  Task 29 (Migrate unit tests) → depends on Task 28
  Task 30 (Migrate integration + e2e tests) → depends on Task 28

Sprint 3 (Frontend Quality):
  Task 10 (Expense form refactor) → independent
  Task 11 (Leases page refactor) → independent
  Task 12 (Schema standardization) → independent
  Task 13 (Component tests) → depends on Tasks 10-12

Sprint 4 (Cleanup & Integration):
  Task 14 (Dead code removal) → independent
  Task 15 (Dashboard widget wrapper) → independent
  Task 16 (Test factory migration) → independent
```

---

## Sprint 1: Security & Critical Fixes

### Task 1: Create Register and Logout Backend Endpoints

**Context:** Frontend calls `POST /auth/register/` (`frontend/lib/api/hooks/use-auth.ts:76`) and `POST /auth/logout/` (`use-auth.ts:92`) but these endpoints don't exist in the backend. The backend only has `/auth/token/`, `/auth/token/refresh/`, `/auth/token/blacklist/`, `/auth/me/`. Frontend MSW mocks define the expected contracts (`frontend/tests/mocks/handlers.ts:421-477`).

**Files:**
- Create: `core/viewsets/auth_views_registration.py`
- Modify: `condominios_manager/urls.py:50-58` (add routes)
- Test: `tests/integration/test_auth_registration.py`

- [ ] **Step 1: Write failing test for user registration**

Create `tests/integration/test_auth_registration.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


class TestUserRegistration:
    """Tests for POST /api/auth/register/."""

    def test_register_creates_user_and_returns_tokens(self, api_client: APIClient) -> None:
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post("/api/auth/register/", payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == "newuser@example.com"
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_register_rejects_mismatched_passwords(self, api_client: APIClient) -> None:
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password2": "DifferentPass456!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post("/api/auth/register/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_rejects_duplicate_email(
        self, api_client: APIClient, admin_user: User
    ) -> None:
        payload = {
            "email": admin_user.email,
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post("/api/auth/register/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_rejects_weak_password(self, api_client: APIClient) -> None:
        payload = {
            "email": "newuser@example.com",
            "password": "123",
            "password2": "123",
            "first_name": "Test",
            "last_name": "User",
        }
        response = api_client.post("/api/auth/register/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/integration/test_auth_registration.py -v
```

Expected: FAIL — 404 on `/api/auth/register/`

- [ ] **Step 3: Write failing test for user logout**

Add to `tests/integration/test_auth_registration.py`:

```python
class TestUserLogout:
    """Tests for POST /api/auth/logout/."""

    def test_logout_blacklists_refresh_token(
        self, authenticated_api_client: APIClient
    ) -> None:
        # First get a refresh token by logging in
        login_response = APIClient().post(
            "/api/auth/token/",
            {"email": "admin@example.com", "password": "testpass123"},
            format="json",
        )
        refresh_token = login_response.data["refresh"]

        response = authenticated_api_client.post(
            "/api/auth/logout/",
            {"refresh": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify the refresh token is blacklisted
        refresh_response = APIClient().post(
            "/api/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_requires_authentication(self, api_client: APIClient) -> None:
        response = api_client.post("/api/auth/logout/", {}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 4: Run test to verify it fails**

```bash
python -m pytest tests/integration/test_auth_registration.py::TestUserLogout -v
```

Expected: FAIL — 404 on `/api/auth/logout/`

- [ ] **Step 5: Implement registration and logout views**

Create `core/viewsets/auth_views_registration.py`:

```python
"""User registration and logout views."""

from django.contrib.auth import get_user_model
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

MIN_PASSWORD_LENGTH = 8


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=MIN_PASSWORD_LENGTH, write_only=True)
    password2 = serializers.CharField(min_length=MIN_PASSWORD_LENGTH, write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            msg = "Um usuário com este email já existe."
            raise serializers.ValidationError(msg)
        return value.lower()

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password2"]:
            msg = "As senhas não conferem."
            raise serializers.ValidationError({"password2": msg})
        return attrs

    def create(self, validated_data: dict) -> User:
        validated_data.pop("password2")
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def register_user(request: Request) -> Response:
    """POST /api/auth/register/ — create a new user and return JWT tokens."""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_user(request: Request) -> Response:
    """POST /api/auth/logout/ — blacklist the refresh token."""
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()
    except Exception:  # noqa: BLE001 — token may already be blacklisted or invalid
        pass  # Logout should succeed regardless

    return Response(status=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Add URL routes**

In `condominios_manager/urls.py`, after line 54 (`path("api/auth/me/", ...)`), add:

```python
    path("api/auth/register/", register_user, name="register"),
    path("api/auth/logout/", logout_user, name="logout"),
```

Add imports at the top of the file:

```python
from core.viewsets.auth_views_registration import logout_user, register_user
```

- [ ] **Step 7: Run tests**

```bash
python -m pytest tests/integration/test_auth_registration.py -v
```

Expected: ALL PASS

- [ ] **Step 8: Update frontend logout hook to send refresh token**

In `frontend/lib/api/hooks/use-auth.ts`, the logout mutationFn (line 92) currently sends no body. Update to send the refresh token:

```typescript
    mutationFn: async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await apiClient.post('/auth/logout/', { refresh: refreshToken });
      }
    },
```

- [ ] **Step 9: Run frontend auth tests**

```bash
cd frontend && npm run test:unit -- --run lib/api/hooks/__tests__/use-auth.test.tsx
```

- [ ] **Step 10: Commit**

```bash
git add core/viewsets/auth_views_registration.py tests/integration/test_auth_registration.py condominios_manager/urls.py frontend/lib/api/hooks/use-auth.ts
git commit -m "feat(auth): add register and logout endpoints

Backend was missing /auth/register/ and /auth/logout/ endpoints that
frontend was already calling. Adds registration with password validation
and logout with refresh token blacklisting."
```

---

### Task 2: Add Security Headers for Production

**Context:** `condominios_manager/settings.py` has basic cookie security (`CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`) behind `if not DEBUG` (line 326-330), but is missing HSTS, XSS protection, content type sniffing protection, and frame options headers.

**Files:**
- Modify: `condominios_manager/settings.py:326-330`

- [ ] **Step 1: Add security headers**

In `condominios_manager/settings.py`, replace the existing production security block (lines 326-330):

```python
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
```

With:

```python
if not DEBUG:
    # Cookie security
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True

    # HSTS — tell browsers to always use HTTPS (1 year)
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Redirect HTTP → HTTPS
    SECURE_SSL_REDIRECT = True

    # Prevent MIME type sniffing
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Clickjacking protection
    X_FRAME_OPTIONS = "DENY"
```

- [ ] **Step 2: Verify settings load without errors**

```bash
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condominios_manager.settings'); django.setup(); print('Settings OK')"
```

- [ ] **Step 3: Commit**

```bash
git add condominios_manager/settings.py
git commit -m "fix(security): add HSTS, content type, and clickjacking headers for production"
```

---

### Task 3: Extract ExpenseViewSet.rebuild to Service with Transaction

**Context:** `core/viewsets/financial_views.py:260-307` has the `rebuild` action with business logic directly in the viewset: field updates via `setattr`, hard-delete of installments, and `bulk_create` — all without `transaction.atomic`. This should be in a service.

**Files:**
- Create: `core/services/expense_service.py`
- Modify: `core/viewsets/financial_views.py:260-307`
- Test: `tests/unit/test_expense_service.py`

- [ ] **Step 1: Write failing test for ExpenseService.rebuild_installments**

Create `tests/unit/test_expense_service.py`:

```python
import pytest
from decimal import Decimal
from model_bakery import baker

from core.services.expense_service import ExpenseService

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestExpenseServiceRebuild:
    """Tests for ExpenseService.rebuild_installments."""

    def test_rebuild_replaces_all_installments(self, admin_user) -> None:
        expense = baker.make(
            "core.Expense",
            description="Test expense",
            total_amount=Decimal("300.00"),
            is_installment=True,
            total_installments=3,
            created_by=admin_user,
            updated_by=admin_user,
        )
        # Create initial installments
        for i in range(1, 4):
            baker.make(
                "core.ExpenseInstallment",
                expense=expense,
                installment_number=i,
                total_installments=3,
                amount=Decimal("100.00"),
                due_date="2026-05-01",
                created_by=admin_user,
                updated_by=admin_user,
            )

        new_installments = [
            {
                "installment_number": 1,
                "total_installments": 2,
                "amount": Decimal("150.00"),
                "due_date": "2026-06-01",
                "is_paid": False,
            },
            {
                "installment_number": 2,
                "total_installments": 2,
                "amount": Decimal("150.00"),
                "due_date": "2026-07-01",
                "is_paid": False,
            },
        ]

        field_updates = {
            "description": "Updated expense",
            "total_amount": Decimal("300.00"),
            "total_installments": 2,
        }

        result = ExpenseService.rebuild_installments(
            expense=expense,
            field_updates=field_updates,
            installments_data=new_installments,
            user=admin_user,
        )

        assert result.description == "Updated expense"
        assert result.total_installments == 2
        assert result.installments.count() == 2

    def test_rebuild_is_atomic_on_failure(self, admin_user) -> None:
        expense = baker.make(
            "core.Expense",
            description="Original",
            total_amount=Decimal("100.00"),
            is_installment=True,
            total_installments=1,
            created_by=admin_user,
            updated_by=admin_user,
        )
        baker.make(
            "core.ExpenseInstallment",
            expense=expense,
            installment_number=1,
            total_installments=1,
            amount=Decimal("100.00"),
            due_date="2026-05-01",
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Invalid installment data — missing required field
        bad_installments = [{"installment_number": 1}]

        with pytest.raises(Exception):
            ExpenseService.rebuild_installments(
                expense=expense,
                field_updates={"description": "Should not persist"},
                installments_data=bad_installments,
                user=admin_user,
            )

        expense.refresh_from_db()
        assert expense.description == "Original"
        assert expense.installments.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/unit/test_expense_service.py -v
```

Expected: FAIL — `ImportError: cannot import name 'ExpenseService'`

- [ ] **Step 3: Implement ExpenseService**

Create `core/services/expense_service.py`:

```python
"""Service for expense business logic."""

from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import transaction

from core.models import Expense, ExpenseInstallment


REBUILD_ALLOWED_FIELDS = frozenset({
    "description",
    "total_amount",
    "category_id",
    "notes",
    "is_installment",
    "total_installments",
    "is_offset",
})


class ExpenseService:
    """Stateless service for expense operations."""

    @staticmethod
    @transaction.atomic
    def rebuild_installments(
        *,
        expense: Expense,
        field_updates: dict[str, Any],
        installments_data: list[dict[str, Any]],
        user: AbstractUser,
    ) -> Expense:
        """Replace expense fields and all installments atomically.

        Hard-deletes existing installments (bypasses soft delete) and creates
        new ones from the provided data. All changes are wrapped in a
        transaction — if any step fails, everything is rolled back.
        """
        # Update allowed expense fields
        for field, value in field_updates.items():
            if field not in REBUILD_ALLOWED_FIELDS:
                continue
            if field == "category_id":
                expense.category_id = value
            else:
                setattr(expense, field, value)
        expense.save()

        # Hard-delete existing installments
        ExpenseInstallment.all_objects.filter(expense=expense).delete()

        # Create new installments
        to_create = [
            ExpenseInstallment(
                expense=expense,
                installment_number=inst["installment_number"],
                total_installments=inst["total_installments"],
                amount=inst["amount"],
                due_date=inst["due_date"],
                is_paid=inst.get("is_paid", False),
                paid_date=inst.get("paid_date"),
                created_by=user,
                updated_by=user,
            )
            for inst in installments_data
        ]
        if to_create:
            ExpenseInstallment.objects.bulk_create(to_create)

        return expense
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/unit/test_expense_service.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Refactor viewset to use service**

In `core/viewsets/financial_views.py`, replace the `rebuild` method (lines 260-307):

```python
    @action(detail=True, methods=["post"])
    def rebuild(self, request: Request, pk: str | None = None) -> Response:
        """Overwrite expense fields and rebuild all installments from scratch."""
        expense = self.get_object()

        field_updates = {
            field: request.data[field]
            for field in (
                "description",
                "total_amount",
                "category_id",
                "notes",
                "is_installment",
                "total_installments",
                "is_offset",
            )
            if field in request.data
        }

        ExpenseService.rebuild_installments(
            expense=expense,
            field_updates=field_updates,
            installments_data=request.data.get("installments", []),
            user=cast(User, request.user),
        )

        expense = self.get_queryset().get(pk=expense.pk)
        serializer = self.get_serializer(expense)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

Add import at top of `financial_views.py`:

```python
from core.services.expense_service import ExpenseService
```

- [ ] **Step 6: Run existing expense tests**

```bash
python -m pytest tests/integration/test_expense_api.py -v
```

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add core/services/expense_service.py core/viewsets/financial_views.py tests/unit/test_expense_service.py
git commit -m "refactor(expenses): extract rebuild logic to ExpenseService with transaction.atomic

Moves business logic from ExpenseViewSet.rebuild to a dedicated service
with proper atomicity. If installment creation fails, the expense field
updates are rolled back."
```

---

### Task 4: Add Axios Request Timeout

**Context:** `frontend/lib/api/client.ts:5-10` creates an Axios instance without a timeout configuration. Requests can hang indefinitely if the backend is unresponsive.

**Files:**
- Modify: `frontend/lib/api/client.ts:5-10`
- Test: `frontend/lib/api/hooks/__tests__/use-auth.test.tsx` (existing tests should still pass)

- [ ] **Step 1: Add timeout to Axios instance**

In `frontend/lib/api/client.ts`, find the `axios.create` call (lines 5-10):

```typescript
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  headers: {
    'Content-Type': 'application/json',
  },
});
```

Replace with:

```typescript
const REQUEST_TIMEOUT_MS = 30_000;

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  timeout: REQUEST_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});
```

- [ ] **Step 2: Run frontend tests**

```bash
cd frontend && npm run test:unit -- --run lib/api/hooks/__tests__/use-auth.test.tsx
```

Expected: ALL PASS (timeout doesn't affect MSW-mocked requests)

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api/client.ts
git commit -m "fix(frontend): add 30s request timeout to Axios client

Prevents requests from hanging indefinitely when backend is unresponsive."
```

---

### Task 5: Add Database Connection Pooling

**Context:** `condominios_manager/settings.py:112-121` has no `CONN_MAX_AGE` setting. Django creates and destroys a database connection per request by default, which is inefficient for production.

**Files:**
- Modify: `condominios_manager/settings.py:112-121`

- [ ] **Step 1: Add CONN_MAX_AGE**

In `condominios_manager/settings.py`, in the `DATABASES` dict (lines 112-121), add `CONN_MAX_AGE`:

```python
DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="condominio"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=600, cast=int),
    }
}
```

- [ ] **Step 2: Verify settings load**

```bash
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condominios_manager.settings'); django.setup(); from django.conf import settings; print(f'CONN_MAX_AGE={settings.DATABASES[\"default\"][\"CONN_MAX_AGE\"]}')"
```

Expected: `CONN_MAX_AGE=600`

- [ ] **Step 3: Commit**

```bash
git add condominios_manager/settings.py
git commit -m "perf(db): add CONN_MAX_AGE=600 for connection pooling

Reuses database connections for up to 10 minutes instead of creating a
new connection per request."
```

---

## Sprint 2: Data Integrity & Performance

### Task 6: Add full_clean() to Serializer Create/Update Methods

**Context:** Serializers in `core/serializers.py` have custom `create()` and `update()` methods (ApartmentSerializer:195-212, TenantSerializer:295-320, LeaseSerializer:457-500+) that bypass model-level cross-field validation because they never call `full_clean()`. This means constraints defined in model `clean()` methods can be bypassed via API.

**Files:**
- Modify: `core/serializers.py` (ApartmentSerializer, TenantSerializer, LeaseSerializer create/update)
- Test: `tests/integration/test_serializer_validation.py`

- [ ] **Step 1: Write failing test for model-level validation via API**

Create `tests/integration/test_serializer_validation.py`:

```python
import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


class TestSerializerValidation:
    """Ensure model.full_clean() is called from serializer create/update."""

    def test_apartment_create_calls_model_validation(
        self, authenticated_api_client: APIClient, sample_building_data: dict
    ) -> None:
        """Model validation should reject invalid data even if serializer fields pass."""
        from core.models import Building

        building = Building.objects.create(**sample_building_data)

        # Create apartment — this should work
        response = authenticated_api_client.post(
            "/api/apartments/",
            {
                "building_id": building.pk,
                "number": "101",
                "rental_value": "1000.00",
                "rental_value_double": "1500.00",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_lease_create_validates_dates(
        self,
        authenticated_api_client: APIClient,
        building_with_apartment: dict,
    ) -> None:
        """Lease model clean() validates start_date < end_date if both present."""
        apartment = building_with_apartment["apartment"]
        tenant_data = {
            "full_name": "Test Tenant",
            "cpf_cnpj": "52998224725",
            "phone": "11999999999",
            "email": "test@example.com",
            "nationality": "Brasileiro",
            "marital_status": "Solteiro(a)",
            "occupation": "Developer",
        }
        from core.models import Tenant

        tenant = Tenant.objects.create(**tenant_data)

        response = authenticated_api_client.post(
            "/api/leases/",
            {
                "apartment_id": apartment.pk,
                "responsible_tenant_id": tenant.pk,
                "start_date": "2026-12-01",
                "rental_value": "1000.00",
                "due_day": 5,
            },
            format="json",
        )
        # Should succeed — valid data
        assert response.status_code == status.HTTP_201_CREATED
```

- [ ] **Step 2: Run test to verify baseline passes**

```bash
python -m pytest tests/integration/test_serializer_validation.py -v
```

- [ ] **Step 3: Add full_clean() to ApartmentSerializer.create and update**

In `core/serializers.py`, find `ApartmentSerializer.create()` (line ~195):

```python
def create(self, validated_data: dict[str, Any]) -> Apartment:
    """Create apartment with furniture relationships."""
    furniture_ids = validated_data.pop("furniture_ids", [])
    apartment = Apartment.objects.create(**validated_data)
    if furniture_ids:
        apartment.furnitures.set(furniture_ids)
    return apartment
```

Replace with:

```python
def create(self, validated_data: dict[str, Any]) -> Apartment:
    """Create apartment with furniture relationships and model validation."""
    furniture_ids = validated_data.pop("furniture_ids", [])
    apartment = Apartment(**validated_data)
    apartment.full_clean()
    apartment.save()
    if furniture_ids:
        apartment.furnitures.set(furniture_ids)
    return apartment
```

Find `ApartmentSerializer.update()` (line ~203):

Add `instance.full_clean()` before the final `instance.save()`:

```python
def update(self, instance: Apartment, validated_data: dict[str, Any]) -> Apartment:
    """Update apartment with furniture relationships and model validation."""
    furniture_ids = validated_data.pop("furniture_ids", None)
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.full_clean()
    instance.save()
    if furniture_ids is not None:
        instance.furnitures.set(furniture_ids)
    return instance
```

- [ ] **Step 4: Add full_clean() to TenantSerializer.create and update**

Apply the same pattern — add `instance.full_clean()` before `instance.save()` in both methods. Note: TenantSerializer creates the object, THEN sets M2M relations. Use the same pattern as Apartment.

- [ ] **Step 5: Add full_clean() to LeaseSerializer.create and update**

Same pattern. Find create/update in LeaseSerializer and add `instance.full_clean()` before save. Be careful with M2M tenant relationships — full_clean goes before save, M2M after.

- [ ] **Step 6: Run all serializer-related tests**

```bash
python -m pytest tests/integration/test_serializer_validation.py tests/integration/test_lease_crud.py tests/unit/test_serializers.py -v
```

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add core/serializers.py tests/integration/test_serializer_validation.py
git commit -m "fix(serializers): add full_clean() to create/update methods

Ensures model-level cross-field validation runs when creating/updating
entities via API. Previously only serializer-level validation ran."
```

---

### Task 7: Fix Race Condition in Lease Signal

**Context:** `core/signals.py:170-182` has `sync_apartment_is_rented` that checks `Lease.objects.filter(apartment_id=...).exists()` and then updates `Apartment.is_rented`. Between the check and the update, another lease could be created/deleted, causing `is_rented` to be incorrect.

**Files:**
- Modify: `core/signals.py:170-182`
- Test: `tests/unit/test_signals.py` (add race condition test)

- [ ] **Step 1: Write test for signal correctness**

Add to existing test file or create `tests/unit/test_lease_signal.py`:

```python
import pytest
from model_bakery import baker

from core.models import Apartment, Lease

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestSyncApartmentIsRented:
    """Tests for the sync_apartment_is_rented signal."""

    def test_apartment_marked_rented_when_lease_created(self, admin_user) -> None:
        building = baker.make("core.Building", street_number=999)
        apartment = baker.make(
            "core.Apartment", building=building, number="101", is_rented=False
        )

        baker.make(
            "core.Lease",
            apartment=apartment,
            rental_value=1000,
            due_day=5,
            start_date="2026-01-01",
            created_by=admin_user,
            updated_by=admin_user,
        )

        apartment.refresh_from_db()
        assert apartment.is_rented is True

    def test_apartment_marked_not_rented_when_last_lease_deleted(
        self, admin_user
    ) -> None:
        building = baker.make("core.Building", street_number=998)
        apartment = baker.make(
            "core.Apartment", building=building, number="101", is_rented=True
        )

        lease = baker.make(
            "core.Lease",
            apartment=apartment,
            rental_value=1000,
            due_day=5,
            start_date="2026-01-01",
            created_by=admin_user,
            updated_by=admin_user,
        )
        lease.delete()  # soft delete

        apartment.refresh_from_db()
        assert apartment.is_rented is False

    def test_apartment_stays_rented_when_one_of_two_leases_deleted(
        self, admin_user
    ) -> None:
        building = baker.make("core.Building", street_number=997)
        apartment = baker.make(
            "core.Apartment", building=building, number="101"
        )

        lease1 = baker.make(
            "core.Lease",
            apartment=apartment,
            rental_value=1000,
            due_day=5,
            start_date="2026-01-01",
            created_by=admin_user,
            updated_by=admin_user,
        )
        baker.make(
            "core.Lease",
            apartment=apartment,
            rental_value=1200,
            due_day=10,
            start_date="2026-06-01",
            created_by=admin_user,
            updated_by=admin_user,
        )

        lease1.delete()  # soft delete first lease

        apartment.refresh_from_db()
        assert apartment.is_rented is True
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/unit/test_lease_signal.py -v
```

- [ ] **Step 3: Fix signal to use atomic update**

In `core/signals.py`, replace the `sync_apartment_is_rented` signal (lines 170-175):

```python
@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender, instance, **kwargs):
    """Sync apartment.is_rented based on whether any active lease exists."""
    has_active_lease = Lease.objects.filter(apartment_id=instance.apartment_id).exists()
    Apartment.objects.filter(pk=instance.apartment_id).update(is_rented=has_active_lease)
```

Replace with:

```python
@receiver(post_save, sender=Lease)
def sync_apartment_is_rented(sender, instance, **kwargs):
    """Sync apartment.is_rented atomically using a subquery."""
    from django.db.models import Exists, OuterRef

    Apartment.objects.filter(pk=instance.apartment_id).update(
        is_rented=Exists(
            Lease.objects.filter(apartment_id=OuterRef("pk"))
        )
    )
```

Apply the same fix to `sync_apartment_is_rented_on_delete` (lines 177-182).

This performs the check and update in a single SQL UPDATE with a subquery, eliminating the race window.

- [ ] **Step 4: Run signal tests**

```bash
python -m pytest tests/unit/test_lease_signal.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/signals.py tests/unit/test_lease_signal.py
git commit -m "fix(signals): eliminate race condition in sync_apartment_is_rented

Uses EXISTS subquery in UPDATE instead of separate check-then-update,
making the operation atomic at the SQL level."
```

---

### Task 8: Add Missing Database Indexes

**Context:** Financial dashboard and cash flow queries filter by `is_recurring`, `category + expense_date`, and `person + is_paid + expense_date` but these columns lack indexes. As the expense table grows, these queries degrade.

**Files:**
- Modify: `core/models.py` (Expense Meta.indexes)
- Create migration

- [ ] **Step 1: Add composite indexes to Expense model**

In `core/models.py`, find the Expense `Meta` class (around line 1076). The `indexes` list should already exist. Add these indexes:

```python
class Meta:
    ordering = ["-expense_date", "-created_at"]
    indexes = [
        # ... existing indexes ...
        models.Index(
            fields=["is_recurring", "expense_date"],
            name="idx_expense_recurring_date",
        ),
        models.Index(
            fields=["category", "expense_date"],
            name="idx_expense_category_date",
        ),
        models.Index(
            fields=["person", "is_paid", "expense_date"],
            name="idx_expense_person_paid_date",
        ),
    ]
```

- [ ] **Step 2: Create migration**

```bash
python manage.py makemigrations core -n add_expense_indexes
```

- [ ] **Step 3: Apply migration**

```bash
python manage.py migrate
```

- [ ] **Step 4: Verify indexes exist**

```bash
python manage.py dbshell -c "\di idx_expense_*"
```

- [ ] **Step 5: Commit**

```bash
git add core/models.py core/migrations/
git commit -m "perf(db): add composite indexes for financial dashboard queries

Adds indexes on Expense for (is_recurring, expense_date),
(category, expense_date), and (person, is_paid, expense_date)
to speed up dashboard and cash flow queries."
```

---

### Task 9: Consolidate Duplicated Date Helpers

**Context:** `core/services/cash_flow_service.py:39` has `_next_month_start(year, month) -> date` and `core/services/fee_calculator.py:102` has `_next_month(year, month) -> tuple[int, int]`. Both compute "the next month" with different return types. Consolidate into `DateCalculatorService`.

**Files:**
- Modify: `core/services/date_calculator.py` (add helper)
- Modify: `core/services/cash_flow_service.py` (use helper)
- Modify: `core/services/fee_calculator.py` (use helper)

- [ ] **Step 1: Add next_month_start to DateCalculatorService**

In `core/services/date_calculator.py`, add a static method to the existing `DateCalculatorService` class:

```python
    @staticmethod
    def next_month_start(year: int, month: int) -> date:
        """Return the first day of the next month.

        Args:
            year: Current year
            month: Current month (1-12)

        Returns:
            First day of the following month
        """
        if month == 12:
            return date(year + 1, 1, 1)
        return date(year, month + 1, 1)
```

- [ ] **Step 2: Replace _next_month_start in cash_flow_service.py**

In `core/services/cash_flow_service.py`, remove the local `_next_month_start` function (line ~39) and replace all usages with:

```python
from core.services.date_calculator import DateCalculatorService

# Replace: _next_month_start(year, month)
# With:    DateCalculatorService.next_month_start(year, month)
```

- [ ] **Step 3: Replace _next_month in fee_calculator.py**

In `core/services/fee_calculator.py`, remove the local `_next_month` function (line ~102) and replace usages. Since `_next_month` returns `(year, month)` tuple, update callers:

```python
from core.services.date_calculator import DateCalculatorService

# Where previously: year, month = _next_month(year, month)
# Now use:          next_start = DateCalculatorService.next_month_start(year, month)
#                   year, month = next_start.year, next_start.month
```

- [ ] **Step 4: Run affected tests**

```bash
python -m pytest tests/unit/test_cash_flow_service.py tests/unit/test_fee_calculator.py tests/unit/test_date_calculator.py -v
```

Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/date_calculator.py core/services/cash_flow_service.py core/services/fee_calculator.py
git commit -m "refactor(services): consolidate _next_month helpers into DateCalculatorService

Removes duplicate date arithmetic from cash_flow_service and
fee_calculator. Both now use DateCalculatorService.next_month_start()."
```

---

## Sprint 3: Frontend Quality

### Task 10: Refactor Expense Form Modal

**Context:** `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx` is 775 lines with schema definition, 7 type-category constants (lines 86-99), conditional field rendering for 6 expense types, and all form logic in a single component. Extract constants and type-specific field logic.

**Files:**
- Create: `frontend/lib/utils/expense-type-config.ts`
- Modify: `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx`
- Modify: `frontend/lib/schemas/expense.schema.ts`

- [ ] **Step 1: Extract expense type constants**

Create `frontend/lib/utils/expense-type-config.ts`:

```typescript
/**
 * Expense type field visibility configuration.
 *
 * Centralizes which fields are required/optional/visible per expense type.
 * Used by both the expense form modal and the expense schema validation.
 */

export const EXPENSE_TYPES = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
  'water_bill',
  'electricity_bill',
  'property_tax',
  'fixed_expense',
  'one_time_expense',
] as const;

export type ExpenseType = (typeof EXPENSE_TYPES)[number];

export const PERSON_REQUIRED_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const PERSON_OPTIONAL_TYPES: readonly ExpenseType[] = [
  'one_time_expense',
  'fixed_expense',
];

export const BUILDING_REQUIRED_TYPES: readonly ExpenseType[] = [
  'water_bill',
  'electricity_bill',
  'property_tax',
];

export const BUILDING_OPTIONAL_TYPES: readonly ExpenseType[] = [
  'fixed_expense',
  'one_time_expense',
];

export const OFFSET_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const INSTALLMENT_TYPES: readonly ExpenseType[] = [
  'card_purchase',
  'bank_loan',
  'personal_loan',
];

export const DEBT_INSTALLMENT_TYPES: readonly ExpenseType[] = [
  'water_bill',
  'electricity_bill',
  'property_tax',
];

/** Check if a field section is visible for the given expense type. */
export function isPersonFieldVisible(type: string): boolean {
  return (
    PERSON_REQUIRED_TYPES.includes(type as ExpenseType) ||
    PERSON_OPTIONAL_TYPES.includes(type as ExpenseType)
  );
}

export function isBuildingFieldVisible(type: string): boolean {
  return (
    BUILDING_REQUIRED_TYPES.includes(type as ExpenseType) ||
    BUILDING_OPTIONAL_TYPES.includes(type as ExpenseType)
  );
}

export function isInstallmentFieldVisible(type: string): boolean {
  return INSTALLMENT_TYPES.includes(type as ExpenseType);
}

export function isOffsetFieldVisible(type: string): boolean {
  return OFFSET_TYPES.includes(type as ExpenseType);
}
```

- [ ] **Step 2: Update expense schema to use centralized constants**

In `frontend/lib/schemas/expense.schema.ts`, replace the inline type string with the enum:

```typescript
import { EXPENSE_TYPES } from '@/lib/utils/expense-type-config';

// Replace: expense_type: z.string().min(1, 'Tipo é obrigatório'),
// With:
expense_type: z.enum(EXPENSE_TYPES, {
  errorMap: () => ({ message: 'Tipo é obrigatório' }),
}),
```

Also import the type constants for `validateExpenseRules`:

```typescript
import {
  PERSON_REQUIRED_TYPES,
  BUILDING_REQUIRED_TYPES,
  type ExpenseType,
} from '@/lib/utils/expense-type-config';
```

Replace hardcoded strings in `validateExpenseRules` with these imported arrays.

- [ ] **Step 3: Update expense-form-modal to use centralized constants**

In `frontend/app/(dashboard)/financial/expenses/_components/expense-form-modal.tsx`:

1. Remove the 7 local constant arrays (lines 86-99)
2. Import from the new utility file:

```typescript
import {
  isPersonFieldVisible,
  isBuildingFieldVisible,
  isInstallmentFieldVisible,
  isOffsetFieldVisible,
  PERSON_REQUIRED_TYPES,
  BUILDING_REQUIRED_TYPES,
} from '@/lib/utils/expense-type-config';
```

3. Replace inline checks like `PERSON_REQUIRED_TYPES.includes(type)` with `isPersonFieldVisible(type)` where appropriate.

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm run test:unit -- --run
```

- [ ] **Step 5: Run type check and lint**

```bash
cd frontend && npm run type-check && npm run lint
```

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/utils/expense-type-config.ts frontend/lib/schemas/expense.schema.ts frontend/app/\(dashboard\)/financial/expenses/_components/expense-form-modal.tsx
git commit -m "refactor(frontend): extract expense type config to centralized module

Moves 7 duplicate constant arrays from expense-form-modal.tsx to a
shared expense-type-config.ts. Adds z.enum() for expense_type in
schema for compile-time safety and exhaustiveness checking."
```

---

### Task 11: Refactor Leases Page — Extract Hooks

**Context:** `frontend/app/(dashboard)/leases/page.tsx` is 531 lines managing 7 modal state variables (lines 110-116), filter state per building (line 119), and action handlers. Extract into custom hooks.

**Files:**
- Create: `frontend/app/(dashboard)/leases/_hooks/use-lease-modals.ts`
- Modify: `frontend/app/(dashboard)/leases/page.tsx`

- [ ] **Step 1: Create use-lease-modals hook**

Create `frontend/app/(dashboard)/leases/_hooks/use-lease-modals.ts`:

```typescript
'use client';

import { useState, useCallback } from 'react';
import type { Lease } from '@/lib/schemas/lease.schema';

type ModalType = 'contract' | 'lateFee' | 'dueDate' | 'terminate' | 'adjustRent' | 'history';

interface LeaseModalsState {
  /** Which modal is currently open (null = none) */
  activeModal: ModalType | null;
  /** The lease associated with the active modal action */
  actionLease: Lease | null;
  /** Lease ID for history sheet (separate because it's a sheet, not dialog) */
  historyLeaseId: number | null;
}

interface LeaseModalsActions {
  openModal: (type: ModalType, lease: Lease) => void;
  openHistory: (leaseId: number) => void;
  closeModal: () => void;
  closeHistory: () => void;
  isOpen: (type: ModalType) => boolean;
}

export function useLeaseModals(): LeaseModalsState & LeaseModalsActions {
  const [activeModal, setActiveModal] = useState<ModalType | null>(null);
  const [actionLease, setActionLease] = useState<Lease | null>(null);
  const [historyLeaseId, setHistoryLeaseId] = useState<number | null>(null);

  const openModal = useCallback((type: ModalType, lease: Lease) => {
    setActiveModal(type);
    setActionLease(lease);
  }, []);

  const openHistory = useCallback((leaseId: number) => {
    setHistoryLeaseId(leaseId);
  }, []);

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setActionLease(null);
  }, []);

  const closeHistory = useCallback(() => {
    setHistoryLeaseId(null);
  }, []);

  const isOpen = useCallback(
    (type: ModalType) => activeModal === type,
    [activeModal],
  );

  return {
    activeModal,
    actionLease,
    historyLeaseId,
    openModal,
    openHistory,
    closeModal,
    closeHistory,
    isOpen,
  };
}
```

- [ ] **Step 2: Refactor leases page to use the hook**

In `frontend/app/(dashboard)/leases/page.tsx`, replace the 7 modal state variables (lines 110-116):

```typescript
// Remove these:
const [isContractModalOpen, setIsContractModalOpen] = useState(false);
const [isLateFeeModalOpen, setIsLateFeeModalOpen] = useState(false);
const [isDueDateModalOpen, setIsDueDateModalOpen] = useState(false);
const [isTerminateModalOpen, setIsTerminateModalOpen] = useState(false);
const [actionLease, setActionLease] = useState<Lease | null>(null);
const [adjustRentLease, setAdjustRentLease] = useState<Lease | null>(null);
const [historyLeaseId, setHistoryLeaseId] = useState<number | null>(null);

// Add:
const modals = useLeaseModals();
```

Update all modal references:
- `isContractModalOpen` → `modals.isOpen('contract')`
- `setIsContractModalOpen(true); setActionLease(lease)` → `modals.openModal('contract', lease)`
- `setIsContractModalOpen(false)` → `modals.closeModal()`
- Same pattern for lateFee, dueDate, terminate, adjustRent
- `historyLeaseId` → `modals.historyLeaseId`
- `setHistoryLeaseId(id)` → `modals.openHistory(id)`
- `setHistoryLeaseId(null)` → `modals.closeHistory()`

Add import:

```typescript
import { useLeaseModals } from './_hooks/use-lease-modals';
```

- [ ] **Step 3: Run type check**

```bash
cd frontend && npm run type-check
```

- [ ] **Step 4: Run lint**

```bash
cd frontend && npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(dashboard\)/leases/_hooks/use-lease-modals.ts frontend/app/\(dashboard\)/leases/page.tsx
git commit -m "refactor(leases): extract modal state to useLeaseModals hook

Replaces 7 individual useState calls with a single hook that manages
modal visibility via a discriminated type. Reduces leases page by ~40
lines and prevents multiple modals from being open simultaneously."
```

---

### Task 12: Standardize Schema Patterns

**Context:** Multiple schema files use inconsistent patterns: `nullable()`, `optional()`, or `nullable().optional()` without clear convention. Also `use-users.ts:5` uses a local `QUERY_KEY` instead of the centralized `queryKeys` object.

**Files:**
- Modify: `frontend/lib/api/hooks/use-users.ts:5` (query key)
- Modify: `frontend/lib/api/query-keys.ts` (add adminUsers key)

- [ ] **Step 1: Add adminUsers to centralized query keys**

In `frontend/lib/api/query-keys.ts`, add after the last entry in the `queryKeys` object:

```typescript
  adminUsers: {
    all: ['admin-users'] as const,
    list: () => [...queryKeys.adminUsers.all] as const,
  },
```

- [ ] **Step 2: Update use-users.ts to use centralized keys**

In `frontend/lib/api/hooks/use-users.ts`, remove the local constant (line 5):

```typescript
// Remove this line:
const QUERY_KEY = ['admin-users'] as const;
```

Replace all `QUERY_KEY` usages with `queryKeys.adminUsers.all`:

```typescript
import { queryKeys } from '@/lib/api/query-keys';

// In useAdminUsers:
queryKey: queryKeys.adminUsers.all,

// In mutations:
queryClient.invalidateQueries({ queryKey: queryKeys.adminUsers.all });
```

- [ ] **Step 3: Run tests and type check**

```bash
cd frontend && npm run test:unit -- --run lib/api/hooks/__tests__/use-users.test.tsx && npm run type-check
```

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api/query-keys.ts frontend/lib/api/hooks/use-users.ts
git commit -m "refactor(frontend): centralize adminUsers query key

Moves local QUERY_KEY constant in use-users.ts to the shared queryKeys
object for consistent cache invalidation patterns."
```

---

### Task 13: Add Critical Component Tests

**Context:** 52+ React components have zero unit tests. Focus on the most critical ones: error states, form behavior, and conditional rendering based on `isAdmin`.

**Files:**
- Create: `frontend/app/(dashboard)/_components/__tests__/financial-summary-widget.test.tsx`
- Create: `frontend/app/(dashboard)/financial/daily/__tests__/daily-page-admin.test.tsx`

- [ ] **Step 1: Write test for financial-summary-widget loading and error states**

Create `frontend/app/(dashboard)/_components/__tests__/financial-summary-widget.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '@/tests/mocks/server';
import { renderWithProviders } from '@/tests/test-utils';

// Dynamic import to match the component's usage pattern
import FinancialSummaryWidget from '../financial-summary-widget';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api';

describe('FinancialSummaryWidget', () => {
  it('shows loading state initially', () => {
    renderWithProviders(<FinancialSummaryWidget />);
    expect(screen.getByText(/carregando/i)).toBeInTheDocument();
  });

  it('renders financial data when loaded', async () => {
    renderWithProviders(<FinancialSummaryWidget />);

    // Wait for data to load (MSW handlers return mock data)
    await screen.findByText(/ocupação/i, {}, { timeout: 5000 });
  });

  it('shows error state when API fails', async () => {
    server.use(
      http.get(`${API_BASE}/dashboard/financial_summary/`, () =>
        HttpResponse.json({ detail: 'Server error' }, { status: 500 }),
      ),
    );

    renderWithProviders(<FinancialSummaryWidget />);

    await screen.findByText(/erro/i, {}, { timeout: 5000 });
  });
});
```

- [ ] **Step 2: Run the new component test**

```bash
cd frontend && npm run test:unit -- --run app/\(dashboard\)/_components/__tests__/financial-summary-widget.test.tsx
```

- [ ] **Step 3: Write test for admin-gated UI on daily page**

Create `frontend/app/(dashboard)/financial/daily/__tests__/daily-page-admin.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { useAuthStore } from '@/store/auth-store';

import DailyControlPage from '../page';

describe('DailyControlPage admin visibility', () => {
  beforeEach(() => {
    // Reset auth store between tests
    useAuthStore.setState({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  });

  it('hides add button for non-admin users', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'user@example.com',
        first_name: 'User',
        last_name: 'Test',
        is_staff: false,
      },
      isAuthenticated: true,
      token: 'fake-token',
      refreshToken: 'fake-refresh',
    });

    renderWithProviders(<DailyControlPage />);

    // Wait for page to render
    await screen.findByText(/controle/i, {}, { timeout: 5000 });

    // The "+" add button should not be visible for non-admin
    const addButtons = screen.queryAllByRole('button', { name: /adicionar|nova/i });
    expect(addButtons).toHaveLength(0);
  });

  it('shows add button for admin users', async () => {
    useAuthStore.setState({
      user: {
        id: 1,
        email: 'admin@example.com',
        first_name: 'Admin',
        last_name: 'Test',
        is_staff: true,
      },
      isAuthenticated: true,
      token: 'fake-token',
      refreshToken: 'fake-refresh',
    });

    renderWithProviders(<DailyControlPage />);

    // Wait for page to render with admin privileges
    await screen.findByText(/controle/i, {}, { timeout: 5000 });

    // Admin should see the add button
    // Note: exact selector depends on button text/aria-label in the actual component
  });
});
```

- [ ] **Step 4: Run the new tests**

```bash
cd frontend && npm run test:unit -- --run app/
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/
git commit -m "test(frontend): add component tests for financial widget and admin gating

Adds tests for loading, error, and data states in financial-summary-widget.
Adds tests verifying admin-only UI elements are hidden for regular users."
```

---

## Sprint 4: Cleanup & Integration

### Task 14: Remove Dead Frontend Code

**Context:** `frontend/lib/api/hooks/use-monthly-purchases.ts` defines a hook that is never imported by any component. This is dead code.

**Files:**
- Remove: `frontend/lib/api/hooks/use-monthly-purchases.ts` (if confirmed unused)
- Modify: `frontend/lib/api/query-keys.ts` (remove monthlyPurchases key if unused)

- [ ] **Step 1: Verify hook is unused**

```bash
cd frontend && grep -r "useMonthlyPurchases\|use-monthly-purchases" --include="*.ts" --include="*.tsx" lib/ app/ components/ | grep -v "__tests__" | grep -v "use-monthly-purchases.ts"
```

If zero results: confirmed dead code.

- [ ] **Step 2: Check if query key is used elsewhere**

```bash
cd frontend && grep -r "monthlyPurchases" --include="*.ts" --include="*.tsx" lib/ | grep -v "use-monthly-purchases.ts" | grep -v "query-keys.ts"
```

If zero results: the query key is also dead.

- [ ] **Step 3: Remove dead hook and query key (only if confirmed unused)**

Delete `frontend/lib/api/hooks/use-monthly-purchases.ts`.

In `frontend/lib/api/query-keys.ts`, remove the `monthlyPurchases` entry.

- [ ] **Step 4: Run type check to confirm no broken imports**

```bash
cd frontend && npm run type-check
```

- [ ] **Step 5: Commit**

```bash
git add -A frontend/lib/api/hooks/use-monthly-purchases.ts frontend/lib/api/query-keys.ts
git commit -m "chore(frontend): remove unused useMonthlyPurchases hook and query key"
```

---

### Task 15: Standardize Dashboard Widget Pattern

**Context:** Dashboard widgets in `frontend/app/(dashboard)/_components/` handle loading/error states inconsistently. `financial-summary-widget.tsx` uses `<Loading>` + `<Alert variant="destructive">`. Others may use inline text or different patterns. Create a wrapper component.

**Files:**
- Create: `frontend/app/(dashboard)/_components/dashboard-widget-wrapper.tsx`
- Modify: `frontend/app/(dashboard)/_components/financial-summary-widget.tsx` (use wrapper)

- [ ] **Step 1: Create DashboardWidgetWrapper component**

Create `frontend/app/(dashboard)/_components/dashboard-widget-wrapper.tsx`:

```typescript
'use client';

import type { ReactNode } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertTriangle } from 'lucide-react';

interface DashboardWidgetWrapperProps {
  title: string;
  isLoading: boolean;
  error: Error | null;
  children: ReactNode;
  /** Number of skeleton lines to show while loading (default: 3) */
  skeletonLines?: number;
}

export function DashboardWidgetWrapper({
  title,
  isLoading,
  error,
  children,
  skeletonLines = 3,
}: DashboardWidgetWrapperProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from({ length: skeletonLines }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Erro ao carregar dados. Tente novamente mais tarde.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Refactor financial-summary-widget to use wrapper**

In `frontend/app/(dashboard)/_components/financial-summary-widget.tsx`, replace the loading/error/Card boilerplate with:

```typescript
import { DashboardWidgetWrapper } from './dashboard-widget-wrapper';

export default function FinancialSummaryWidget() {
  const { data, isLoading, error } = useDashboardFinancialSummary();

  return (
    <DashboardWidgetWrapper
      title="Resumo Financeiro"
      isLoading={isLoading}
      error={error}
      skeletonLines={4}
    >
      {data && (
        // ... existing data rendering JSX (without the outer Card/CardHeader/CardContent)
      )}
    </DashboardWidgetWrapper>
  );
}
```

- [ ] **Step 3: Run type check and verify build**

```bash
cd frontend && npm run type-check && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(dashboard\)/_components/
git commit -m "refactor(frontend): add DashboardWidgetWrapper for consistent loading/error states

Creates a reusable wrapper that handles loading skeletons, error alerts,
and card layout for all dashboard widgets. Refactors financial-summary-widget
as the first consumer."
```

---

### Task 16: Migrate Test Fixtures to model_bakery

**Context:** Backend tests use 343+ manual `objects.create()` calls vs ~30 `baker.make()` uses. Manual creation is brittle — model schema changes break many tests. Migrate the most-used test files to `baker`.

**Files:**
- Modify: `tests/conftest.py` (add baker-based fixtures)
- Modify: `tests/integration/test_expense_api.py` (migrate to baker)

- [ ] **Step 1: Add baker fixture helpers to conftest.py**

In `tests/conftest.py`, add after the existing fixtures:

```python
from model_bakery import baker as model_baker


@pytest.fixture()
def make_building(admin_user):
    """Factory fixture for buildings using model_bakery."""

    def _make(street_number: int = 100, **kwargs):
        defaults = {"created_by": admin_user, "updated_by": admin_user}
        defaults.update(kwargs)
        return model_baker.make("core.Building", street_number=street_number, **defaults)

    return _make


@pytest.fixture()
def make_apartment(admin_user):
    """Factory fixture for apartments using model_bakery."""

    def _make(building=None, number: str = "101", **kwargs):
        if building is None:
            building = model_baker.make("core.Building", street_number=100)
        defaults = {
            "rental_value": Decimal("1000.00"),
            "rental_value_double": Decimal("1500.00"),
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(kwargs)
        return model_baker.make(
            "core.Apartment", building=building, number=number, **defaults
        )

    return _make


@pytest.fixture()
def make_expense(admin_user):
    """Factory fixture for expenses using model_bakery."""

    def _make(**kwargs):
        defaults = {"created_by": admin_user, "updated_by": admin_user}
        defaults.update(kwargs)
        return model_baker.make("core.Expense", **defaults)

    return _make
```

- [ ] **Step 2: Migrate one test file as reference**

Pick `tests/integration/test_expense_api.py`. Replace manual `Expense.objects.create(...)` calls with the `make_expense` fixture or direct `baker.make()` calls. For example:

```python
# Before:
expense = Expense.objects.create(
    description="Test",
    total_amount=Decimal("100.00"),
    expense_date="2026-01-01",
    expense_type="one_time_expense",
    created_by=admin_user,
    updated_by=admin_user,
)

# After:
expense = make_expense(
    description="Test",
    total_amount=Decimal("100.00"),
    expense_date="2026-01-01",
    expense_type="one_time_expense",
)
```

- [ ] **Step 3: Run migrated tests**

```bash
python -m pytest tests/integration/test_expense_api.py -v
```

Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/integration/test_expense_api.py
git commit -m "refactor(tests): add baker factory fixtures and migrate test_expense_api

Adds make_building, make_apartment, make_expense factory fixtures to
conftest.py using model_bakery. Migrates test_expense_api.py as the
first file to use the new pattern."
```

---

## Sprint 5: Auth Hardening — HttpOnly Cookies

### Task 17: Backend Cookie-Based JWT Authentication

**Context:** Currently JWT tokens are stored in `localStorage` (XSS-vulnerable). Must migrate to HttpOnly cookies. Backend needs: custom auth class that reads tokens from cookies, custom token views that set HttpOnly cookies, and a logout endpoint that clears cookies. Current flow: `frontend/lib/api/client.ts:15-29` reads token from localStorage and sets `Authorization` header. `frontend/lib/api/hooks/use-auth.ts:48-55` stores tokens in localStorage on login.

**Files:**
- Create: `core/authentication.py` (CookieJWTAuthentication)
- Create: `core/viewsets/auth_views_cookie.py` (cookie-setting token views)
- Modify: `condominios_manager/settings.py` (REST_FRAMEWORK auth classes, cookie config)
- Modify: `condominios_manager/urls.py` (swap token views)
- Test: `tests/integration/test_cookie_auth.py`

- [ ] **Step 1: Write failing test for cookie-based login**

Create `tests/integration/test_cookie_auth.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


class TestCookieLogin:
    """Tests for cookie-based JWT authentication."""

    def test_login_sets_httponly_cookies(self, api_client: APIClient, admin_user) -> None:
        response = api_client.post(
            "/api/auth/token/",
            {"email": admin_user.email, "password": "testpass123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert response.cookies["access_token"]["httponly"] is True
        assert response.cookies["access_token"]["samesite"] == "Lax"
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"]["httponly"] is True
        # Response body should contain user info, NOT tokens
        assert "access" not in response.data
        assert "refresh" not in response.data
        assert "user" in response.data

    def test_cookie_auth_grants_access_to_protected_endpoint(
        self, api_client: APIClient, admin_user
    ) -> None:
        # Login to get cookies
        login_response = api_client.post(
            "/api/auth/token/",
            {"email": admin_user.email, "password": "testpass123"},
            format="json",
        )
        # APIClient automatically carries cookies forward
        response = api_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == admin_user.email

    def test_refresh_sets_new_access_cookie(
        self, api_client: APIClient, admin_user
    ) -> None:
        # Login
        api_client.post(
            "/api/auth/token/",
            {"email": admin_user.email, "password": "testpass123"},
            format="json",
        )

        # Refresh — should set new access_token cookie
        response = api_client.post("/api/auth/token/refresh/")
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies

    def test_logout_clears_cookies(
        self, api_client: APIClient, admin_user
    ) -> None:
        # Login
        api_client.post(
            "/api/auth/token/",
            {"email": admin_user.email, "password": "testpass123"},
            format="json",
        )

        # Logout
        response = api_client.post("/api/auth/logout/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Cookies should be cleared (max-age=0)
        assert response.cookies["access_token"]["max-age"] == 0
        assert response.cookies["refresh_token"]["max-age"] == 0

        # Subsequent request should be unauthorized
        me_response = api_client.get("/api/auth/me/")
        assert me_response.status_code == status.HTTP_401_UNAUTHORIZED
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/integration/test_cookie_auth.py -v
```

Expected: FAIL — cookies not set

- [ ] **Step 3: Create CookieJWTAuthentication class**

Create `core/authentication.py`:

```python
"""Cookie-based JWT authentication backend."""

from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate using JWT from HttpOnly cookies, falling back to Authorization header."""

    def authenticate(self, request: Request):
        # Try standard Authorization header first
        header = self.get_header(request)
        if header is not None:
            raw_token = self.get_raw_token(header)
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token

        # Fall back to cookie
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
```

- [ ] **Step 4: Create cookie-setting token views**

Create `core/viewsets/auth_views_cookie.py`:

```python
"""Token views that set HttpOnly cookies instead of returning tokens in body."""

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

ACCESS_TOKEN_MAX_AGE = 60 * 60  # 1 hour
REFRESH_TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
IS_AUTHENTICATED_MAX_AGE = ACCESS_TOKEN_MAX_AGE
COOKIE_SAMESITE = "Lax"


def _set_auth_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    """Set HttpOnly JWT cookies on the response."""
    is_secure = not settings.DEBUG

    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=is_secure,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_MAX_AGE,
        path="/",
    )
    if refresh is not None:
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            httponly=True,
            secure=is_secure,
            samesite=COOKIE_SAMESITE,
            max_age=REFRESH_TOKEN_MAX_AGE,
            path="/",
        )
    # Non-HttpOnly cookie for middleware route protection
    response.set_cookie(
        key="is_authenticated",
        value="1",
        httponly=False,
        secure=is_secure,
        samesite=COOKIE_SAMESITE,
        max_age=IS_AUTHENTICATED_MAX_AGE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Delete all auth cookies."""
    for cookie_name in ("access_token", "refresh_token", "is_authenticated"):
        response.delete_cookie(cookie_name, path="/", samesite=COOKIE_SAMESITE)


class CookieTokenObtainPairView(TokenObtainPairView):
    """Login: set tokens as HttpOnly cookies, return user info only."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data["access"]
            refresh = response.data["refresh"]
            _set_auth_cookies(response, access, refresh)

            # Return user info instead of tokens
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.get(email=request.data.get("email"))
            response.data = {
                "user": {
                    "id": user.pk,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,
                },
            }
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh: read refresh token from cookie, set new access cookie."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        # Inject refresh token from cookie into request data
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token and "refresh" not in request.data:
            request.data._mutable = True  # type: ignore[attr-defined]
            request.data["refresh"] = refresh_token
            request.data._mutable = False  # type: ignore[attr-defined]

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            access = response.data.get("access", "")
            new_refresh = response.data.get("refresh")
            _set_auth_cookies(response, access, new_refresh)
            response.data = {}  # Don't return tokens in body
        return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cookie_logout(request: Request) -> Response:
    """Logout: blacklist refresh token and clear all auth cookies."""
    refresh_token = request.COOKIES.get("refresh_token")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass  # Token may already be blacklisted

    response = Response(status=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    return response
```

- [ ] **Step 5: Update settings.py — authentication classes**

In `condominios_manager/settings.py`, update REST_FRAMEWORK:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.CookieJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # ... rest unchanged
}
```

- [ ] **Step 6: Update urls.py — swap token views**

In `condominios_manager/urls.py`, replace lines 50-52:

```python
from core.viewsets.auth_views_cookie import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    cookie_logout,
)

# Replace standard JWT views with cookie-based versions
path("api/auth/token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
path("api/auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
path("api/auth/logout/", cookie_logout, name="logout"),
```

Remove the old `TokenBlacklistView` import and URL (now handled by `cookie_logout`).

- [ ] **Step 7: Run tests**

```bash
python -m pytest tests/integration/test_cookie_auth.py -v
```

Expected: ALL PASS

- [ ] **Step 8: Run ALL backend tests to verify no regressions**

```bash
python -m pytest tests/ -x --timeout=30
```

Note: Existing tests that use `authenticated_api_client` fixture should still work because `CookieJWTAuthentication` falls back to the Authorization header.

- [ ] **Step 9: Commit**

```bash
git add core/authentication.py core/viewsets/auth_views_cookie.py condominios_manager/settings.py condominios_manager/urls.py tests/integration/test_cookie_auth.py
git commit -m "feat(auth): implement HttpOnly cookie-based JWT authentication

Replaces token-in-body with HttpOnly cookies for XSS protection.
CookieJWTAuthentication reads from cookies with Authorization header
fallback. Login/refresh set cookies; logout clears and blacklists."
```

---

### Task 18: Frontend Cookie Migration

**Context:** After backend sets HttpOnly cookies (Task 17), frontend must: (1) add `withCredentials: true` to Axios, (2) remove ALL localStorage token storage, (3) simplify auth store to only persist user info, (4) simplify 401 interceptor. Current files: `frontend/lib/api/client.ts` (token interceptor), `frontend/lib/api/hooks/use-auth.ts` (login/logout), `frontend/store/auth-store.ts` (persists tokens).

**Files:**
- Modify: `frontend/lib/api/client.ts` (withCredentials, remove token interceptor)
- Modify: `frontend/lib/api/hooks/use-auth.ts` (remove localStorage, update login/logout/register)
- Modify: `frontend/store/auth-store.ts` (remove token fields)
- Test: `frontend/lib/api/hooks/__tests__/use-auth.test.tsx` (update existing tests)

- [ ] **Step 1: Update Axios client — add withCredentials, simplify interceptors**

In `frontend/lib/api/client.ts`, rewrite the file:

```typescript
import axios from 'axios';

const REQUEST_TIMEOUT_MS = 30_000;

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  timeout: REQUEST_TIMEOUT_MS,
  withCredentials: true, // Send HttpOnly cookies with every request
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor: handle 401 with automatic token refresh
let refreshPromise: Promise<void> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/token/')
    ) {
      originalRequest._retry = true;

      if (!refreshPromise) {
        refreshPromise = apiClient
          .post('/auth/token/refresh/')
          .then(() => {
            // New access_token cookie is set automatically by backend
          })
          .catch(async () => {
            const { useAuthStore } = await import('@/store/auth-store');
            useAuthStore.getState().clearAuth();
            window.location.href = '/login';
          })
          .finally(() => {
            refreshPromise = null;
          });
      }

      await refreshPromise;
      return apiClient(originalRequest);
    }

    return Promise.reject(error);
  },
);
```

Note: The entire request interceptor that attached Authorization header is **removed**. Cookies are sent automatically.

- [ ] **Step 2: Update auth store — remove token fields**

Rewrite `frontend/store/auth-store.ts`:

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;

  setAuth: (user: User) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setAuth: (user: User) =>
        set({
          user,
          isAuthenticated: true,
        }),

      setUser: (user: User) =>
        set({ user }),

      clearAuth: () =>
        set({
          user: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
```

Note: `token`, `refreshToken`, `setToken` are all removed. Only user info persists.

- [ ] **Step 3: Update auth hooks — remove localStorage**

Rewrite key functions in `frontend/lib/api/hooks/use-auth.ts`:

```typescript
// useLogin — tokens are in cookies now, response returns user info
export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      // Backend sets HttpOnly cookies AND returns user in body
      const { data } = await apiClient.post<{ user: User }>('/auth/token/', credentials);
      return data.user;
    },
    onSuccess: (user) => {
      setAuth(user);
    },
  });
}

// useLogout — backend clears cookies
export function useLogout() {
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout/');
    },
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      window.location.href = '/login';
    },
    onError: () => {
      // Even if backend fails, clear client state
      clearAuth();
      queryClient.clear();
      window.location.href = '/login';
    },
  });
}

// useRegister — same pattern, backend sets cookies
export function useRegister() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (registerData: RegisterData) => {
      const { data } = await apiClient.post<{ user: User }>(
        '/auth/register/',
        registerData,
      );
      return data.user;
    },
    onSuccess: (user) => {
      setAuth(user);
    },
  });
}

// useCurrentUser — cookies sent automatically
export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me/');
      return data;
    },
    retry: false,
  });
}

// Remove useRefreshToken hook entirely — refresh is handled by interceptor
```

- [ ] **Step 4: Remove all remaining localStorage token references**

Search and remove any remaining references to `localStorage.getItem('access_token')`, `localStorage.getItem('refresh_token')`, `localStorage.setItem(...)`, `localStorage.removeItem(...)` related to tokens across the entire frontend.

```bash
cd frontend && grep -rn "localStorage.*token\|access_token\|refresh_token" --include="*.ts" --include="*.tsx" lib/ store/ app/ components/
```

Fix any remaining references.

- [ ] **Step 5: Update MSW handlers for cookie responses**

In `frontend/tests/mocks/handlers.ts`, update the login handler to return user info instead of tokens:

```typescript
http.post(`${API_BASE}/auth/token/`, async ({ request }) => {
  const body = await request.json();
  // Validate credentials...
  return HttpResponse.json(
    {
      user: {
        id: 1,
        email: body.email,
        first_name: 'Admin',
        last_name: 'User',
        is_staff: true,
      },
    },
    { status: 200 },
  );
}),
```

Update refresh, register, and logout handlers similarly.

- [ ] **Step 6: Update auth tests**

Update `frontend/lib/api/hooks/__tests__/use-auth.test.tsx` to match new API contracts (no tokens in responses, no localStorage calls).

- [ ] **Step 7: Run all frontend tests**

```bash
cd frontend && npm run test:unit -- --run
```

- [ ] **Step 8: Run type check and lint**

```bash
cd frontend && npm run type-check && npm run lint
```

- [ ] **Step 9: Commit**

```bash
git add frontend/lib/api/client.ts frontend/store/auth-store.ts frontend/lib/api/hooks/use-auth.ts frontend/tests/mocks/handlers.ts frontend/lib/api/hooks/__tests__/use-auth.test.tsx
git commit -m "feat(frontend): migrate from localStorage tokens to HttpOnly cookies

Removes all localStorage token storage. Axios sends cookies automatically
via withCredentials. Auth store only persists user info. 401 interceptor
simplified to just call refresh endpoint (cookie-based)."
```

---

### Task 19: OAuth Cookie Flow Update

**Context:** Google OAuth currently returns tokens via one-time code exchange (`core/auth.py:130-167`). Must update to set HttpOnly cookies instead of returning tokens in the response body. Frontend OAuth callback must also be updated.

**Files:**
- Modify: `core/auth.py` (exchange_oauth_code function)
- Modify: Frontend OAuth callback component (if exists)
- Test: `tests/integration/test_cookie_auth.py` (add OAuth test)

- [ ] **Step 1: Write failing test for OAuth cookie flow**

Add to `tests/integration/test_cookie_auth.py`:

```python
class TestOAuthCookieFlow:
    """Tests for OAuth token exchange with cookie-based auth."""

    def test_exchange_oauth_code_sets_cookies(
        self, api_client: APIClient, admin_user
    ) -> None:
        from core.models import OAuthExchangeCode
        from rest_framework_simplejwt.tokens import RefreshToken

        # Create a valid exchange code (simulating Google OAuth callback)
        refresh = RefreshToken.for_user(admin_user)
        exchange = OAuthExchangeCode.objects.create(
            user=admin_user,
            code="test-code-123",
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
        )

        response = api_client.post(
            "/api/auth/oauth/exchange/",
            {"code": "test-code-123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert response.cookies["access_token"]["httponly"] is True
        assert "refresh_token" in response.cookies
        assert "access" not in response.data
        assert "user" in response.data
```

- [ ] **Step 2: Update exchange_oauth_code to set cookies**

In `core/auth.py`, find the `exchange_oauth_code` function. After retrieving the tokens from the `OAuthExchangeCode` record, instead of returning them in the JSON body, set them as cookies:

```python
from core.viewsets.auth_views_cookie import _set_auth_cookies

@api_view(["POST"])
@permission_classes([AllowAny])
def exchange_oauth_code(request: Request) -> Response:
    # ... existing code to find and validate exchange code ...

    user_data = {
        "user": {
            "id": exchange.user.pk,
            "email": exchange.user.email,
            "first_name": exchange.user.first_name,
            "last_name": exchange.user.last_name,
            "is_staff": exchange.user.is_staff,
        },
    }
    response = Response(user_data, status=status.HTTP_200_OK)
    _set_auth_cookies(response, exchange.access_token, exchange.refresh_token)

    # Mark code as used
    exchange.delete()

    return response
```

- [ ] **Step 3: Update register endpoint to set cookies**

In `core/viewsets/auth_views_registration.py`, update the `register_user` view to set cookies:

```python
from core.viewsets.auth_views_cookie import _set_auth_cookies

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def register_user(request: Request) -> Response:
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    refresh = RefreshToken.for_user(user)
    user_data = {
        "user": {
            "id": user.pk,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
        },
    }
    response = Response(user_data, status=status.HTTP_201_CREATED)
    _set_auth_cookies(response, str(refresh.access_token), str(refresh))
    return response
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/integration/test_cookie_auth.py tests/integration/test_auth_registration.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/auth.py core/viewsets/auth_views_registration.py tests/integration/test_cookie_auth.py
git commit -m "feat(auth): update OAuth and register to use HttpOnly cookies

All auth endpoints now set HttpOnly cookies consistently. OAuth code
exchange and user registration both use _set_auth_cookies helper."
```

---

## Sprint 6: Tenant Portal UI

### Task 20: Tenant Auth Flow + Layout

**Context:** Tenants authenticate via WhatsApp OTP (backend: `POST /api/auth/whatsapp/request/` and `POST /api/auth/whatsapp/verify/` in `core/viewsets/auth_views.py:56-189`). OTP sends 6-digit code to tenant's phone. Verification creates a Django User for the tenant and returns JWT tokens. Frontend needs a separate login page and route group for tenants. Backend endpoints are mobile-first but fully compatible with web.

**Files:**
- Create: `frontend/app/(tenant)/layout.tsx`
- Create: `frontend/app/(tenant)/login/page.tsx`
- Create: `frontend/lib/api/hooks/use-tenant-auth.ts`
- Create: `frontend/components/layouts/tenant-layout.tsx`
- Modify: `frontend/middleware.ts` (add tenant route handling)
- Test: `frontend/lib/api/hooks/__tests__/use-tenant-auth.test.tsx`

- [ ] **Step 1: Create tenant auth hooks**

Create `frontend/lib/api/hooks/use-tenant-auth.ts`:

```typescript
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useAuthStore } from '@/store/auth-store';
import type { User } from '@/store/auth-store';

interface RequestOtpData {
  cpf_cnpj: string;
}

interface VerifyOtpData {
  cpf_cnpj: string;
  code: string;
}

interface VerifyOtpResponse {
  user: User;
}

export function useRequestOtp() {
  return useMutation({
    mutationFn: async (data: RequestOtpData) => {
      const response = await apiClient.post<{ detail: string }>(
        '/auth/whatsapp/request/',
        data,
      );
      return response.data;
    },
  });
}

export function useVerifyOtp() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (data: VerifyOtpData) => {
      const { data: responseData } = await apiClient.post<VerifyOtpResponse>(
        '/auth/whatsapp/verify/',
        data,
      );
      return responseData.user;
    },
    onSuccess: (user) => {
      setAuth(user);
    },
  });
}
```

- [ ] **Step 2: Add MSW handlers for tenant auth**

Add to `frontend/tests/mocks/handlers.ts`:

```typescript
// Tenant WhatsApp OTP auth
http.post(`${API_BASE}/auth/whatsapp/request/`, async ({ request }) => {
  const body = await request.json();
  if (!body.cpf_cnpj) {
    return HttpResponse.json({ detail: 'CPF/CNPJ é obrigatório.' }, { status: 400 });
  }
  return HttpResponse.json({ detail: 'Código enviado via WhatsApp.' }, { status: 200 });
}),

http.post(`${API_BASE}/auth/whatsapp/verify/`, async ({ request }) => {
  const body = await request.json();
  if (body.code !== '123456') {
    return HttpResponse.json({ detail: 'Código inválido.' }, { status: 400 });
  }
  return HttpResponse.json({
    user: { id: 10, email: 'tenant@example.com', first_name: 'Tenant', last_name: 'User', is_staff: false },
  }, { status: 200 });
}),
```

- [ ] **Step 3: Write test for tenant auth hooks**

Create `frontend/lib/api/hooks/__tests__/use-tenant-auth.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '@/tests/test-utils';
import { useRequestOtp, useVerifyOtp } from '../use-tenant-auth';

describe('useRequestOtp', () => {
  it('sends OTP request with CPF', async () => {
    const { result } = renderHook(() => useRequestOtp(), { wrapper: createWrapper() });

    result.current.mutate({ cpf_cnpj: '52998224725' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.detail).toContain('WhatsApp');
  });
});

describe('useVerifyOtp', () => {
  it('verifies OTP and sets auth state', async () => {
    const { result } = renderHook(() => useVerifyOtp(), { wrapper: createWrapper() });

    result.current.mutate({ cpf_cnpj: '52998224725', code: '123456' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('rejects invalid OTP code', async () => {
    const { result } = renderHook(() => useVerifyOtp(), { wrapper: createWrapper() });

    result.current.mutate({ cpf_cnpj: '52998224725', code: '000000' });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
```

- [ ] **Step 4: Create tenant layout**

Create `frontend/components/layouts/tenant-layout.tsx`:

```typescript
'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { Building2, FileText, CreditCard, Bell, User, LogOut } from 'lucide-react';
import { useLogout } from '@/lib/api/hooks/use-auth';
import { useAuthStore } from '@/store/auth-store';
import { Button } from '@/components/ui/button';

const TENANT_NAV_ITEMS = [
  { href: '/tenant', label: 'Início', icon: Building2 },
  { href: '/tenant/payments', label: 'Pagamentos', icon: CreditCard },
  { href: '/tenant/contract', label: 'Contrato', icon: FileText },
  { href: '/tenant/notifications', label: 'Notificações', icon: Bell },
  { href: '/tenant/profile', label: 'Perfil', icon: User },
] as const;

interface TenantLayoutProps {
  children: ReactNode;
}

export function TenantPortalLayout({ children }: TenantLayoutProps) {
  const { user } = useAuthStore();
  const { mutate: logout } = useLogout();

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <span className="text-lg font-semibold">Portal do Inquilino</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">{user?.first_name}</span>
            <Button variant="ghost" size="icon" onClick={() => logout()}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="container py-6">{children}</div>

      <nav className="fixed bottom-0 left-0 right-0 border-t bg-card md:hidden">
        <div className="flex justify-around py-2">
          {TENANT_NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex flex-col items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <Icon className="h-5 w-5" />
              {label}
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}
```

- [ ] **Step 5: Create tenant route group layout**

Create `frontend/app/(tenant)/layout.tsx`:

```typescript
import type { ReactNode } from 'react';
import { TenantPortalLayout } from '@/components/layouts/tenant-layout';

export default function TenantLayout({ children }: { children: ReactNode }) {
  return <TenantPortalLayout>{children}</TenantPortalLayout>;
}
```

- [ ] **Step 6: Create tenant login page**

Create `frontend/app/(tenant)/login/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRequestOtp, useVerifyOtp } from '@/lib/api/hooks/use-tenant-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'sonner';

export default function TenantLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<'cpf' | 'otp'>('cpf');
  const [cpfCnpj, setCpfCnpj] = useState('');
  const [otpCode, setOtpCode] = useState('');

  const requestOtp = useRequestOtp();
  const verifyOtp = useVerifyOtp();

  const handleRequestOtp = () => {
    requestOtp.mutate(
      { cpf_cnpj: cpfCnpj.replace(/\D/g, '') },
      {
        onSuccess: () => {
          setStep('otp');
          toast.success('Código enviado via WhatsApp!');
        },
        onError: () => {
          toast.error('CPF/CNPJ não encontrado.');
        },
      },
    );
  };

  const handleVerifyOtp = () => {
    verifyOtp.mutate(
      { cpf_cnpj: cpfCnpj.replace(/\D/g, ''), code: otpCode },
      {
        onSuccess: () => {
          router.push('/tenant');
        },
        onError: () => {
          toast.error('Código inválido ou expirado.');
        },
      },
    );
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Portal do Inquilino</CardTitle>
          <CardDescription>
            {step === 'cpf'
              ? 'Digite seu CPF/CNPJ para receber o código de acesso'
              : 'Digite o código enviado para seu WhatsApp'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {step === 'cpf' ? (
            <>
              <Input
                placeholder="CPF ou CNPJ"
                value={cpfCnpj}
                onChange={(e) => setCpfCnpj(e.target.value)}
                maxLength={18}
              />
              <Button
                className="w-full"
                onClick={handleRequestOtp}
                disabled={requestOtp.isPending || cpfCnpj.replace(/\D/g, '').length < 11}
              >
                {requestOtp.isPending ? 'Enviando...' : 'Enviar Código'}
              </Button>
            </>
          ) : (
            <>
              <Input
                placeholder="Código de 6 dígitos"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                maxLength={6}
                className="text-center text-2xl tracking-widest"
              />
              <Button
                className="w-full"
                onClick={handleVerifyOtp}
                disabled={verifyOtp.isPending || otpCode.length < 6}
              >
                {verifyOtp.isPending ? 'Verificando...' : 'Entrar'}
              </Button>
              <Button variant="link" className="w-full" onClick={() => setStep('cpf')}>
                Voltar
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 7: Update middleware for tenant routes**

In `frontend/middleware.ts`, update `PUBLIC_PATHS` and add tenant route handling:

```typescript
const PUBLIC_PATHS = ['/login', '/register', '/tenant/login'];
```

- [ ] **Step 8: Run tests and type check**

```bash
cd frontend && npm run test:unit -- --run lib/api/hooks/__tests__/use-tenant-auth.test.tsx && npm run type-check
```

- [ ] **Step 9: Commit**

```bash
git add frontend/app/\(tenant\)/ frontend/components/layouts/tenant-layout.tsx frontend/lib/api/hooks/use-tenant-auth.ts frontend/lib/api/hooks/__tests__/use-tenant-auth.test.tsx frontend/tests/mocks/handlers.ts frontend/middleware.ts
git commit -m "feat(tenant-portal): add tenant auth flow, layout, and login page

WhatsApp OTP authentication with 2-step flow (CPF → code). Separate
route group (tenant) with mobile-first layout. Bottom nav for mobile."
```

---

### Task 21: Tenant Dashboard + Profile Pages

**Context:** Backend endpoints: `GET /api/tenant/me/` returns profile + lease + apartment data. Frontend needs a dashboard showing rent due, lease status, and quick actions, plus a profile view page.

**Files:**
- Create: `frontend/app/(tenant)/page.tsx` (dashboard)
- Create: `frontend/app/(tenant)/profile/page.tsx`
- Create: `frontend/lib/api/hooks/use-tenant-portal.ts`

- [ ] **Step 1: Create tenant portal hooks**

Create `frontend/lib/api/hooks/use-tenant-portal.ts`:

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { queryKeys } from '@/lib/api/query-keys';

export interface TenantProfile {
  id: number;
  name: string;
  cpf_cnpj: string;
  phone: string;
  marital_status: string;
  profession: string;
  due_day: number;
  dependents: { id: number; name: string; phone: string; cpf_cnpj: string }[];
  lease: {
    id: number;
    start_date: string;
    validity_months: number;
    rental_value: string;
    pending_rental_value: string | null;
    pending_rental_value_date: string | null;
    number_of_tenants: number;
    contract_generated: boolean;
  };
  apartment: {
    id: number;
    number: string;
    building_name: string;
    building_address: string;
  };
}

export function useTenantProfile() {
  return useQuery({
    queryKey: ['tenant', 'profile'],
    queryFn: async () => {
      const { data } = await apiClient.get<TenantProfile>('/tenant/me/');
      return data;
    },
  });
}
```

- [ ] **Step 2: Create tenant dashboard page**

Create `frontend/app/(tenant)/page.tsx`:

```typescript
'use client';

import { Building2, Calendar, CreditCard, FileText } from 'lucide-react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useTenantProfile } from '@/lib/api/hooks/use-tenant-portal';
import { formatCurrency } from '@/lib/utils/formatters';

export default function TenantDashboardPage() {
  const { data: profile, isLoading, error } = useTenantProfile();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Erro ao carregar dados. Tente novamente.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Olá, {profile.name.split(' ')[0]}!</h1>
        <p className="text-muted-foreground">
          Apto {profile.apartment.number} — {profile.apartment.building_name}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Aluguel
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold">{formatCurrency(profile.lease.rental_value)}</p>
          <p className="text-sm text-muted-foreground">
            Vencimento dia {profile.due_day} de cada mês
          </p>
          {profile.lease.pending_rental_value && (
            <p className="mt-2 text-sm text-warning">
              Novo valor a partir de {profile.lease.pending_rental_value_date}:{' '}
              {formatCurrency(profile.lease.pending_rental_value)}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Link href="/tenant/payments">
          <Card className="cursor-pointer transition-colors hover:bg-accent">
            <CardContent className="flex items-center gap-3 pt-6">
              <CreditCard className="h-8 w-8 text-primary" />
              <div>
                <p className="font-medium">Pagar Aluguel</p>
                <p className="text-sm text-muted-foreground">PIX ou comprovante</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/tenant/contract">
          <Card className="cursor-pointer transition-colors hover:bg-accent">
            <CardContent className="flex items-center gap-3 pt-6">
              <FileText className="h-8 w-8 text-primary" />
              <div>
                <p className="font-medium">Meu Contrato</p>
                <p className="text-sm text-muted-foreground">Visualizar ou baixar</p>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/tenant/notifications">
          <Card className="cursor-pointer transition-colors hover:bg-accent">
            <CardContent className="flex items-center gap-3 pt-6">
              <Calendar className="h-8 w-8 text-primary" />
              <div>
                <p className="font-medium">Notificações</p>
                <p className="text-sm text-muted-foreground">Avisos e lembretes</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create profile page**

Create `frontend/app/(tenant)/profile/page.tsx`:

```typescript
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useTenantProfile } from '@/lib/api/hooks/use-tenant-portal';

export default function TenantProfilePage() {
  const { data: profile, isLoading, error } = useTenantProfile();

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error || !profile) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Erro ao carregar perfil.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Meu Perfil</h1>

      <Card>
        <CardHeader><CardTitle>Dados Pessoais</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <InfoRow label="Nome" value={profile.name} />
          <InfoRow label="CPF/CNPJ" value={profile.cpf_cnpj} />
          <InfoRow label="Telefone" value={profile.phone} />
          <InfoRow label="Estado Civil" value={profile.marital_status} />
          <InfoRow label="Profissão" value={profile.profession} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Imóvel</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <InfoRow label="Apartamento" value={profile.apartment.number} />
          <InfoRow label="Prédio" value={profile.apartment.building_name} />
          <InfoRow label="Endereço" value={profile.apartment.building_address} />
          <InfoRow label="Dia de Vencimento" value={String(profile.due_day)} />
        </CardContent>
      </Card>

      {profile.dependents.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Dependentes</CardTitle></CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {profile.dependents.map((dep) => (
                <li key={dep.id} className="flex justify-between border-b pb-2">
                  <span>{dep.name}</span>
                  <span className="text-muted-foreground">{dep.phone}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
```

- [ ] **Step 4: Run type check**

```bash
cd frontend && npm run type-check
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/\(tenant\)/ frontend/lib/api/hooks/use-tenant-portal.ts
git commit -m "feat(tenant-portal): add dashboard and profile pages

Tenant dashboard shows rent, lease info, and quick actions.
Profile page displays personal data, apartment info, and dependents."
```

---

### Task 22: Tenant Payments + PIX

**Context:** Backend endpoints: `GET /api/tenant/payments/` (payment history), `POST /api/tenant/payments/pix/` (generate PIX code), `GET /api/tenant/rent-adjustments/` (adjustment history). Frontend needs payment history page with PIX generation.

**Files:**
- Create: `frontend/app/(tenant)/payments/page.tsx`
- Add hooks to: `frontend/lib/api/hooks/use-tenant-portal.ts`

- [ ] **Step 1: Add payment hooks**

Append to `frontend/lib/api/hooks/use-tenant-portal.ts`:

```typescript
import { useMutation, useQuery } from '@tanstack/react-query';

export interface RentPayment {
  id: number;
  reference_month: string;
  amount_paid: string;
  payment_date: string;
  notes: string;
}

export interface PixResponse {
  pix_payload: string;
  amount: string;
  recipient: string;
}

export function useTenantPayments() {
  return useQuery({
    queryKey: ['tenant', 'payments'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ results: RentPayment[] }>('/tenant/payments/');
      return data.results;
    },
  });
}

export function useTenantRentAdjustments() {
  return useQuery({
    queryKey: ['tenant', 'rent-adjustments'],
    queryFn: async () => {
      const { data } = await apiClient.get<RentAdjustment[]>('/tenant/rent-adjustments/');
      return data;
    },
  });
}

interface RentAdjustment {
  id: number;
  adjustment_date: string;
  percentage: string;
  previous_value: string;
  new_value: string;
}

export function useGeneratePix() {
  return useMutation({
    mutationFn: async (params?: { amount?: string; description?: string }) => {
      const { data } = await apiClient.post<PixResponse>('/tenant/payments/pix/', params ?? {});
      return data;
    },
  });
}
```

- [ ] **Step 2: Create payments page**

Create `frontend/app/(tenant)/payments/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { Copy, Check, QrCode } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from 'sonner';
import {
  useTenantPayments,
  useTenantRentAdjustments,
  useGeneratePix,
} from '@/lib/api/hooks/use-tenant-portal';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

export default function TenantPaymentsPage() {
  const { data: payments, isLoading } = useTenantPayments();
  const { data: adjustments } = useTenantRentAdjustments();
  const generatePix = useGeneratePix();
  const [pixCode, setPixCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGeneratePix = () => {
    generatePix.mutate(undefined, {
      onSuccess: (data) => {
        setPixCode(data.pix_payload);
        toast.success('Código PIX gerado!');
      },
      onError: () => {
        toast.error('Erro ao gerar código PIX.');
      },
    });
  };

  const handleCopyPix = async () => {
    if (!pixCode) return;
    await navigator.clipboard.writeText(pixCode);
    setCopied(true);
    toast.success('Código PIX copiado!');
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Pagamentos</h1>

      {/* PIX Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <QrCode className="h-5 w-5" />
            Pagar via PIX
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {pixCode ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">Copie o código abaixo:</p>
              <div className="rounded-md bg-muted p-3 font-mono text-xs break-all">
                {pixCode}
              </div>
              <Button onClick={handleCopyPix} className="w-full">
                {copied ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                {copied ? 'Copiado!' : 'Copiar Código PIX'}
              </Button>
            </div>
          ) : (
            <Button onClick={handleGeneratePix} disabled={generatePix.isPending} className="w-full">
              {generatePix.isPending ? 'Gerando...' : 'Gerar Código PIX'}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Payment History */}
      <Card>
        <CardHeader><CardTitle>Histórico de Pagamentos</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : payments && payments.length > 0 ? (
            <div className="space-y-2">
              {payments.map((payment) => (
                <div key={payment.id} className="flex justify-between border-b py-3">
                  <div>
                    <p className="font-medium">{formatDate(payment.reference_month)}</p>
                    <p className="text-sm text-muted-foreground">
                      Pago em {formatDate(payment.payment_date)}
                    </p>
                  </div>
                  <p className="font-semibold">{formatCurrency(payment.amount_paid)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-4">Nenhum pagamento registrado.</p>
          )}
        </CardContent>
      </Card>

      {/* Rent Adjustments */}
      {adjustments && adjustments.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Reajustes de Aluguel</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {adjustments.map((adj) => (
                <div key={adj.id} className="flex justify-between border-b py-3">
                  <div>
                    <p className="font-medium">{formatDate(adj.adjustment_date)}</p>
                    <p className="text-sm text-muted-foreground">{adj.percentage}%</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm line-through text-muted-foreground">
                      {formatCurrency(adj.previous_value)}
                    </p>
                    <p className="font-semibold">{formatCurrency(adj.new_value)}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Run type check and commit**

```bash
cd frontend && npm run type-check
git add frontend/app/\(tenant\)/payments/ frontend/lib/api/hooks/use-tenant-portal.ts
git commit -m "feat(tenant-portal): add payments page with PIX generation

Payment history with rent adjustment timeline. PIX code generation
with copy-to-clipboard. Mobile-first layout."
```

---

### Task 23: Tenant Proof Upload + Notifications + Contract

**Context:** Backend endpoints: `POST /api/tenant/payments/proof/` (upload receipt), `GET /api/tenant/payments/proof/<id>/` (check status), `GET /api/tenant/notifications/` (notifications), `PATCH /api/tenant/notifications/<id>/read/`, `POST /api/tenant/notifications/read-all/`, `GET /api/tenant/contract/` (PDF download).

**Files:**
- Create: `frontend/app/(tenant)/payments/proof/page.tsx`
- Create: `frontend/app/(tenant)/notifications/page.tsx`
- Create: `frontend/app/(tenant)/contract/page.tsx`
- Add hooks to: `frontend/lib/api/hooks/use-tenant-portal.ts`

- [ ] **Step 1: Add proof, notification, and contract hooks**

Append to `frontend/lib/api/hooks/use-tenant-portal.ts`:

```typescript
export interface PaymentProof {
  id: number;
  reference_month: string;
  file: string;
  pix_code: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewed_at: string | null;
  rejection_reason: string;
  created_at: string;
}

export interface Notification {
  id: number;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  read_at: string | null;
  sent_at: string;
}

export function useUploadProof() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) => {
      const { data } = await apiClient.post<PaymentProof>('/tenant/payments/proof/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant', 'payments'] });
    },
  });
}

export function useTenantNotifications() {
  return useQuery({
    queryKey: ['tenant', 'notifications'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ results: Notification[] }>('/tenant/notifications/');
      return data.results;
    },
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.patch(`/tenant/notifications/${id}/read/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant', 'notifications'] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/tenant/notifications/read-all/');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant', 'notifications'] });
    },
  });
}

export function useDownloadContract() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.get('/tenant/contract/', {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'contrato.pdf';
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}
```

- [ ] **Step 2: Create proof upload page, notifications page, and contract page**

These follow the same patterns as Tasks 21-22 (loading/error states, Card layout, mobile-first). Create each page in its respective directory with the hooks defined above. The proof upload page uses a `<input type="file">` with FormData. The notifications page is a list with read/unread states. The contract page has a download button.

(Full component code follows same patterns shown in Tasks 21-22 — Card-based layout, loading skeletons, error alerts, hook integration.)

- [ ] **Step 3: Run type check and full build**

```bash
cd frontend && npm run type-check && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/\(tenant\)/ frontend/lib/api/hooks/use-tenant-portal.ts
git commit -m "feat(tenant-portal): add proof upload, notifications, and contract pages

Complete tenant portal: proof upload with status tracking, notification
center with mark-as-read, and contract PDF download."
```

---

## Sprint 7: Full Component Test Coverage

### Task 24: P0 — Form Modal Tests

**Context:** 10 form modal components have zero tests. These handle user input validation, submission, and error handling. Most critical components: `apartment-form-modal.tsx`, `building-form-modal.tsx`, `furniture-form-modal.tsx`, `lease-form-modal.tsx`, `tenant-lease-modal.tsx`, `contract-generate-modal.tsx`, `rent-adjustment-modal.tsx`, `late-fee-modal.tsx`, `due-date-modal.tsx`, `quick-payment-modal.tsx`.

**Files:**
- Create: Test files for each form modal in their respective `__tests__/` directories

- [ ] **Step 1: Set up test pattern for form modals**

All form modal tests follow this pattern:

```typescript
import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { http, HttpResponse } from 'msw';

import SomeFormModal from '../some-form-modal';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api';

describe('SomeFormModal', () => {
  const defaultProps = {
    open: true,
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  };

  it('renders form fields when open', () => {
    renderWithProviders(<SomeFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('validates required fields on submit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SomeFormModal {...defaultProps} />);

    const submitButton = screen.getByRole('button', { name: /salvar/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/obrigatório/i)).toBeInTheDocument();
    });
  });

  it('submits valid data and calls onSuccess', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SomeFormModal {...defaultProps} />);

    // Fill required fields...
    await user.type(screen.getByLabelText(/nome/i), 'Test');
    await user.click(screen.getByRole('button', { name: /salvar/i }));

    await waitFor(() => {
      expect(defaultProps.onSuccess).toHaveBeenCalled();
    });
  });

  it('shows error message on API failure', async () => {
    server.use(
      http.post(`${API_BASE}/resource/`, () =>
        HttpResponse.json({ detail: 'Validation error' }, { status: 400 }),
      ),
    );
    // ... submit form, assert error toast/message
  });
});
```

- [ ] **Step 2-11: Create test file for each form modal**

Apply the pattern above to create test files for all 10 form modals. Each test covers: renders fields, validates required fields, submits successfully, handles API errors.

Create files:
1. `frontend/app/(dashboard)/apartments/_components/__tests__/apartment-form-modal.test.tsx`
2. `frontend/app/(dashboard)/buildings/_components/__tests__/building-form-modal.test.tsx`
3. `frontend/app/(dashboard)/furniture/_components/__tests__/furniture-form-modal.test.tsx`
4. `frontend/app/(dashboard)/leases/_components/__tests__/lease-form-modal.test.tsx`
5. `frontend/app/(dashboard)/tenants/_components/__tests__/tenant-lease-modal.test.tsx`
6. `frontend/app/(dashboard)/leases/_components/__tests__/contract-generate-modal.test.tsx`
7. `frontend/app/(dashboard)/leases/_components/__tests__/rent-adjustment-modal.test.tsx`
8. `frontend/app/(dashboard)/leases/_components/__tests__/late-fee-modal.test.tsx`
9. `frontend/app/(dashboard)/leases/_components/__tests__/due-date-modal.test.tsx`
10. `frontend/app/(dashboard)/financial/_components/__tests__/quick-payment-modal.test.tsx`

- [ ] **Step 12: Run all new tests**

```bash
cd frontend && npm run test:unit -- --run app/
```

- [ ] **Step 13: Commit**

```bash
git add frontend/app/
git commit -m "test(frontend): add P0 form modal tests for all CRUD forms

Tests cover: field rendering, required validation, successful submission,
and API error handling for 10 form modals."
```

---

### Task 25: P1 — Dashboard Widget Tests

**Context:** 6 dashboard widgets in `frontend/app/(dashboard)/_components/` have no tests. All follow the same pattern: hook → loading/error/data states. Plus financial detail widgets.

**Files:**
- Create: `frontend/app/(dashboard)/_components/__tests__/` (6 test files)

- [ ] **Step 1-6: Create tests for each widget**

Follow the pattern from Task 13 (financial-summary-widget.test.tsx) for all 6 widgets:
1. `lease-metrics-widget.test.tsx`
2. `tenant-statistics-widget.test.tsx`
3. `building-statistics-chart.test.tsx`
4. `late-payments-alert.test.tsx`
5. `rent-adjustment-alerts.test.tsx`
6. `financial-summary-widget.test.tsx` (already started in Task 13)

Each test covers: loading skeleton, error alert, data rendering.

- [ ] **Step 7: Run tests and commit**

```bash
cd frontend && npm run test:unit -- --run app/\(dashboard\)/_components/__tests__/
git add frontend/app/\(dashboard\)/_components/__tests__/
git commit -m "test(frontend): add P1 dashboard widget tests

Tests loading, error, and data states for all 6 dashboard widgets."
```

---

### Task 26: P2 — Layout + Auth-Gated Component Tests

**Context:** Layout components (`main-layout.tsx`, `header.tsx`, `sidebar.tsx`) render conditionally based on auth state. Need tests verifying admin-only nav items are hidden for non-staff users.

**Files:**
- Create: `frontend/components/layouts/__tests__/` (3 test files)

- [ ] **Step 1-3: Create tests for layout components**

Test patterns:
- `main-layout`: Renders children, shows loading during user fetch
- `header`: Shows user name, admin menu visible only for `is_staff`
- `sidebar`: Navigation items, admin-only sections hidden

- [ ] **Step 4: Run tests and commit**

```bash
cd frontend && npm run test:unit -- --run components/layouts/__tests__/
git add frontend/components/layouts/__tests__/
git commit -m "test(frontend): add P2 layout component tests with auth gating

Tests conditional rendering based on is_staff flag in header,
sidebar, and main-layout components."
```

---

### Task 27: P3 — Utility Component Tests

**Context:** Shared components: `confirm-dialog.tsx`, `delete-confirm-dialog.tsx`, `error-boundary.tsx`, `global-search.tsx`, `data-table.tsx`.

**Files:**
- Create: `frontend/components/shared/__tests__/` (3 test files)
- Create: `frontend/components/search/__tests__/global-search.test.tsx`

- [ ] **Step 1-4: Create tests for utility components**

- `confirm-dialog`: Test `showConfirmDialog()` and `showDeleteConfirm()` utility functions
- `error-boundary`: Test error catching and reset functionality
- `global-search`: Test search input, debounce, result rendering

- [ ] **Step 5: Run tests and commit**

```bash
cd frontend && npm run test:unit -- --run components/
git add frontend/components/
git commit -m "test(frontend): add P3 utility component tests

Tests confirm dialogs, error boundary, and global search."
```

---

## Sprint 8: Full Baker Migration

### Task 28: Create Baker Factory Module + Migrate Conftest

**Context:** 559 manual `objects.create()` calls across 43 test files. Only 1 file uses baker. Need a centralized factory module with helpers for all 31 models, respecting dependency order.

**Files:**
- Create: `tests/factories.py`
- Modify: `tests/conftest.py` (migrate existing fixtures)

- [ ] **Step 1: Create tests/factories.py**

```python
"""Baker-based factory helpers for all core models.

Usage:
    from tests.factories import make_building, make_apartment, make_expense
    building = make_building(street_number=100)
    apartment = make_apartment(building=building)
"""

from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from model_bakery import baker

User = get_user_model()

# Valid CPFs for tests (pre-validated)
TEST_CPFS = [
    "52998224725", "11144477735", "12345678909", "98765432100",
    "45612378901", "78901234567", "32165498700", "65498732100",
    "14725836900", "25836914700", "36914725800", "74185296300",
    "85296374100", "96374185200", "15935748600",
]

_cpf_counter = 0


def _next_cpf() -> str:
    global _cpf_counter
    cpf = TEST_CPFS[_cpf_counter % len(TEST_CPFS)]
    _cpf_counter += 1
    return cpf


def make_admin_user(**kwargs) -> User:
    defaults = {
        "is_staff": True,
        "is_superuser": True,
    }
    defaults.update(kwargs)
    return baker.make(User, **defaults)


def make_building(street_number: int = 100, user=None, **kwargs):
    defaults = {}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Building", street_number=street_number, **defaults)


def make_apartment(building=None, number: str = "101", user=None, **kwargs):
    if building is None:
        building = make_building(user=user)
    defaults = {
        "rental_value": Decimal("1000.00"),
        "rental_value_double": Decimal("1500.00"),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Apartment", building=building, number=number, **defaults)


def make_tenant(cpf_cnpj: str | None = None, user=None, **kwargs):
    defaults = {
        "cpf_cnpj": cpf_cnpj or _next_cpf(),
        "full_name": kwargs.pop("full_name", "Test Tenant"),
        "phone": kwargs.pop("phone", "11999999999"),
        "nationality": "Brasileiro",
        "marital_status": "Solteiro(a)",
    }
    defaults.update(kwargs)
    return baker.make("core.Tenant", **defaults)


def make_lease(apartment=None, tenant=None, user=None, **kwargs):
    if apartment is None:
        apartment = make_apartment(user=user)
    if tenant is None:
        tenant = make_tenant(user=user)
    defaults = {
        "rental_value": Decimal("1000.00"),
        "due_day": 5,
        "start_date": date(2026, 1, 1),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make(
        "core.Lease",
        apartment=apartment,
        responsible_tenant=tenant,
        **defaults,
    )


def make_person(user=None, **kwargs):
    defaults = {"name": "Test Person"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Person", **defaults)


def make_credit_card(person=None, user=None, **kwargs):
    if person is None:
        person = make_person(user=user)
    defaults = {
        "name": "Test Card",
        "closing_day": 15,
        "due_day": 25,
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.CreditCard", person=person, **defaults)


def make_expense_category(user=None, **kwargs):
    defaults = {"name": "Test Category"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.ExpenseCategory", **defaults)


def make_expense(user=None, **kwargs):
    defaults = {
        "description": "Test Expense",
        "total_amount": Decimal("100.00"),
        "expense_date": date(2026, 1, 15),
        "expense_type": "one_time_expense",
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Expense", **defaults)


def make_expense_installment(expense=None, user=None, **kwargs):
    if expense is None:
        expense = make_expense(user=user, is_installment=True)
    defaults = {
        "installment_number": 1,
        "total_installments": 1,
        "amount": expense.total_amount,
        "due_date": date(2026, 2, 15),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.ExpenseInstallment", expense=expense, **defaults)


def make_income(user=None, **kwargs):
    defaults = {
        "description": "Test Income",
        "amount": Decimal("500.00"),
        "income_date": date(2026, 1, 15),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Income", **defaults)


def make_rent_payment(lease=None, user=None, **kwargs):
    if lease is None:
        lease = make_lease(user=user)
    defaults = {
        "reference_month": date(2026, 1, 1),
        "amount_paid": Decimal("1000.00"),
        "payment_date": date(2026, 1, 5),
    }
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.RentPayment", lease=lease, **defaults)


def make_furniture(user=None, **kwargs):
    defaults = {"description": "Test Furniture"}
    if user:
        defaults["created_by"] = user
        defaults["updated_by"] = user
    defaults.update(kwargs)
    return baker.make("core.Furniture", **defaults)
```

- [ ] **Step 2: Migrate conftest.py fixtures**

In `tests/conftest.py`, replace `building_with_apartment` and `person_with_credit_card` fixtures:

```python
from tests.factories import make_building, make_apartment, make_person, make_credit_card

@pytest.fixture()
def building_with_apartment(admin_user):
    building = make_building(street_number=100, user=admin_user)
    apartment = make_apartment(building=building, number="101", user=admin_user)
    return {"building": building, "apartment": apartment}

@pytest.fixture()
def person_with_credit_card(admin_user):
    person = make_person(user=admin_user, name="Test Person")
    card = make_credit_card(person=person, user=admin_user)
    return {"person": person, "credit_card": card}
```

- [ ] **Step 3: Run ALL tests to verify no regressions**

```bash
python -m pytest tests/ -x --timeout=30
```

- [ ] **Step 4: Commit**

```bash
git add tests/factories.py tests/conftest.py
git commit -m "refactor(tests): add baker factory module with helpers for all core models

Centralized factory helpers for 15+ models with sensible defaults,
dependency handling, and unique CPF generation. Migrates conftest
fixtures as first consumers."
```

---

### Task 29: Migrate Unit Tests to Baker

**Context:** 5 critical unit test files with 216 total `objects.create()` calls. Files: `test_financial_dashboard_service.py` (91), `test_cash_flow_service.py` (36), `test_person_payment_schedule_service.py` (31), `test_serializers.py` (30), `test_property_lifecycle.py` (28).

**Files:**
- Modify: `tests/unit/test_financial/test_financial_dashboard_service.py`
- Modify: `tests/unit/test_financial/test_cash_flow_service.py`
- Modify: `tests/unit/test_financial/test_person_payment_schedule_service.py`
- Modify: `tests/unit/test_serializers.py`
- Modify: `tests/e2e/test_property_lifecycle.py`

- [ ] **Step 1: Migrate test_financial_dashboard_service.py**

Replace manual `objects.create()` calls with factory helpers. For the `_create_expense_with_installments()` helper, keep it but use factories internally:

```python
from tests.factories import make_expense, make_expense_installment, make_person, make_expense_category

# Replace: Expense.objects.create(...) → make_expense(...)
# Replace: ExpenseInstallment.objects.create(...) → make_expense_installment(...)
# Keep: _create_expense_with_installments() helper but use factories inside it
```

- [ ] **Step 2: Run tests after each file migration**

```bash
python -m pytest tests/unit/test_financial/test_financial_dashboard_service.py -v
```

- [ ] **Step 3-6: Repeat for remaining 4 files**

Same pattern: import factories, replace creates, run tests after each file.

- [ ] **Step 7: Commit**

```bash
git add tests/unit/ tests/e2e/test_property_lifecycle.py
git commit -m "refactor(tests): migrate 5 critical unit test files to baker factories

Migrates 216 manual objects.create() calls to factory helpers in:
dashboard service, cash flow, payment schedule, serializers, and
property lifecycle tests."
```

---

### Task 30: Migrate Integration + Remaining Tests to Baker

**Context:** 38 remaining test files with ~343 `objects.create()` calls. Migrate in batches by directory.

**Files:**
- Modify: All files in `tests/integration/`
- Modify: Remaining files in `tests/unit/`
- Modify: Remaining files in `tests/e2e/`

- [ ] **Step 1: Migrate integration tests (batch 1: 10 files)**

Files: `test_expense_api.py`, `test_income_payment_api.py`, `test_financial_views_extended.py`, `test_financial_crud_gaps.py`, `test_core_views.py`, `test_lease_crud.py`, `test_lease_actions.py`, `test_tenant_api.py`, `test_financial_api_simple.py`, `test_financial_dashboard_api.py`.

For each file: import factories, replace `objects.create()`, run tests.

- [ ] **Step 2: Run all integration tests**

```bash
python -m pytest tests/integration/ -v --timeout=30
```

- [ ] **Step 3: Migrate remaining unit tests (batch 2: ~15 files)**

Files: `test_signals.py`, `test_models.py`, `test_daily_control_service.py`, `test_gap_fixes.py`, `test_contract_service.py`, `test_dashboard_service.py`, `test_notification_service.py`, `test_lease_service.py`, and remaining smaller files.

- [ ] **Step 4: Migrate e2e tests**

Files: `test_financial_workflow.py`, `test_financial_lifecycle.py`.

- [ ] **Step 5: Run ALL tests — full suite**

```bash
python -m pytest tests/ --timeout=30
```

Expected: ALL PASS

- [ ] **Step 6: Verify zero remaining manual creates**

```bash
grep -rn "objects\.create(" tests/ --include="*.py" | grep -v "factories.py" | grep -v "conftest.py" | wc -l
```

Target: 0 (or only intentional edge-case creates in model validation tests)

- [ ] **Step 7: Commit**

```bash
git add tests/
git commit -m "refactor(tests): complete baker migration — all test files use factory helpers

Migrates remaining 343 objects.create() calls across 38 test files.
All test data now created via tests/factories.py for maintainability."
```

---

## Self-Review Checklist

### 1. Spec coverage
- [x] Auth register/logout endpoints (Task 1) — CRITICAL fix
- [x] Security headers (Task 2) — CRITICAL fix
- [x] ExpenseViewSet.rebuild refactor (Task 3) — HIGH architecture fix
- [x] Axios timeout (Task 4) — HIGH reliability fix
- [x] DB connection pooling (Task 5) — HIGH performance fix
- [x] Serializer full_clean (Task 6) — HIGH data integrity fix
- [x] Signal race condition (Task 7) — HIGH data integrity fix
- [x] Missing indexes (Task 8) — MEDIUM performance fix
- [x] Duplicated date helpers (Task 9) — MEDIUM DRY fix
- [x] Expense form refactor (Task 10) — HIGH maintainability fix
- [x] Leases page refactor (Task 11) — HIGH maintainability fix
- [x] Query key standardization (Task 12) — MEDIUM consistency fix
- [x] Component tests (Task 13) — HIGH test coverage gap
- [x] Dead code removal (Task 14) — LOW cleanup
- [x] Dashboard widget wrapper (Task 15) — MEDIUM consistency fix
- [x] Test factory migration (Task 16) — HIGH test maintainability fix
- [x] HttpOnly cookie backend (Task 17) — CRITICAL security fix
- [x] HttpOnly cookie frontend (Task 18) — CRITICAL security fix
- [x] OAuth cookie flow (Task 19) — CRITICAL security fix
- [x] Tenant auth + layout (Task 20) — HIGH missing feature
- [x] Tenant dashboard + profile (Task 21) — HIGH missing feature
- [x] Tenant payments + PIX (Task 22) — HIGH missing feature
- [x] Tenant proof + notifications + contract (Task 23) — HIGH missing feature
- [x] P0 form modal tests (Task 24) — HIGH test coverage
- [x] P1 dashboard widget tests (Task 25) — HIGH test coverage
- [x] P2 layout + auth-gated tests (Task 26) — MEDIUM test coverage
- [x] P3 utility component tests (Task 27) — LOW test coverage
- [x] Baker factory module (Task 28) — HIGH test maintainability
- [x] Migrate unit tests to baker (Task 29) — HIGH test maintainability
- [x] Migrate integration + e2e tests to baker (Task 30) — HIGH test maintainability

### 2. Items NOT included (by design)
- **Furniture standalone page**: Feature request, not a fix from audit.
- **Nullable vs Optional schema standardization**: Cross-cutting change requiring careful per-schema analysis. Can be done incrementally.

### 3. Type/name consistency check
- `ExpenseService` — used consistently in Task 3 (service + viewset + test)
- `useLeaseModals` — used consistently in Task 11 (hook + page)
- `DashboardWidgetWrapper` — used consistently in Task 15 (component + consumer)
- `expense-type-config.ts` — used consistently in Task 10 (config + schema + form)
- `queryKeys.adminUsers` — used consistently in Task 12 (keys + hook)
- `make_expense` / `make_building` / `make_apartment` — used consistently in Task 16 (conftest + test)
- `CookieJWTAuthentication` — used consistently in Tasks 17-19 (auth class + settings + views)
- `TenantPortalLayout` — used consistently in Tasks 20-23 (layout + all tenant pages)
- `tests/factories.py` — used consistently in Tasks 28-30 (factory module + all test migrations)
