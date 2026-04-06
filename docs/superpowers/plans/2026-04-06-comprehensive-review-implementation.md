# Comprehensive Application Review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 85 issues found across 8 review domains — security vulnerabilities, financial calculation bugs, performance bottlenecks, frontend pattern violations, and testing gaps.

**Architecture:** 10 tasks organized by functional domain with dependency graph. Each task is self-contained and independently verifiable. Backend fixes come first (foundation → correctness → performance), then frontend cleanup and features, then tests.

**Tech Stack:** Django 5.2, DRF, PostgreSQL 15, Redis, Celery, Next.js 14, React 18, TypeScript, TanStack Query, Zustand, Zod, Vitest, MSW, pytest

**Spec:** `docs/superpowers/specs/2026-04-06-comprehensive-application-review.md`

**Dependency Graph:**
```
Task 01 Foundation ──┬──→ Task 03 Financial ──→ Task 04 Financial Data ──┐
                     │                                                    ├──→ Task 09 Tests Backend
Task 05 Cache ───────┴──→ Task 06 Performance ───────────────────────────┘
Task 02 Security (independent) ──────────────────────────────────────────→ Task 09 Tests Backend
Task 07 Frontend Cleanup ──→ Task 08 Frontend Features ──────────────────→ Task 10 Tests Frontend
```

---

### Task 1: Foundation — Models, Mixins, Coding Standards

**Files:**
- Modify: `core/models.py:147-185` (SoftDeleteMixin), `core/models.py:469-472` (Tenant.save), `core/models.py:667-670` (Lease.save), `core/models.py:1076-1080` (Expense CheckConstraint), `core/models.py:1289-1290` (EmployeePayment.total_paid)
- Modify: `core/cache.py:30-45` (HAS_DJANGO_REDIS)
- Modify: `core/infrastructure/storage.py:22-30` (HAS_BOTO3)
- Modify: `core/services/template_management_service.py:10` (future annotations)
- Modify: `core/infrastructure/pdf_generator.py:16` (future annotations)

- [ ] **Step 1: Fix SoftDeleteMixin.delete() — add updated_at**

In `core/models.py`, find the `delete` method of `SoftDeleteMixin` (~line 170) and add `updated_at`:

```python
# Replace this line:
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
# With:
        self.updated_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
```

- [ ] **Step 2: Fix SoftDeleteMixin.restore() — add updated_at**

In the `restore` method (~line 185), add `updated_at`:

```python
# Replace this line:
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by"])
# With:
        self.updated_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_by", "updated_at"])
```

- [ ] **Step 3: Fix Tenant.save() and Lease.save() — guard full_clean with update_fields**

In `core/models.py` line 469-472, replace:

```python
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to enforce validation before persisting."""
        self.full_clean()
        super().save(*args, **kwargs)
```

With:

```python
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to enforce validation before persisting."""
        if not kwargs.get("update_fields"):
            self.full_clean()
        super().save(*args, **kwargs)
```

Apply the **exact same change** to `Lease.save()` at line 667-670.

- [ ] **Step 4: Fix Expense CheckConstraint — total_amount__gt=0**

In `core/models.py` ~line 1076, replace:

```python
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="expense_total_amount_non_negative",
            ),
```

With:

```python
            models.CheckConstraint(
                check=models.Q(total_amount__gt=0),
                name="expense_total_amount_positive",
            ),
```

Create the migration:

```bash
python manage.py makemigrations core -n fix_expense_check_constraint
```

- [ ] **Step 5: Fix EmployeePayment.total_paid — subtract rent_offset**

In `core/models.py` ~line 1289, replace:

```python
    @property
    def total_paid(self) -> Decimal:
        return self.base_salary + self.variable_amount
```

With:

```python
    @property
    def total_paid(self) -> Decimal:
        return self.base_salary + self.variable_amount - self.rent_offset
```

- [ ] **Step 6: Remove HAS_DJANGO_REDIS pattern from cache.py**

In `core/cache.py` lines 30-38, replace:

```python
try:
    from django_redis import get_redis_connection

    HAS_DJANGO_REDIS = True
except ImportError:
    HAS_DJANGO_REDIS = False
```

With:

```python
from django_redis import get_redis_connection
```

Then search the file for all uses of `HAS_DJANGO_REDIS` and `_is_redis_backend()`. The `_is_redis_backend()` function should check only the CACHES backend string, not the flag:

```python
def _is_redis_backend() -> bool:
    """Check if the default cache backend is Redis."""
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    return "redis" in backend.lower()
```

- [ ] **Step 7: Remove HAS_BOTO3 pattern from storage.py**

In `core/infrastructure/storage.py` lines 22-30, replace:

```python
# Try to import boto3 for S3 support (optional dependency)
try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    HAS_BOTO3 = False
```

With:

```python
import boto3
```

Search for `HAS_BOTO3` in the file and remove any conditional checks — the import is now unconditional.

- [ ] **Step 8: Remove `from __future__ import annotations`**

Delete line 10 from `core/services/template_management_service.py`:
```python
from __future__ import annotations
```

Delete line 16 from `core/infrastructure/pdf_generator.py`:
```python
from __future__ import annotations
```

Check if any type hints in those files use string forward references that depended on this import. If any `"ClassName"` style hints exist, convert them to direct imports.

- [ ] **Step 9: Run verification**

```bash
cd c:/Users/alvar/git/personal/gerenciador_condominios
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/unit/ -x --tb=short -q
```

Fix any issues before proceeding.

- [ ] **Step 10: Commit**

```bash
git add core/models.py core/cache.py core/infrastructure/storage.py core/services/template_management_service.py core/infrastructure/pdf_generator.py
git commit -m "fix(core): foundation fixes — mixins, constraints, imports, coding standards"
```

If a migration was created in Step 4, include it:
```bash
git add core/migrations/
```

---

### Task 2: Security — OAuth, Permissions, Middleware

**Files:**
- Create: `core/models.py` (add OAuthExchangeCode model)
- Modify: `core/auth.py` (OAuth flow, link_oauth_account, oauth_status)
- Modify: `core/views.py:493-519` (terminate/transfer permissions)
- Modify: `core/views.py:635` (remove activate_pending_adjustments from GET)
- Modify: `condominios_manager/settings.py:63-76` (MIDDLEWARE order)
- Modify: `condominios_manager/urls.py:45` (schema endpoint)
- Modify: `core/serializers.py` (PaymentProofSerializer validate_file)
- Modify: `core/viewsets/auth_views.py` (verify_code lockout)
- Modify: `frontend/lib/api/hooks/use-auth.ts` (remove cookie token, update OAuth callback)
- Modify: `frontend/store/auth-store.ts` (token single source)
- Modify: `frontend/lib/api/client.ts` (read from Zustand)

- [ ] **Step 1: Fix MIDDLEWARE order**

In `condominios_manager/settings.py`, replace:

```python
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.RequestResponseLoggingMiddleware",  # Request/response logging
    "django.middleware.security.SecurityMiddleware",
```

With:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.RequestResponseLoggingMiddleware",  # Request/response logging
```

- [ ] **Step 2: Protect OpenAPI schema endpoint**

In `condominios_manager/urls.py`, move the schema line inside the existing `if settings.DEBUG` block. Remove:

```python
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
```

And add it to the existing DEBUG block:

```python
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
```

- [ ] **Step 3: Fix terminate/transfer inline permission checks**

In `core/views.py`, replace the `terminate` action (~line 493):

```python
    @action(detail=True, methods=["post"], url_path="terminate")
    def terminate(self, request: Request, pk: int | None = None) -> Response:
        """Terminate a lease contract."""
        if not request.user.is_staff:
            return Response(
                {"detail": "Apenas administradores podem encerrar contratos."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lease = self.get_object()
        terminate_lease(lease.id, request.user)
        return Response({"detail": "Contrato encerrado com sucesso."}, status=status.HTTP_200_OK)
```

With:

```python
    @action(detail=True, methods=["post"], url_path="terminate", permission_classes=[IsAdminUser])
    def terminate(self, request: Request, pk: int | None = None) -> Response:
        """Terminate a lease contract."""
        lease = self.get_object()
        terminate_lease(lease.id, request.user)
        return Response({"detail": "Contrato encerrado com sucesso."}, status=status.HTTP_200_OK)
```

Replace the `transfer` action (~line 506):

```python
    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request: Request, pk: int | None = None) -> Response:
        """Transfer a lease to a new apartment."""
        if not request.user.is_staff:
            return Response(
                {"detail": "Apenas administradores podem transferir contratos."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lease = self.get_object()
```

With:

```python
    @action(detail=True, methods=["post"], url_path="transfer", permission_classes=[IsAdminUser])
    def transfer(self, request: Request, pk: int | None = None) -> Response:
        """Transfer a lease to a new apartment."""
        lease = self.get_object()
```

Ensure `IsAdminUser` is imported from `rest_framework.permissions`.

- [ ] **Step 4: Remove activate_pending_adjustments from GET financial_summary**

In `core/views.py` ~line 635, remove:

```python
        # Activate any pending rent adjustments whose month has arrived
        RentAdjustmentService.activate_pending_adjustments()
```

- [ ] **Step 5: Create POST endpoint for activate_pending_adjustments**

Add a new action to the appropriate viewset (or create a new one) in `core/views.py`:

```python
class RentAdjustmentViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["post"], url_path="activate")
    def activate_pending(self, request: Request) -> Response:
        """Activate rent adjustments whose effective month has arrived."""
        result = RentAdjustmentService.activate_pending_adjustments()
        return Response(result, status=status.HTTP_200_OK)
```

Register in `core/urls.py`:

```python
router.register(r"rent-adjustments", RentAdjustmentViewSet, basename="rent-adjustments")
```

- [ ] **Step 6: Add OAuthExchangeCode model**

In `core/models.py`, add after the imports:

```python
import uuid

class OAuthExchangeCode(models.Model):
    """One-time code for OAuth token exchange. Expires in 60 seconds."""
    code = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "core_oauth_exchange_code"

    def is_valid(self) -> bool:
        """Check if the code is unused and not expired (60s TTL)."""
        if self.is_used:
            return False
        elapsed = (timezone.now() - self.created_at).total_seconds()
        return elapsed <= 60
```

Create migration:
```bash
python manage.py makemigrations core -n add_oauth_exchange_code
```

- [ ] **Step 7: Rewrite OAuth callback to use one-time code**

In `core/auth.py`, replace the `handle_callback` method's try block. Replace:

```python
            params = {
                "access_token": tokens["access"],
                "refresh_token": tokens["refresh"],
                "user_id": user_info["id"],
                "username": user_info["username"],
                "email": user_info["email"],
                "is_staff": user_info["is_staff"],
                "is_superuser": user_info["is_superuser"],
            }

            # Construct the full redirect URL
            redirect_url = (
                f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}?{urlencode(params)}"
            )

            return redirect(redirect_url)

        except Exception as e:
            logger.error(f"Error generating JWT tokens for OAuth user: {e!s}", exc_info=True)
            error_url = f"{settings.FRONTEND_URL}?error=token_generation_failed&message={e!s}"
            return redirect(error_url)
```

With:

```python
            # Create one-time exchange code
            exchange = OAuthExchangeCode.objects.create(
                user=request.user,
                access_token=str(tokens["access"]),
                refresh_token=str(tokens["refresh"]),
            )

            redirect_url = (
                f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}"
                f"?code={exchange.code}"
            )
            return redirect(redirect_url)

        except Exception:
            logger.exception("Error generating JWT tokens for OAuth user")
            error_url = f"{settings.FRONTEND_URL}?error=token_generation_failed"
            return redirect(error_url)
```

Add the import at the top: `from core.models import OAuthExchangeCode`

- [ ] **Step 8: Create exchange endpoint**

In `core/auth.py`, add:

```python
@api_view(["POST"])
@permission_classes([AllowAny])
def exchange_oauth_code(request: Request) -> JsonResponse:
    """Exchange a one-time OAuth code for JWT tokens."""
    code = request.data.get("code")
    if not code:
        return JsonResponse({"error": "Code is required"}, status=400)

    try:
        exchange = OAuthExchangeCode.objects.get(code=code)
    except (OAuthExchangeCode.DoesNotExist, ValueError):
        return JsonResponse({"error": "Invalid or expired code"}, status=400)

    if not exchange.is_valid():
        return JsonResponse({"error": "Invalid or expired code"}, status=400)

    exchange.is_used = True
    exchange.save(update_fields=["is_used"])

    user = exchange.user
    return JsonResponse({
        "access": exchange.access_token,
        "refresh": exchange.refresh_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    })
```

Register in `condominios_manager/urls.py`:
```python
    path("api/auth/oauth/exchange/", exchange_oauth_code, name="exchange_oauth_code"),
```

- [ ] **Step 9: Fix exception leak in auth.py**

In `link_oauth_account` (~line 211), replace:

```python
        return JsonResponse({"error": "Failed to link account", "message": str(e)}, status=500)
```

With:

```python
        return JsonResponse({"error": "Failed to link account"}, status=500)
```

- [ ] **Step 10: Protect link_oauth_account and oauth_status**

In `core/auth.py`, change `link_oauth_account`:

```python
@api_view(["POST"])
@permission_classes([AllowAny])
def link_oauth_account(request: Request) -> JsonResponse:
```

To:

```python
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def link_oauth_account(request: Request) -> JsonResponse:
```

Change `oauth_status`:

```python
@api_view(["GET"])
@permission_classes([AllowAny])
def oauth_status(request: Request) -> JsonResponse:
```

To:

```python
@api_view(["GET"])
@permission_classes([IsAdminUser])
def oauth_status(request: Request) -> JsonResponse:
```

Add imports: `from rest_framework.permissions import IsAuthenticated, IsAdminUser`

- [ ] **Step 11: Add PaymentProof file validation**

In `core/serializers.py`, add to `PaymentProofSerializer`:

```python
class PaymentProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = [...]
        read_only_fields = [...]

    def validate_file(self, value: Any) -> Any:
        max_size = 10 * 1024 * 1024  # 10MB
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if value.size > max_size:
            raise serializers.ValidationError("Arquivo excede o tamanho máximo de 10MB.")
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Tipo de arquivo não permitido. Use JPEG, PNG ou PDF."
            )
        return value
```

- [ ] **Step 12: Add OTP verify_code lockout**

In `core/viewsets/auth_views.py`, in the `verify_code` action, after retrieving the verification record and before checking the code, add:

```python
        verification = (
            WhatsAppVerification.objects.filter(cpf_cnpj=cpf_cnpj, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not verification:
            return Response({"error": "Nenhum código pendente"}, status=status.HTTP_404_NOT_FOUND)

        # Check lockout BEFORE verifying code
        if verification.attempts >= 3:
            return Response(
                {"error": "Código bloqueado por excesso de tentativas. Solicite um novo."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
```

- [ ] **Step 13: Fix frontend auth — remove token cookie, single source of truth**

In `frontend/lib/api/hooks/use-auth.ts`, in `useLogin` mutationFn, replace:

```typescript
      // Store tokens immediately so the next request is authenticated
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);
        document.cookie = `access_token=${tokens.access}; path=/; max-age=3600; SameSite=Lax`;
      }
```

With:

```typescript
      // Store tokens immediately so the next request is authenticated
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', tokens.access);
        localStorage.setItem('refresh_token', tokens.refresh);
        // Set auth flag cookie for Next.js middleware (no token value)
        document.cookie = 'is_authenticated=1; path=/; max-age=3600; SameSite=Lax';
      }
```

Search the entire frontend for any other `document.cookie = \`access_token=` and replace similarly.

- [ ] **Step 14: Run verification**

```bash
cd c:/Users/alvar/git/personal/gerenciador_condominios
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/unit/test_permissions.py tests/unit/test_auth.py -x --tb=short -q
cd frontend && npm run lint && npm run type-check
```

- [ ] **Step 15: Commit**

```bash
git add core/ condominios_manager/ frontend/lib/api/ frontend/store/
git commit -m "fix(security): OAuth code exchange, permission classes, middleware order, file validation"
```

---

### Task 3: Financial Correctness — Formulas, Serializers, Race Conditions

**Files:**
- Modify: `core/services/financial_dashboard_service.py:843` (double staticmethod)
- Modify: `core/viewsets/financial_dashboard_views.py:113` (unguarded int)
- Modify: `core/services/fee_calculator.py:72-77` (docstring)
- Modify: `core/serializers.py:863-894` (ExpenseSerializer.validate)
- Modify: `core/services/daily_control_service.py:274-291` (race condition)
- Modify: `core/views.py:453-461` (change_due_date)
- Modify: `core/models.py:1112-1119` (Expense.restore)

- [ ] **Step 1: Fix double @staticmethod**

In `core/services/financial_dashboard_service.py` ~line 843, find:

```python
    @staticmethod
    @staticmethod
    def _ensure_employee_payments(month_start: date) -> None:
```

Remove one `@staticmethod`:

```python
    @staticmethod
    def _ensure_employee_payments(month_start: date) -> None:
```

Search the entire file for other double `@staticmethod` occurrences:
```bash
rg -n "@staticmethod" core/services/financial_dashboard_service.py
```
Fix any duplicates found.

- [ ] **Step 2: Fix unguarded int() conversion**

In `core/viewsets/financial_dashboard_views.py` ~line 113, replace:

```python
        detail_id_str = request.query_params.get("id")
        detail_id = int(detail_id_str) if detail_id_str else None
```

With:

```python
        detail_id_str = request.query_params.get("id")
        detail_id: int | None = None
        if detail_id_str:
            try:
                detail_id = int(detail_id_str)
            except ValueError:
                return Response(
                    {"error": "Parâmetro 'id' deve ser um número inteiro."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
```

- [ ] **Step 3: Fix late fee docstring**

In `core/services/fee_calculator.py` lines 72-77, replace the example:

```python
            >>> result = service.calculate_late_fee(Decimal("1500.00"), 10, date(2025, 1, 15))
            >>> result["late_days"]
            5
            >>> result["late_fee"]
            Decimal('375.00')  # (1500/30) × 5 × 1.05
```

With:

```python
            >>> result = service.calculate_late_fee(Decimal("1500.00"), 10, date(2025, 1, 15))
            >>> result["late_days"]
            5
            >>> result["late_fee"]
            Decimal('12.50')  # (1500/30) × 5 × 0.05
```

Also check `docs/LESSONS_LEARNED.md` and `CLAUDE.md` for references to "R$375" or "1.05" and fix them.

- [ ] **Step 4: Fix ExpenseSerializer.validate for partial updates**

In `core/serializers.py`, replace the `validate` method of `ExpenseSerializer` (~line 863):

```python
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        expense_type = attrs.get("expense_type", "")

        if expense_type == "card_purchase" and not attrs.get("credit_card"):
```

With:

```python
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)

        # For partial updates, fall back to instance values for cross-field validation
        expense_type = attrs.get("expense_type")
        if expense_type is None and self.instance:
            expense_type = self.instance.expense_type
        expense_type = expense_type or ""

        credit_card = attrs.get("credit_card")
        if credit_card is None and "credit_card" not in attrs and self.instance:
            credit_card = self.instance.credit_card

        person = attrs.get("person")
        if person is None and "person" not in attrs and self.instance:
            person = self.instance.person

        building = attrs.get("building")
        if building is None and "building" not in attrs and self.instance:
            building = self.instance.building

        if expense_type == "card_purchase" and not credit_card:
```

Then update all subsequent checks to use the resolved local variables instead of `attrs.get(...)`:
- `attrs.get("credit_card")` → `credit_card`
- `attrs.get("person")` → `person`
- `attrs.get("building")` → `building`

Leave `attrs.get("is_installment")`, `attrs.get("total_installments")`, etc. as-is since those are self-contained.

- [ ] **Step 5: Fix credit card bulk-pay race condition**

In `core/services/daily_control_service.py`, replace the `_mark_credit_card_paid` function (~line 274):

```python
def _mark_credit_card_paid(card_id: int, payment_date: date) -> dict[str, Any]:
    """Mark all unpaid installments for a credit card in the current month as paid."""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    next_month = _next_month_start(today.year, today.month)

    unpaid = ExpenseInstallment.objects.filter(
        expense__credit_card_id=card_id,
        expense__is_offset=False,
        due_date__gte=month_start,
        due_date__lt=next_month,
        is_paid=False,
    )

    count = unpaid.update(is_paid=True, paid_date=payment_date)
```

With:

```python
def _mark_credit_card_paid(card_id: int, payment_date: date) -> dict[str, Any]:
    """Mark all unpaid installments for a credit card in the current month as paid."""
    today = timezone.now().date()
    month_start = today.replace(day=1)
    next_month = _next_month_start(today.year, today.month)

    with transaction.atomic():
        unpaid = (
            ExpenseInstallment.objects.select_for_update()
            .filter(
                expense__credit_card_id=card_id,
                expense__is_offset=False,
                due_date__gte=month_start,
                due_date__lt=next_month,
                is_paid=False,
            )
        )
        count = unpaid.update(is_paid=True, paid_date=payment_date)
```

Add import at top: `from django.db import transaction`

- [ ] **Step 6: Move change_due_date business logic to service**

First, create or extend a lease service. Check if `core/services/lease_service.py` exists:

```bash
ls core/services/lease_service.py 2>/dev/null || echo "does not exist"
```

Add a function (in the appropriate service file):

```python
def change_tenant_due_day(tenant: "Tenant", new_due_day: int) -> None:
    """Update a tenant's rent due day with validation."""
    tenant.due_day = new_due_day
    tenant.full_clean()
    tenant.updated_at = timezone.now()
    tenant.save(update_fields=["due_day", "updated_at"])
```

In `core/views.py` ~line 457, replace:

```python
            tenant = lease.responsible_tenant
            tenant.due_day = new_due_day
            tenant.save(update_fields=["due_day"])
```

With:

```python
            tenant = lease.responsible_tenant
            change_tenant_due_day(tenant, new_due_day)
```

Add the import at the top of `views.py`.

- [ ] **Step 7: Fix Expense.restore() — only restore cascade-deleted installments**

In `core/models.py`, replace the `Expense.restore` method (~line 1112):

```python
    def restore(self, restored_by: Any = None) -> None:
        super().restore(restored_by=restored_by)
        # Cascade restore to child installments
        self.installments.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )
```

With:

```python
    def restore(self, restored_by: Any = None) -> None:
        original_deleted_at = self.deleted_at
        super().restore(restored_by=restored_by)
        # Only restore installments that were cascade-deleted with this expense (within 2s window)
        if original_deleted_at:
            from datetime import timedelta

            window = timedelta(seconds=2)
            self.installments.filter(
                is_deleted=True,
                deleted_at__gte=original_deleted_at - window,
                deleted_at__lte=original_deleted_at + window,
            ).update(
                is_deleted=False,
                deleted_at=None,
                deleted_by=None,
            )
```

- [ ] **Step 8: Run verification**

```bash
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/unit/test_financial/ tests/unit/test_fee_calculator.py tests/integration/test_expense_api.py -x --tb=short -q
```

- [ ] **Step 9: Commit**

```bash
git add core/
git commit -m "fix(financial): calculation correctness — race condition, partial update, restore cascade"
```

---

### Task 4: Financial Data — Cash Flow, Dashboard Service, Filtering

**Files:**
- Modify: `core/services/cash_flow_service.py:688-693` (projected stipends)
- Modify: `core/services/cash_flow_service.py:817-830` (person summary stipends)
- Modify: `core/services/cash_flow_service.py:157-183` (owner repayments)
- Modify: `core/services/cash_flow_service.py:680` (projected owner repayments)
- Modify: `core/services/cash_flow_service.py:696-704` (double counting)
- Modify: `core/services/financial_dashboard_service.py:327-360` (category breakdown)

- [ ] **Step 1: Fix projected stipends — add date filtering**

In `core/services/cash_flow_service.py` ~line 688, replace:

```python
        stipend_total: Decimal = PersonIncome.objects.filter(
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
            fixed_amount__isnull=False,
        ).aggregate(total=Coalesce(Sum("fixed_amount"), Decimal("0.00")))["total"]
```

With:

```python
        stipend_total: Decimal = (
            PersonIncome.objects.filter(
                income_type=PersonIncomeType.FIXED_STIPEND,
                is_active=True,
                fixed_amount__isnull=False,
                start_date__lte=month_start,
            )
            .exclude(end_date__lt=month_start)
            .aggregate(total=Coalesce(Sum("fixed_amount"), Decimal("0.00")))["total"]
        )
```

- [ ] **Step 2: Fix person summary stipends — add date filtering**

In `core/services/cash_flow_service.py` ~line 820, find the stipend query in `get_person_summary`:

```python
        stipends = PersonIncome.objects.filter(
            person=person,
            income_type=PersonIncomeType.FIXED_STIPEND,
            is_active=True,
        )
```

Replace with:

```python
        stipends = (
            PersonIncome.objects.filter(
                person=person,
                income_type=PersonIncomeType.FIXED_STIPEND,
                is_active=True,
                start_date__lte=month_start,
            )
            .exclude(end_date__lt=month_start)
        )
```

- [ ] **Step 3: Fix owner repayments — add prepaid/salary_offset exclusions**

In `core/services/cash_flow_service.py` ~line 160, in `_collect_owner_repayments`, replace:

```python
        owner_leases = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=False,
            )
            .filter(start_date__lte=month_start)
            .select_related("apartment", "apartment__owner", "apartment__building")
        )
```

With:

```python
        owner_leases = (
            Lease.objects.filter(
                apartment__is_rented=True,
                apartment__owner__isnull=False,
                start_date__lte=month_start,
            )
            .exclude(prepaid_until__gte=month_start)
            .exclude(is_salary_offset=True)
            .select_related("apartment", "apartment__owner", "apartment__building")
        )
```

Apply the same exclusions in the projected version (~line 680):

```python
        owner_leases = Lease.objects.filter(
            apartment__is_rented=True,
            apartment__owner__isnull=False,
        )
```

Add `.exclude(prepaid_until__gte=month_start).exclude(is_salary_offset=True)` to this query as well.

- [ ] **Step 4: Fix projected expenses double-counting**

In `core/services/cash_flow_service.py`, find `_get_projected_utility_average` method and add `is_debt_installment=False` to exclude debts already counted in installments:

Find the filter in the method (search for `WATER_BILL` or `ELECTRICITY_BILL`) and add:

```python
            is_debt_installment=False,
```

to the `.filter(...)` call.

- [ ] **Step 5: Fix category breakdown — split direct vs installment expenses**

In `core/services/financial_dashboard_service.py`, replace the `get_expense_category_breakdown` method's main query (~line 330):

```python
        expenses_in_month = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            is_offset=False,
        )

        # Get grand total for percentage calculation
        grand_total = expenses_in_month.aggregate(
            total=Coalesce(Sum("total_amount"), Decimal("0.00"))
        )["total"]
```

With:

```python
        # Direct expenses (no installments) by expense_date
        direct_total: Decimal = Expense.objects.filter(
            expense_date__gte=month_start,
            expense_date__lt=next_month,
            is_offset=False,
            is_installment=False,
        ).aggregate(total=Coalesce(Sum("total_amount"), Decimal("0.00")))["total"]

        # Installment expenses by installment due_date
        installment_total: Decimal = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            expense__is_offset=False,
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

        grand_total = direct_total + installment_total
```

Then update the category grouping to combine both sources. Replace the `category_data` query with:

```python
        # Direct expenses by category
        direct_by_category = (
            Expense.objects.filter(
                expense_date__gte=month_start,
                expense_date__lt=next_month,
                is_offset=False,
                is_installment=False,
            )
            .values("category__id", "category__name", "category__color")
            .annotate(total=Sum("total_amount"), count=Count("id"))
        )

        # Installment expenses by category
        installment_by_category = (
            ExpenseInstallment.objects.filter(
                due_date__gte=month_start,
                due_date__lt=next_month,
                expense__is_offset=False,
            )
            .values(
                "expense__category__id",
                "expense__category__name",
                "expense__category__color",
            )
            .annotate(total=Sum("amount"), count=Count("id"))
        )

        # Merge results by category
        merged: dict[int | None, dict[str, Any]] = {}
        for item in direct_by_category:
            cid = item["category__id"]
            merged[cid] = {
                "id": cid,
                "name": item["category__name"] or "Sem Categoria",
                "color": item["category__color"] or "#6B7280",
                "total": item["total"],
                "count": item["count"],
            }

        for item in installment_by_category:
            cid = item["expense__category__id"]
            if cid in merged:
                merged[cid]["total"] += item["total"]
                merged[cid]["count"] += item["count"]
            else:
                merged[cid] = {
                    "id": cid,
                    "name": item["expense__category__name"] or "Sem Categoria",
                    "color": item["expense__category__color"] or "#6B7280",
                    "total": item["total"],
                    "count": item["count"],
                }

        category_data = sorted(merged.values(), key=lambda x: x["total"], reverse=True)
```

Update the loop below to use `category_data` (which is now a list of dicts) instead of the queryset. Adapt the field access from `item["category__id"]` to `item["id"]`, etc.

- [ ] **Step 6: Run verification**

```bash
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/unit/test_financial/test_cash_flow_service.py tests/unit/test_financial/test_financial_dashboard_service.py -x --tb=short -q
```

- [ ] **Step 7: Commit**

```bash
git add core/services/
git commit -m "fix(financial): cash flow data correctness — stipend filtering, owner exclusions, category breakdown"
```

---

### Task 5: Cache & Infrastructure

**Files:**
- Modify: `core/cache.py:150-175` (sentinel), `core/cache.py:240-253` (SCAN)
- Modify: `core/services/financial_dashboard_service.py` (cache keys with date params)
- Modify: `core/services/cash_flow_service.py` (cache projection)
- Modify: `core/services/dashboard_service.py` (add @cache_result)
- Modify: `core/viewsets/financial_dashboard_views.py` (pass year/month)

- [ ] **Step 1: Fix cache_result — use sentinel for None**

In `core/cache.py`, add at module level (after imports):

```python
_SENTINEL = object()
```

In the `cache_result` decorator (~line 158), replace:

```python
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cast(T, cached_value)
```

With:

```python
            cached_value = cache.get(cache_key, _SENTINEL)
            if cached_value is not _SENTINEL:
                logger.debug(f"Cache HIT: {cache_key}")
                return cast(T, cached_value)
```

- [ ] **Step 2: Replace Redis KEYS with SCAN**

In `core/cache.py`, replace `invalidate_pattern` (~line 240):

```python
        try:
            redis_client = get_redis_connection("default")
            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "condominios")
            full_pattern = f"{key_prefix}:1:{pattern}"
            keys = redis_client.keys(full_pattern)
        except Exception:
            logger.exception(f"Error invalidating cache pattern {pattern}")
            return 0
        else:
            if keys:
                count: int = cast(int, redis_client.delete(*keys))
                logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
                return count
            logger.debug(f"No cache keys found matching pattern: {pattern}")
            return 0
```

With:

```python
        try:
            redis_client = get_redis_connection("default")
            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "condominios")
            full_pattern = f"{key_prefix}:1:{pattern}"
            count = 0
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    count += len(keys)
                    redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            logger.exception(f"Error invalidating cache pattern {pattern}")
            return 0
        else:
            if count > 0:
                logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")
            return count
```

- [ ] **Step 3: Add year/month params to FinancialDashboardService methods**

For each method that calls `timezone.now()` internally, add optional `year`/`month` params. Example for `get_overview`:

```python
    @staticmethod
    @cache_result(timeout=120, key_prefix="financial-dashboard-overview")
    def get_overview(year: int | None = None, month: int | None = None) -> dict[str, Any]:
        today = timezone.now().date()
        year = year or today.year
        month = month or today.month
```

Apply same change to: `get_debt_by_person`, `get_debt_by_type`, `get_upcoming_installments`, `get_overdue_installments`, `get_dashboard_summary`.

Update callers in `core/viewsets/financial_dashboard_views.py` to pass `year=year, month=month`.

- [ ] **Step 4: Cache get_cash_flow_projection**

In `core/services/cash_flow_service.py`, find `get_cash_flow_projection` and add decorator:

```python
    @staticmethod
    @cache_result(timeout=300, key_prefix="cash-flow-projection")
    def get_cash_flow_projection(months: int = 12) -> list[dict[str, Any]]:
```

Add import: `from core.cache import cache_result`

- [ ] **Step 5: Add @cache_result to DashboardService methods**

In `core/services/dashboard_service.py`, add decorator to each method:

```python
    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-financial-summary")
    def get_financial_summary() -> dict[str, Any]:

    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-lease-metrics")
    def get_lease_metrics() -> dict[str, Any]:

    @staticmethod
    @cache_result(timeout=120, key_prefix="dashboard-late-payment")
    def get_late_payment_summary() -> dict[str, Any]:

    @staticmethod
    @cache_result(timeout=300, key_prefix="dashboard-tenant-stats")
    def get_tenant_statistics() -> dict[str, Any]:

    @staticmethod
    @cache_result(timeout=300, key_prefix="dashboard-building-stats")
    def get_building_statistics() -> dict[str, Any]:
```

Add import: `from core.cache import cache_result`

Add signal-based invalidation in `core/signals.py` for the models Lease, Apartment, Building, Tenant (if not already present for dashboard keys).

- [ ] **Step 6: Fix FinancialSettings.objects.first() in loop**

In `core/services/financial_dashboard_service.py`, find `_build_overdue_previous_months` or `_get_person_waterfall`. Fetch settings once before the loop and pass as parameter:

```python
# Before the loop:
financial_settings = FinancialSettings.objects.first()

# In the loop, pass settings:
waterfall = cls._get_person_waterfall(person, months, settings=financial_settings)
```

Update `_get_person_waterfall` signature to accept optional `settings` param.

- [ ] **Step 7: Run verification**

```bash
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/unit/ -x --tb=short -q
```

- [ ] **Step 8: Commit**

```bash
git add core/
git commit -m "perf(cache): sentinel for None, SCAN instead of KEYS, cache dashboard methods"
```

---

### Task 6: Performance — Queries, N+1, Async PDF

**Files:**
- Modify: `core/services/dashboard_service.py:183-195` (lease metrics)
- Modify: `core/services/financial_dashboard_service.py:138-195` (debt by person)
- Modify: `core/services/financial_dashboard_service.py:491-612` (calc person expenses)
- Modify: `core/services/dashboard_service.py:304-368` (late payment summary)
- Create: `core/tasks.py` (Celery task for PDF)
- Modify: `core/views.py` (generate_contract → async)
- Modify: `condominios_manager/settings_production.py:233` (CONN_MAX_AGE)
- Modify: `frontend/lib/api/hooks/use-dashboard.ts` (refetchInterval)
- Modify: `frontend/lib/config/query-client.ts` (refetchOnWindowFocus)

- [ ] **Step 1: Fix get_lease_metrics — DB annotation instead of Python loop**

In `core/services/dashboard_service.py`, replace the Python loop in `get_lease_metrics` (~line 185-195):

```python
        lease_dates = Lease.objects.values("start_date", "validity_months")

        expiring_soon = 0
        expired_leases = 0

        for lease_data in lease_dates:
            final_date = lease_data["start_date"] + timedelta(
                days=lease_data["validity_months"] * 30
            )
            if final_date < today:
                expired_leases += 1
            elif final_date <= expiry_threshold:
                expiring_soon += 1
```

With:

```python
        from django.db.models import DateField
        from django.db.models.expressions import RawSQL

        annotated = Lease.objects.annotate(
            end_date=RawSQL(
                "(start_date + (validity_months || ' months')::interval)::date",
                [],
                output_field=DateField(),
            ),
        )

        counts = annotated.aggregate(
            expiring_soon=Count("id", filter=Q(end_date__gte=today, end_date__lte=expiry_threshold)),
            expired_leases=Count("id", filter=Q(end_date__lt=today)),
        )

        expiring_soon = counts["expiring_soon"]
        expired_leases = counts["expired_leases"]
```

Add imports: `from django.db.models import Count, Q, DateField` and `from django.db.models.expressions import RawSQL`

- [ ] **Step 2: Fix get_debt_by_person — single grouped query**

In `core/services/financial_dashboard_service.py`, replace the full `get_debt_by_person` method body (the for-loop with 5 queries per person) with a single grouped query. See spec section 6.2 for the exact replacement code using `values("expense__person_id").annotate(...)` with conditional `Sum(filter=Q(...))`.

- [ ] **Step 3: Consolidate _calc_person_expense_total**

This is the largest refactor. Create a new method `_calc_all_person_expenses(person_ids, months)` that returns a `dict[(person_id, month_start), Decimal]` using 2 grouped queries. Refactor `_build_overdue_previous_months` to call it once. See spec section 6.3 for the approach.

- [ ] **Step 4: Remove CONN_MAX_AGE at module level**

In `condominios_manager/settings_production.py` ~line 233, delete:

```python
CONN_MAX_AGE = 600
```

Keep only line 103: `DATABASES["default"]["CONN_MAX_AGE"] = 600`

- [ ] **Step 5: Create Celery task for PDF generation**

Create `core/tasks.py`:

```python
from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def generate_contract_pdf(self, lease_id: int) -> str:
    """Generate contract PDF asynchronously. Returns the file path."""
    from core.models import Lease
    from core.services.contract_service import ContractService

    lease = Lease.objects.select_related(
        "apartment", "apartment__building"
    ).get(id=lease_id)
    path = ContractService.generate_contract(lease)
    return str(path)
```

Modify `core/views.py` `generate_contract` action to return 202:

```python
    @action(detail=True, methods=["post"], url_path="generate_contract", permission_classes=[IsAdminUser])
    def generate_contract(self, request: Request, pk: int | None = None) -> Response:
        lease = self.get_object()
        from core.tasks import generate_contract_pdf
        task = generate_contract_pdf.delay(lease.id)
        return Response(
            {"task_id": task.id, "status": "processing"},
            status=status.HTTP_202_ACCEPTED,
        )
```

Add a task status endpoint in `core/views.py`:

```python
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def task_status(request: Request, task_id: str) -> Response:
    from celery.result import AsyncResult
    result = AsyncResult(task_id)
    data = {"task_id": task_id, "status": result.status}
    if result.ready():
        if result.successful():
            data["result"] = result.result
        else:
            data["error"] = str(result.result)
    return Response(data)
```

Register: `path("api/tasks/<str:task_id>/status/", task_status, name="task_status")` in `urls.py`.

- [ ] **Step 6: Remove refetchInterval from dashboard hooks**

In `frontend/lib/api/hooks/use-dashboard.ts`, remove `refetchInterval: 1000 * 60 * 5` from:
- `useDashboardFinancialSummary`
- `useDashboardLeaseMetrics`
- `useDashboardBuildingStatistics`

Keep `refetchInterval` only in `useDashboardLatePayments`, but change to 10 minutes:

```typescript
    refetchInterval: 1000 * 60 * 10,
```

Do the same in `use-financial-dashboard.ts` — remove `refetchInterval` from all hooks.

- [ ] **Step 7: Enable refetchOnWindowFocus**

In `frontend/lib/config/query-client.ts`, change:

```typescript
      refetchOnWindowFocus: false,
```

To:

```typescript
      refetchOnWindowFocus: true,
```

- [ ] **Step 8: Run verification**

```bash
ruff check core/ && ruff format --check core/
mypy core/
python -m pytest tests/ -x --tb=short -q
cd frontend && npm run lint && npm run type-check
```

- [ ] **Step 9: Commit**

```bash
git add core/ condominios_manager/ frontend/
git commit -m "perf(queries): N+1 fixes, DB annotations, async PDF, remove excessive polling"
```

---

### Task 7: Frontend Cleanup — Dead Code, Patterns, Aliases

**Files:**
- Modify: 12 CRUD pages (toast.error in render)
- Modify: 4 files (raw query keys)
- Delete: `frontend/app/(dashboard)/tenants/_components/tenant-form-wizard.tsx`
- Modify: `frontend/lib/utils/formatters.ts` (remove aliases)
- Modify: 13+ files (console.error → handleError)
- Delete: `frontend/app/(dashboard)/financial-employees-temp/`
- Modify: `frontend/store/auth-store.ts` (dead actions)
- Modify: `frontend/lib/config/query-client.ts` (retry filter)
- Modify: 5 hooks (null id query key)
- Modify: `frontend/lib/api/hooks/use-auth.ts` (queryFn side effect)

- [ ] **Step 1: Fix toast.error in render → useEffect**

For each of these files, find the pattern `if (error) { toast.error(...); }` in the component body (NOT inside useEffect) and wrap it:

Files to check and fix:
1. `frontend/app/(dashboard)/buildings/page.tsx`
2. `frontend/app/(dashboard)/apartments/page.tsx`
3. `frontend/app/(dashboard)/tenants/page.tsx`
4. `frontend/app/(dashboard)/leases/page.tsx`
5. `frontend/app/(dashboard)/furniture/page.tsx`
6. `frontend/app/(dashboard)/financial/persons/page.tsx`
7. `frontend/app/(dashboard)/financial/incomes/page.tsx`
8. `frontend/app/(dashboard)/financial/employees/page.tsx`
9. `frontend/app/(dashboard)/financial/rent-payments/page.tsx`

For each, replace:
```typescript
  if (error) {
    toast.error('Erro ao carregar ...');
  }
```

With:
```typescript
  useEffect(() => {
    if (error) {
      toast.error('Erro ao carregar ...');
    }
  }, [error]);
```

Add `useEffect` to the imports if not already present. Run a search to find any other pages with this pattern:

```bash
cd frontend && grep -rn "if (error)" app/ --include="*.tsx" | grep "toast"
```

- [ ] **Step 2: Replace raw query keys**

Search for all raw string query keys:

```bash
cd frontend && grep -rn "invalidateQueries.*queryKey.*\['" --include="*.ts" --include="*.tsx"
```

Replace each with the appropriate `queryKeys.*` constant. Import `queryKeys` from `@/lib/api/query-keys`.

- [ ] **Step 3: Remove re-export barrel and aliases**

Search for consumers of `tenant-form-wizard`:
```bash
cd frontend && grep -rn "tenant-form-wizard" --include="*.ts" --include="*.tsx"
```

Update each import to use `./wizard` instead, then delete `tenant-form-wizard.tsx`.

Search for consumers of aliases:
```bash
cd frontend && grep -rn "formatCPFOrCNPJ\|formatBrazilianPhone" --include="*.ts" --include="*.tsx"
```

Replace `formatCPFOrCNPJ` → `formatCpfCnpj` and `formatBrazilianPhone` → `formatPhone` in each file, update imports.

Remove the aliases from `formatters.ts`.

- [ ] **Step 4: Replace console.error with handleError**

Search:
```bash
cd frontend && grep -rn "console\.error\|console\.warn\|console\.log" app/ lib/hooks/ --include="*.ts" --include="*.tsx"
```

Replace each `console.error('...', error)` with `handleError(error, 'Context')` from `@/lib/utils/error-handler`.

- [ ] **Step 5: Delete dead code**

```bash
rm -rf frontend/app/\(dashboard\)/financial-employees-temp/
```

- [ ] **Step 6: Remove dead Zustand actions**

Search for usage of `setTokens` and `setToken`:
```bash
cd frontend && grep -rn "setTokens\|setToken[^s]" --include="*.ts" --include="*.tsx"
```

If only used in store definition and test mocks, remove from `AuthState` interface and store implementation in `auth-store.ts`.

- [ ] **Step 7: Fix retry to filter 401/403**

In `frontend/lib/config/query-client.ts`, replace:

```typescript
      retry: 3,
```

With:

```typescript
      retry: (failureCount, error) => {
        if (
          error instanceof Error &&
          'response' in error &&
          [401, 403].includes((error as { response?: { status?: number } }).response?.status ?? 0)
        ) {
          return false;
        }
        return failureCount < 3;
      },
```

Import `AxiosError` from axios if available for cleaner typing.

- [ ] **Step 8: Fix null id query key fallback**

In each of these hooks, replace `queryKey: id ? queryKeys.X.detail(id) : queryKeys.X.all` with `queryKey: queryKeys.X.detail(id ?? 0)`:

- `frontend/lib/api/hooks/use-buildings.ts`
- `frontend/lib/api/hooks/use-leases.ts`
- `frontend/lib/api/hooks/use-expenses.ts`
- `frontend/lib/api/hooks/use-rent-payments.ts`
- `frontend/lib/api/hooks/use-persons.ts`

- [ ] **Step 9: Fix useCurrentUser — remove side effect, use placeholderData**

In `frontend/lib/api/hooks/use-auth.ts`, replace:

```typescript
  return useQuery({
    queryKey: queryKeys.currentUser.all,
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me/');
      setUser(data);
      return data;
    },
    enabled: Boolean(user),
    initialData: user ?? undefined,
  });
```

With:

```typescript
  return useQuery({
    queryKey: queryKeys.currentUser.all,
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me/');
      return data;
    },
    enabled: Boolean(user),
    placeholderData: user ?? undefined,
  });
```

Remove `setUser` from the hook (the import from auth store and the call).

- [ ] **Step 10: Run verification**

```bash
cd frontend && npm run lint && npm run type-check && npm run build
npm run test:unit -- --run
```

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "refactor(frontend): cleanup dead code, fix patterns, remove aliases and re-exports"
```

---

### Task 8: Frontend Features — Settings, Register, UI Fixes

**Files:**
- Create: `frontend/app/(dashboard)/settings/page.tsx`
- Create: `frontend/lib/schemas/settings.ts`
- Create: `frontend/lib/api/hooks/use-settings.ts`
- Create: `frontend/app/(dashboard)/admin/users/page.tsx`
- Create: `frontend/app/(dashboard)/admin/users/_components/user-form-modal.tsx`
- Create: `frontend/lib/api/hooks/use-users.ts`
- Create: `frontend/lib/schemas/user.ts`
- Create: `frontend/lib/hooks/use-unsaved-changes.ts`
- Create: `frontend/components/ui/confirm-discard-dialog.tsx`
- Create: `core/viewsets/user_admin_views.py` (backend for admin users)
- Modify: Multiple CRUD pages (inline error UI)
- Modify: Multiple form modals (dirty-state guard)
- Modify: Various UI fixes (formatCurrency, global-error, DataTable)

This task is large. It should be split into sub-commits:

- [ ] **Step 1: Create backend for user admin**

Create `core/viewsets/user_admin_views.py`:

```python
from django.contrib.auth.models import User
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response


class UserAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "is_staff", "is_active", "password", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminUser]
```

Create `core/viewsets/profile_views.py` for change password:

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request: Request) -> Response:
    user = request.user
    user.first_name = request.data.get("first_name", user.first_name)
    user.last_name = request.data.get("last_name", user.last_name)
    user.save(update_fields=["first_name", "last_name"])
    return Response({"detail": "Perfil atualizado."})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request: Request) -> Response:
    user = request.user
    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")

    if not user.check_password(old_password):
        return Response(
            {"error": "Senha atual incorreta."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(new_password) < 8:
        return Response(
            {"error": "Nova senha deve ter pelo menos 8 caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save()
    return Response({"detail": "Senha alterada com sucesso."})
```

Register in `core/urls.py`:

```python
router.register(r"admin/users", UserAdminViewSet, basename="admin-users")
```

And in `condominios_manager/urls.py`:
```python
    path("api/auth/me/update/", update_profile, name="update_profile"),
    path("api/auth/change-password/", change_password, name="change_password"),
```

- [ ] **Step 2: Create frontend /settings page**

Create Zod schema `frontend/lib/schemas/settings.ts`, hook `frontend/lib/api/hooks/use-settings.ts`, and page `frontend/app/(dashboard)/settings/page.tsx`. Follow existing patterns for form pages (e.g., look at how `financial/settings/page.tsx` is structured).

Fix header/sidebar links to point to `/settings`.

- [ ] **Step 3: Create frontend /admin/users page**

Create schema `frontend/lib/schemas/user.ts`, hook `frontend/lib/api/hooks/use-users.ts`, page `frontend/app/(dashboard)/admin/users/page.tsx`, and form modal. Follow existing DataTable + FormModal patterns.

Remove "Criar nova conta" button from `frontend/app/login/page.tsx`.

- [ ] **Step 4: Add inline error UI to CRUD pages**

Add this pattern to every CRUD page that currently only uses toast for errors:

```tsx
{error && !data && (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertTitle>Erro</AlertTitle>
    <AlertDescription>
      Erro ao carregar dados. Verifique sua conexão e tente novamente.
    </AlertDescription>
  </Alert>
)}
```

Import `Alert, AlertTitle, AlertDescription` from `@/components/ui/alert` and `AlertCircle` from `lucide-react`.

- [ ] **Step 5: Create useUnsavedChanges hook and ConfirmDiscardDialog**

Create `frontend/lib/hooks/use-unsaved-changes.ts` and `frontend/components/ui/confirm-discard-dialog.tsx` as described in the spec (section 8.4).

Apply to form modals — start with `building-form-modal.tsx` as the pattern, then replicate to others.

- [ ] **Step 6: Fix FinancialSummaryWidget formatCurrency**

In `frontend/app/(dashboard)/_components/financial-summary-widget.tsx`, replace manual formatting with `formatCurrency()` from `@/lib/utils/formatters`.

- [ ] **Step 7: Fix global-error.tsx**

Replace raw `<button>` with `<Button>` component. Replace `error.message` with generic message.

- [ ] **Step 8: Fix DataTable checkbox indeterminate**

In `frontend/components/tables/data-table.tsx`, replace:

```tsx
  className={someSelected ? 'opacity-50' : ''}
```

With:

```tsx
  checked={someSelected && !allSelected ? 'indeterminate' : allSelected}
```

Remove the `className` hack.

- [ ] **Step 9: Extract apiClient calls to hooks**

For each component that calls `apiClient` directly, create a `useMutation` hook in the appropriate hooks file and replace the manual `isSaving` state. See spec section 8.8 for the list of components.

- [ ] **Step 10: Extract EXPENSE_TYPES constant**

Add to `frontend/lib/utils/constants.ts` and import in both form modals. See spec section 8.9.

- [ ] **Step 11: Run verification**

```bash
cd c:/Users/alvar/git/personal/gerenciador_condominios
ruff check core/ && mypy core/
cd frontend && npm run lint && npm run type-check && npm run build
```

- [ ] **Step 12: Commit**

```bash
git add core/ frontend/
git commit -m "feat(ui): settings page, admin users, error states, dirty-state guards"
```

---

### Task 9: Testing Backend

**Files:**
- Create: `tests/integration/test_financial_permissions.py`
- Create: `tests/integration/test_export_endpoints.py`
- Create: `tests/unit/test_financial/test_rent_adjustment_edge_cases.py`
- Create: `tests/unit/test_financial/test_prepaid_lease.py`
- Modify: `tests/unit/test_month_advance_service.py`
- Modify: `tests/integration/test_soft_delete.py`
- Modify: `tests/unit/test_whatsapp_service.py`
- Modify: `tests/conftest.py` (fixtures → baker, remove dead fixture)

See spec sections 9.1 through 9.9 for the exact test code for each file. The test code is provided in full in the spec document.

- [ ] **Step 1: Create financial permissions integration test**

Create `tests/integration/test_financial_permissions.py` with parametrized tests for all financial write endpoints. Use `regular_authenticated_api_client` fixture.

- [ ] **Step 2: Create export endpoint tests**

Create `tests/integration/test_export_endpoints.py` with parametrized tests for Excel/CSV export across all resources.

- [ ] **Step 3: Create rent adjustment edge case tests**

Create `tests/unit/test_financial/test_rent_adjustment_edge_cases.py` testing: None IPCA factor, decimal rounding, zero/negative percentage.

- [ ] **Step 4: Expand month advance rollback tests**

Add rollback tests to `tests/unit/test_month_advance_service.py`: no-snapshot rollback, advance+rollback=original state.

- [ ] **Step 5: Create prepaid lease boundary tests**

Create `tests/unit/test_financial/test_prepaid_lease.py` testing: past/today/future prepaid_until, dashboard exclusion.

- [ ] **Step 6: Add soft-delete cascade tests**

Add to `tests/integration/test_soft_delete.py`: Building→Apartment cascade, Lease delete→apartment.is_rented=False.

- [ ] **Step 7: Convert key fixtures to model_bakery**

In `tests/conftest.py`, convert `building_with_apartment` and `person_with_credit_card` fixtures to use `baker.make()`.

- [ ] **Step 8: Add WhatsApp send test**

In `tests/unit/test_whatsapp_service.py`, add `@responses.activate` test for `send_verification_code` verifying HTTP payload.

- [ ] **Step 9: Remove dead fixture**

Delete `cleanup_test_contracts` fixture from `tests/conftest.py`.

- [ ] **Step 10: Run all tests**

```bash
python -m pytest tests/ -x --tb=short -q
python -m pytest --cov=core --cov-report=term-missing
```

- [ ] **Step 11: Commit**

```bash
git add tests/
git commit -m "test(backend): financial permissions, exports, edge cases, cascade, mock policy"
```

---

### Task 10: Testing Frontend

**Files:**
- Modify: `frontend/tests/mocks/handlers.ts` (add template, auth, financial, cash-flow, daily-control handlers)
- Rewrite: `frontend/lib/api/hooks/__tests__/use-contract-template.test.tsx`
- Rewrite: `frontend/lib/api/hooks/__tests__/use-auth.test.tsx`
- Modify: `frontend/lib/api/hooks/__tests__/use-financial-dashboard.test.tsx` (error tests)
- Modify: `frontend/lib/api/hooks/__tests__/use-cash-flow.test.tsx` (error tests)

See spec sections 10.1 through 10.3 for the exact MSW handler definitions and test rewrites.

- [ ] **Step 1: Add MSW handlers**

Add to `frontend/tests/mocks/handlers.ts`:
- `templateHandlers` for `/api/templates/*`
- `authHandlers` for `/api/auth/token/`, `/api/auth/me/`
- `financialDashboardHandlers` for `/api/financial-dashboard/*`
- `cashFlowHandlers` for `/api/cash-flow/*`
- `dailyControlHandlers` for `/api/daily-control/*`

Register all in the main handlers array.

- [ ] **Step 2: Rewrite use-contract-template.test.tsx**

Remove all `vi.mock('@/lib/api/client')` calls. Rewrite using `createWrapper()` and MSW. Test: fetch current template, save template, handle server error.

- [ ] **Step 3: Rewrite use-auth.test.tsx**

Remove all `vi.mock('@/store/auth-store')` calls. Test with real Zustand store (reset between tests via `useAuthStore.getState().clearAuth()`). Test: successful login stores tokens, failed login doesn't update store, logout clears store.

- [ ] **Step 4: Add error state tests to financial hooks**

In `use-financial-dashboard.test.tsx`, add tests that override MSW to return 500 and assert `isError === true`.

Same for `use-cash-flow.test.tsx` and `use-simulation.test.tsx`.

- [ ] **Step 5: Verify no internal mocks remain**

```bash
cd frontend && grep -rn "vi\.mock.*api/client\|vi\.mock.*store/" lib/api/hooks/__tests__/
```

Should return zero results.

- [ ] **Step 6: Run tests**

```bash
cd frontend && npm run test:unit -- --run
npm run lint && npm run type-check
```

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "test(frontend): rewrite mock-policy violations, add MSW handlers, error tests"
```
