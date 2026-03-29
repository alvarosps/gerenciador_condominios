# Mobile Backend API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all Django backend endpoints, models, and services required by the mobile app (tenant auth, tenant API, admin proofs, PIX, notifications, device tokens).

**Architecture:** New models (WhatsAppVerification, DeviceToken, PaymentProof, Notification) + new services (whatsapp_service, notification_service, pix_service) + new viewsets (tenant_views, device_views) + permission fixes. All added to the existing Django+DRF codebase.

**Tech Stack:** Django 5.2, DRF, simplejwt, Twilio (WhatsApp), Expo Push API, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-mobile-app-design.md` (rev.4)

**Related plans (future):**
- Plan 2: Mobile Setup + Auth (Expo scaffold)
- Plan 3: Mobile Tenant Experience
- Plan 4: Mobile Admin Experience
- Plan 5: Push Notifications

---

## File Structure

### New Files
- `core/models/mobile.py` — WhatsAppVerification, DeviceToken, PaymentProof, Notification models
- `core/services/whatsapp_service.py` — Twilio WhatsApp integration (auth codes, reajuste, manual messages)
- `core/services/notification_service.py` — Expo Push API + in-app notification creation
- `core/services/pix_service.py` — PIX EMV payload generation
- `core/viewsets/tenant_views.py` — All /api/tenant/* endpoints
- `core/viewsets/auth_views.py` — WhatsApp auth endpoints + set-password
- `core/viewsets/device_views.py` — Device token register/unregister
- `core/viewsets/proof_views.py` — Admin proof review endpoints
- `core/management/commands/send_scheduled_notifications.py` — Cron management command
- `tests/unit/test_whatsapp_service.py` — WhatsApp service tests
- `tests/unit/test_notification_service.py` — Notification service tests
- `tests/unit/test_pix_service.py` — PIX service tests
- `tests/integration/test_tenant_auth_api.py` — Tenant auth endpoint tests
- `tests/integration/test_tenant_api.py` — Tenant API endpoint tests
- `tests/integration/test_admin_proofs_api.py` — Admin proof endpoint tests
- `tests/integration/test_device_api.py` — Device token endpoint tests

### Modified Files
- `core/models.py` — Import and register new models from `core/models/mobile.py`
- `core/models/__init__.py` — Create models package if refactoring to directory (or keep in models.py)
- `core/serializers.py` — Add serializers for new models
- `core/permissions.py` — Add IsTenantUser, HasActiveLease
- `core/urls.py` — Register new viewsets and URL patterns
- `core/signals.py` — Add cache invalidation for new models
- `core/admin.py` — Register new models in Django admin
- `condominios_manager/settings.py` — Add Twilio env vars, MEDIA_ROOT config
- `requirements.txt` — Add twilio
- `pyproject.toml` — Add twilio to dependencies
- `core/viewsets/__init__.py` — Export new viewsets
- `core/viewsets/financial_dashboard_views.py` — Fix DailyControlViewSet permission to IsAdminUser

---

## Task 1: New Models + Migrations

**Files:**
- Modify: `core/models.py`
- Create: migration file (auto-generated)

- [ ] **Step 1: Add WhatsAppVerification model**

Add to `core/models.py` after the existing models:

```python
class WhatsAppVerification(models.Model):
    """Verification codes for WhatsApp-based tenant authentication."""

    cpf_cnpj = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["cpf_cnpj", "is_used", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"WhatsApp verification for {self.cpf_cnpj}"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired and self.attempts < 3
```

- [ ] **Step 2: Add DeviceToken model**

```python
class DeviceToken(AuditMixin, models.Model):
    """Expo push notification tokens for mobile devices."""

    PLATFORM_CHOICES = [
        ("ios", "iOS"),
        ("android", "Android"),
    ]

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.platform} token for {self.user}"
```

- [ ] **Step 3: Add PaymentProof model**

```python
class PaymentProof(AuditMixin, SoftDeleteMixin, models.Model):
    """Proof of payment uploaded by tenants (photo/PDF of PIX receipt)."""

    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("approved", "Aprovado"),
        ("rejected", "Rejeitado"),
    ]

    lease = models.ForeignKey(
        "Lease",
        on_delete=models.CASCADE,
        related_name="payment_proofs",
    )
    reference_month = models.DateField()
    file = models.FileField(upload_to="payment_proofs/%Y/%m/")
    pix_code = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_proofs",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["lease", "reference_month"]),
        ]

    def __str__(self) -> str:
        return f"Proof for {self.lease} - {self.reference_month:%Y-%m}"
```

- [ ] **Step 4: Add Notification model**

```python
class Notification(AuditMixin, models.Model):
    """Push/in-app notifications for tenants and admins."""

    TYPE_CHOICES = [
        ("due_reminder", "Lembrete de vencimento"),
        ("due_today", "Vencimento hoje"),
        ("overdue", "Aluguel atrasado"),
        ("proof_approved", "Comprovante aprovado"),
        ("proof_rejected", "Comprovante rejeitado"),
        ("rent_adjustment", "Reajuste de aluguel"),
        ("admin_notice", "Aviso do admin"),
        ("new_proof", "Novo comprovante"),
        ("contract_expiring", "Contrato vencendo"),
        ("adjustment_eligible", "Reajuste elegível"),
    ]

    recipient = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField()
    data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["recipient", "-sent_at"]),
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["type", "recipient", "sent_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} → {self.recipient} ({self.sent_at:%Y-%m-%d})"
```

- [ ] **Step 5: Add PIX fields to Person and FinancialSettings**

In Person model, add after existing fields:

```python
pix_key = models.CharField(max_length=100, null=True, blank=True)
pix_key_type = models.CharField(
    max_length=10,
    null=True,
    blank=True,
    choices=[
        ("cpf", "CPF"),
        ("cnpj", "CNPJ"),
        ("email", "E-mail"),
        ("phone", "Telefone"),
        ("random", "Chave aleatória"),
    ],
)
```

In FinancialSettings model, add:

```python
default_pix_key = models.CharField(max_length=100, null=True, blank=True)
default_pix_key_type = models.CharField(
    max_length=10,
    null=True,
    blank=True,
    choices=[
        ("cpf", "CPF"),
        ("cnpj", "CNPJ"),
        ("email", "E-mail"),
        ("phone", "Telefone"),
        ("random", "Chave aleatória"),
    ],
)
```

- [ ] **Step 6: Generate and apply migrations**

Run:
```bash
python manage.py makemigrations core --name mobile_models
python manage.py migrate
```

Expected: Migration creates 4 new tables + 4 new fields on existing tables.

- [ ] **Step 7: Register models in admin.py**

Add to `core/admin.py`:

```python
from core.models import WhatsAppVerification, DeviceToken, PaymentProof, Notification

@admin.register(WhatsAppVerification)
class WhatsAppVerificationAdmin(admin.ModelAdmin):
    list_display = ["cpf_cnpj", "phone", "is_used", "created_at", "expires_at"]
    list_filter = ["is_used"]
    search_fields = ["cpf_cnpj", "phone"]

@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "is_active", "created_at"]
    list_filter = ["platform", "is_active"]

@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ["lease", "reference_month", "status", "created_at"]
    list_filter = ["status"]

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "type", "title", "is_read", "sent_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["title", "body"]
```

- [ ] **Step 8: Add cache invalidation signals**

Add to `core/signals.py`:

```python
from core.models import PaymentProof, Notification, DeviceToken

for model_class in [PaymentProof, Notification, DeviceToken]:
    post_save.connect(invalidate_cache_on_save, sender=model_class)
    post_delete.connect(invalidate_cache_on_delete, sender=model_class)
```

- [ ] **Step 9: Commit**

```bash
git add core/models.py core/migrations/ core/admin.py core/signals.py
git commit -m "feat(models): add mobile models — WhatsAppVerification, DeviceToken, PaymentProof, Notification, PIX fields"
```

---

## Task 2: Permissions — Fix Existing + Add New

**Files:**
- Modify: `core/permissions.py`
- Modify: `core/viewsets/financial_dashboard_views.py`
- Test: `tests/unit/test_permissions.py`

- [ ] **Step 1: Write tests for IsTenantUser and HasActiveLease**

Create `tests/unit/test_permissions.py`:

```python
import pytest
from unittest.mock import MagicMock
from core.permissions import IsTenantUser, HasActiveLease


@pytest.mark.unit
@pytest.mark.django_db
class TestIsTenantUser:
    def test_denies_unauthenticated(self):
        request = MagicMock()
        request.user.is_authenticated = False
        assert IsTenantUser().has_permission(request, None) is False

    def test_denies_staff(self):
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = True
        assert IsTenantUser().has_permission(request, None) is False

    def test_denies_no_tenant_profile(self):
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False
        request.user.tenant_profile = None
        assert IsTenantUser().has_permission(request, None) is False

    def test_denies_deleted_tenant(self):
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False
        request.user.tenant_profile = MagicMock(is_deleted=True)
        assert IsTenantUser().has_permission(request, None) is False

    def test_allows_active_tenant(self):
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False
        request.user.tenant_profile = MagicMock(is_deleted=False)
        assert IsTenantUser().has_permission(request, None) is True


@pytest.mark.unit
@pytest.mark.django_db
class TestHasActiveLease:
    def test_denies_no_tenant(self):
        request = MagicMock()
        request.user.tenant_profile = None
        assert HasActiveLease().has_permission(request, None) is False

    def test_denies_no_active_lease(self):
        request = MagicMock()
        tenant = MagicMock()
        tenant.leases.filter.return_value.exists.return_value = False
        request.user.tenant_profile = tenant
        assert HasActiveLease().has_permission(request, None) is False

    def test_allows_with_active_lease(self):
        request = MagicMock()
        tenant = MagicMock()
        tenant.leases.filter.return_value.exists.return_value = True
        request.user.tenant_profile = tenant
        assert HasActiveLease().has_permission(request, None) is True
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/unit/test_permissions.py -v`
Expected: ImportError — IsTenantUser, HasActiveLease not found

- [ ] **Step 3: Implement IsTenantUser and HasActiveLease**

Add to `core/permissions.py`:

```python
class IsTenantUser(permissions.BasePermission):
    """Allows access only to authenticated tenants with a non-deleted record."""

    def has_permission(self, request: Request, view: Any) -> bool:
        if not (request.user.is_authenticated and not request.user.is_staff):
            return False
        tenant = getattr(request.user, "tenant_profile", None)
        return tenant is not None and not tenant.is_deleted


class HasActiveLease(permissions.BasePermission):
    """Allows access only to tenants with an active (non-deleted) lease."""

    def has_permission(self, request: Request, view: Any) -> bool:
        tenant = getattr(request.user, "tenant_profile", None)
        if tenant is None:
            return False
        return tenant.leases.filter(is_deleted=False).exists()
```

Add to `PERMISSION_CLASSES` dict:

```python
"IsTenantUser": IsTenantUser,
"HasActiveLease": HasActiveLease,
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `python -m pytest tests/unit/test_permissions.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Fix DailyControlViewSet permission**

In `core/viewsets/financial_dashboard_views.py`, change `DailyControlViewSet`:

```python
# Before:
permission_classes = [IsAuthenticated]

# After:
permission_classes = [IsAdminUser]
```

Also check and fix `CashFlowViewSet` and `FinancialDashboardViewSet` if they use `IsAuthenticated` instead of a more restrictive permission.

- [ ] **Step 6: Verify Tenant model has `related_name='tenant_profile'` on user field**

Check `core/models.py` — the `Tenant.user` field must have `related_name='tenant_profile'` for the permission to work via `request.user.tenant_profile`. If not, add it and generate a migration.

- [ ] **Step 7: Commit**

```bash
git add core/permissions.py core/viewsets/financial_dashboard_views.py tests/unit/test_permissions.py
git commit -m "feat(permissions): add IsTenantUser, HasActiveLease; fix DailyControlViewSet to IsAdminUser"
```

---

## Task 3: WhatsApp Service (Twilio)

**Files:**
- Create: `core/services/whatsapp_service.py`
- Test: `tests/unit/test_whatsapp_service.py`
- Modify: `requirements.txt`, `pyproject.toml`
- Modify: `condominios_manager/settings.py`

- [ ] **Step 1: Add twilio dependency**

Add `twilio>=9.0.0` to `requirements.txt` and `pyproject.toml` `[project.dependencies]`.

Run: `uv pip install twilio`

- [ ] **Step 2: Add Twilio settings**

Add to `condominios_manager/settings.py`:

```python
# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID = config("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = config("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_FROM = config("TWILIO_WHATSAPP_FROM", default="")
```

- [ ] **Step 3: Write tests for phone normalization and code generation**

Create `tests/unit/test_whatsapp_service.py`:

```python
import pytest
from core.services.whatsapp_service import normalize_phone_to_e164, generate_verification_code


@pytest.mark.unit
class TestNormalizePhone:
    def test_already_e164(self):
        assert normalize_phone_to_e164("+5511999998888") == "+5511999998888"

    def test_strips_formatting(self):
        assert normalize_phone_to_e164("(11) 99999-8888") == "+5511999998888"

    def test_adds_country_code(self):
        assert normalize_phone_to_e164("11999998888") == "+5511999998888"

    def test_handles_spaces_and_dashes(self):
        assert normalize_phone_to_e164("11 99999 8888") == "+5511999998888"

    def test_empty_phone_raises(self):
        with pytest.raises(ValueError, match="Telefone não cadastrado"):
            normalize_phone_to_e164("")

    def test_none_phone_raises(self):
        with pytest.raises(ValueError, match="Telefone não cadastrado"):
            normalize_phone_to_e164(None)


@pytest.mark.unit
class TestGenerateCode:
    def test_code_is_6_digits(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_codes_are_random(self):
        codes = {generate_verification_code() for _ in range(100)}
        assert len(codes) > 1  # not all the same
```

- [ ] **Step 4: Run tests — verify they fail**

Run: `python -m pytest tests/unit/test_whatsapp_service.py -v`
Expected: ImportError

- [ ] **Step 5: Implement whatsapp_service.py**

Create `core/services/whatsapp_service.py`:

```python
import re
import secrets
from django.conf import settings


def normalize_phone_to_e164(phone: str | None) -> str:
    """Normalize Brazilian phone to E.164 format (+5511999998888).

    Strips formatting (parens, spaces, dashes) and adds +55 if needed.
    Raises ValueError if phone is empty or None.
    """
    if not phone:
        raise ValueError("Telefone não cadastrado")

    digits = re.sub(r"\D", "", phone)

    if not digits:
        raise ValueError("Telefone não cadastrado")

    if digits.startswith("55") and len(digits) >= 12:
        return f"+{digits}"
    return f"+55{digits}"


def generate_verification_code() -> str:
    """Generate a cryptographically secure 6-digit verification code."""
    return f"{secrets.randbelow(1000000):06d}"


def send_whatsapp_message(to_phone: str, template_sid: str, template_variables: dict[str, str]) -> str:
    """Send a WhatsApp message via Twilio.

    Args:
        to_phone: E.164 formatted phone number
        template_sid: Twilio content template SID
        template_variables: Template variable substitutions

    Returns:
        Twilio message SID

    Raises:
        RuntimeError: If Twilio credentials are not configured
    """
    if not settings.TWILIO_ACCOUNT_SID:
        raise RuntimeError("Twilio credentials not configured")

    from twilio.rest import Client

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        from_=f"whatsapp:{settings.TWILIO_WHATSAPP_FROM}",
        to=f"whatsapp:{to_phone}",
        content_sid=template_sid,
        content_variables=template_variables,
    )
    return message.sid


def send_verification_code(phone: str, code: str) -> str:
    """Send a verification code via WhatsApp.

    Args:
        phone: E.164 formatted phone number
        code: 6-digit verification code

    Returns:
        Twilio message SID
    """
    template_sid = settings.TWILIO_TEMPLATE_VERIFICATION
    return send_whatsapp_message(
        to_phone=phone,
        template_sid=template_sid,
        template_variables={"1": code},
    )


def send_rent_adjustment_notice(
    phone: str,
    property_address: str,
    old_value: str,
    new_value: str,
    percentage: str,
    effective_date: str,
) -> str:
    """Send rent adjustment notification via WhatsApp."""
    template_sid = settings.TWILIO_TEMPLATE_RENT_ADJUSTMENT
    return send_whatsapp_message(
        to_phone=phone,
        template_sid=template_sid,
        template_variables={
            "1": property_address,
            "2": old_value,
            "3": new_value,
            "4": percentage,
            "5": effective_date,
        },
    )
```

- [ ] **Step 6: Add template SID settings**

Add to `condominios_manager/settings.py`:

```python
TWILIO_TEMPLATE_VERIFICATION = config("TWILIO_TEMPLATE_VERIFICATION", default="")
TWILIO_TEMPLATE_RENT_ADJUSTMENT = config("TWILIO_TEMPLATE_RENT_ADJUSTMENT", default="")
TWILIO_TEMPLATE_GENERIC = config("TWILIO_TEMPLATE_GENERIC", default="")
```

- [ ] **Step 7: Run tests — verify they pass**

Run: `python -m pytest tests/unit/test_whatsapp_service.py -v`
Expected: All pass (send tests that hit Twilio are not included — mock at integration level)

- [ ] **Step 8: Register service in __init__.py**

Add to `core/services/__init__.py`:

```python
from core.services.whatsapp_service import (
    normalize_phone_to_e164,
    generate_verification_code,
    send_verification_code,
    send_rent_adjustment_notice,
    send_whatsapp_message,
)
```

- [ ] **Step 9: Commit**

```bash
git add core/services/whatsapp_service.py tests/unit/test_whatsapp_service.py requirements.txt pyproject.toml condominios_manager/settings.py core/services/__init__.py
git commit -m "feat(whatsapp): add WhatsApp service with Twilio integration"
```

---

## Task 4: Tenant Auth Endpoints

**Files:**
- Create: `core/viewsets/auth_views.py`
- Create: `core/serializers/mobile_serializers.py` (or add to existing serializers.py)
- Test: `tests/integration/test_tenant_auth_api.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Write integration tests for WhatsApp auth flow**

Create `tests/integration/test_tenant_auth_api.py`:

```python
import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import Tenant, Apartment, Building, Lease, WhatsAppVerification


@pytest.mark.integration
@pytest.mark.django_db
class TestWhatsAppAuthRequest:
    def setup_method(self):
        self.client = APIClient()

    @pytest.fixture
    def tenant_with_phone(self, admin_user):
        building = Building.objects.create(
            street_number="100", name="Test", created_by=admin_user, updated_by=admin_user,
        )
        apartment = Apartment.objects.create(
            building=building, number=101, rental_value=Decimal("1200.00"),
            cleaning_fee=Decimal("150.00"), max_tenants=2,
            created_by=admin_user, updated_by=admin_user,
        )
        tenant = Tenant.objects.create(
            name="João Silva", cpf_cnpj="12345678901", phone="(11) 99999-8888",
            marital_status="Solteiro(a)", due_day=10,
            created_by=admin_user, updated_by=admin_user,
        )
        Lease.objects.create(
            apartment=apartment, responsible_tenant=tenant,
            start_date=timezone.now().date(), validity_months=12,
            rental_value=Decimal("1200.00"), number_of_tenants=1,
            created_by=admin_user, updated_by=admin_user,
        )
        return tenant

    @patch("core.viewsets.auth_views.send_verification_code")
    def test_request_code_success(self, mock_send, tenant_with_phone):
        mock_send.return_value = "SM123"
        response = self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "12345678901"})
        assert response.status_code == 200
        assert response.data["message"] == "Código enviado"
        assert WhatsAppVerification.objects.filter(cpf_cnpj="12345678901").exists()
        mock_send.assert_called_once()

    def test_request_code_unknown_cpf(self):
        response = self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "00000000000"})
        assert response.status_code == 404

    @patch("core.viewsets.auth_views.send_verification_code")
    def test_verify_code_success(self, mock_send, tenant_with_phone):
        mock_send.return_value = "SM123"
        # Request code
        self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "12345678901"})
        verification = WhatsAppVerification.objects.filter(cpf_cnpj="12345678901").latest("created_at")

        # Verify code
        response = self.client.post("/api/auth/whatsapp/verify/", {
            "cpf_cnpj": "12345678901",
            "code": verification.code,
        })
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        # Tenant.user should be linked
        tenant_with_phone.refresh_from_db()
        assert tenant_with_phone.user is not None
        assert tenant_with_phone.user.is_staff is False

    @patch("core.viewsets.auth_views.send_verification_code")
    def test_verify_wrong_code(self, mock_send, tenant_with_phone):
        mock_send.return_value = "SM123"
        self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "12345678901"})
        response = self.client.post("/api/auth/whatsapp/verify/", {
            "cpf_cnpj": "12345678901",
            "code": "000000",
        })
        assert response.status_code == 400

    @patch("core.viewsets.auth_views.send_verification_code")
    def test_rate_limiting(self, mock_send, tenant_with_phone):
        mock_send.return_value = "SM123"
        for _ in range(3):
            self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "12345678901"})
        # 4th request should be rate limited
        response = self.client.post("/api/auth/whatsapp/request/", {"cpf_cnpj": "12345678901"})
        assert response.status_code == 429
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/integration/test_tenant_auth_api.py -v`
Expected: ImportError or 404 (endpoints don't exist)

- [ ] **Step 3: Implement auth_views.py**

Create `core/viewsets/auth_views.py`:

```python
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Tenant, WhatsAppVerification
from core.services.whatsapp_service import (
    generate_verification_code,
    normalize_phone_to_e164,
    send_verification_code,
)

RATE_LIMIT_WINDOW_MINUTES = 15
RATE_LIMIT_MAX_CODES = 3
CODE_EXPIRY_MINUTES = 5
MAX_ATTEMPTS_PER_CODE = 3


class WhatsAppAuthViewSet(ViewSet):
    """WhatsApp-based authentication for tenants."""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="request")
    def request_code(self, request: Request) -> Response:
        cpf_cnpj = request.data.get("cpf_cnpj", "").strip()
        if not cpf_cnpj:
            return Response({"error": "CPF/CNPJ é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant = Tenant.objects.get(cpf_cnpj=cpf_cnpj)
        except Tenant.DoesNotExist:
            return Response({"error": "CPF/CNPJ não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        # Rate limiting
        window_start = timezone.now() - timedelta(minutes=RATE_LIMIT_WINDOW_MINUTES)
        recent_codes = WhatsAppVerification.objects.filter(
            cpf_cnpj=cpf_cnpj, created_at__gte=window_start
        ).count()
        if recent_codes >= RATE_LIMIT_MAX_CODES:
            return Response(
                {"error": "Muitas tentativas. Aguarde 15 minutos."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Normalize phone
        try:
            phone_e164 = normalize_phone_to_e164(tenant.phone)
        except ValueError:
            return Response(
                {"error": "Telefone não cadastrado. Entre em contato com o administrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate and save code
        code = generate_verification_code()
        WhatsAppVerification.objects.create(
            cpf_cnpj=cpf_cnpj,
            code=code,
            phone=phone_e164,
            expires_at=timezone.now() + timedelta(minutes=CODE_EXPIRY_MINUTES),
        )

        # Send via Twilio
        send_verification_code(phone_e164, code)

        return Response({"message": "Código enviado"})

    @action(detail=False, methods=["post"], url_path="verify")
    def verify_code(self, request: Request) -> Response:
        cpf_cnpj = request.data.get("cpf_cnpj", "").strip()
        code = request.data.get("code", "").strip()

        if not cpf_cnpj or not code:
            return Response(
                {"error": "CPF/CNPJ e código são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find latest valid verification
        verification = (
            WhatsAppVerification.objects.filter(
                cpf_cnpj=cpf_cnpj, is_used=False, expires_at__gt=timezone.now()
            )
            .order_by("-created_at")
            .first()
        )

        if verification is None:
            return Response(
                {"error": "Código expirado ou não encontrado. Solicite um novo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.attempts >= MAX_ATTEMPTS_PER_CODE:
            return Response(
                {"error": "Muitas tentativas erradas. Solicite um novo código."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.code != code:
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            return Response({"error": "Código incorreto"}, status=status.HTTP_400_BAD_REQUEST)

        # Code is valid — mark as used
        verification.is_used = True
        verification.save(update_fields=["is_used"])

        # Get tenant and create/get user
        tenant = Tenant.objects.get(cpf_cnpj=cpf_cnpj)
        if tenant.user is None:
            user = User.objects.create_user(
                username=f"tenant_{tenant.pk}",
                first_name=tenant.name.split()[0] if tenant.name else "",
                last_name=" ".join(tenant.name.split()[1:]) if tenant.name else "",
                is_staff=False,
            )
            tenant.user = user
            tenant.save(update_fields=["user"])
        else:
            user = tenant.user

        # Generate JWT
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.pk,
                "name": tenant.name,
                "is_staff": False,
            },
        })


class SetPasswordViewSet(ViewSet):
    """Allows admin users to set a password for mobile login."""

    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["post"], url_path="set-password")
    def set_password(self, request: Request) -> Response:
        password = request.data.get("password", "")
        if len(password) < 8:
            return Response(
                {"error": "Senha deve ter no mínimo 8 caracteres"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(password)
        request.user.save(update_fields=["password"])
        return Response({"message": "Senha definida com sucesso"})
```

- [ ] **Step 4: Register URL patterns**

Add to `core/urls.py`:

```python
from core.viewsets.auth_views import WhatsAppAuthViewSet, SetPasswordViewSet

# After existing router registrations:
router.register(r"auth/whatsapp", WhatsAppAuthViewSet, basename="whatsapp-auth")
router.register(r"auth", SetPasswordViewSet, basename="auth-set-password")
```

- [ ] **Step 5: Update viewsets/__init__.py**

Add to `core/viewsets/__init__.py`:

```python
from core.viewsets.auth_views import WhatsAppAuthViewSet, SetPasswordViewSet
```

- [ ] **Step 6: Run tests — verify they pass**

Run: `python -m pytest tests/integration/test_tenant_auth_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add core/viewsets/auth_views.py tests/integration/test_tenant_auth_api.py core/urls.py core/viewsets/__init__.py
git commit -m "feat(auth): add WhatsApp-based tenant authentication endpoints"
```

---

## Task 5: PIX Service

**Files:**
- Create: `core/services/pix_service.py`
- Test: `tests/unit/test_pix_service.py`

- [ ] **Step 1: Write tests for PIX payload generation**

Create `tests/unit/test_pix_service.py`:

```python
import pytest
from decimal import Decimal
from core.services.pix_service import generate_pix_payload, generate_pix_emv


@pytest.mark.unit
class TestPixPayload:
    def test_generate_payload_with_cpf_key(self):
        result = generate_pix_payload(
            pix_key="12345678901",
            pix_key_type="cpf",
            amount=Decimal("1200.00"),
            merchant_name="Maria Silva",
            city="Sao Paulo",
        )
        assert "pix_copy_paste" in result
        assert "qr_data" in result
        assert result["amount"] == "1200.00"
        assert result["pix_key"] == "12345678901"

    def test_generate_emv_format(self):
        emv = generate_pix_emv(
            pix_key="12345678901",
            merchant_name="Maria Silva",
            city="Sao Paulo",
            amount=Decimal("1200.00"),
        )
        assert emv.startswith("00")  # EMV payload indicator
        assert "12345678901" in emv
        assert "1200.00" in emv

    def test_no_pix_key_raises(self):
        with pytest.raises(ValueError, match="Chave PIX não cadastrada"):
            generate_pix_payload(
                pix_key="",
                pix_key_type="cpf",
                amount=Decimal("1200.00"),
                merchant_name="Test",
                city="Test",
            )
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/unit/test_pix_service.py -v`

- [ ] **Step 3: Implement pix_service.py**

Create `core/services/pix_service.py`:

```python
import binascii
from decimal import Decimal


def _crc16_ccitt(data: str) -> str:
    """Calculate CRC16-CCITT for EMV PIX payload."""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _emv_field(tag: str, value: str) -> str:
    """Format an EMV TLV field: tag + length (2 digits) + value."""
    return f"{tag}{len(value):02d}{value}"


def generate_pix_emv(
    pix_key: str,
    merchant_name: str,
    city: str,
    amount: Decimal,
    txid: str = "***",
) -> str:
    """Generate PIX EMV (copia e cola) payload string.

    Follows BCB specification for static PIX QR codes.
    """
    # Merchant Account Information (tag 26)
    gui = _emv_field("00", "br.gov.bcb.pix")
    key = _emv_field("01", pix_key)
    merchant_account = _emv_field("26", gui + key)

    payload = (
        _emv_field("00", "01")  # Payload Format Indicator
        + merchant_account
        + _emv_field("52", "0000")  # Merchant Category Code
        + _emv_field("53", "986")  # Transaction Currency (BRL)
        + _emv_field("54", f"{amount:.2f}")  # Transaction Amount
        + _emv_field("58", "BR")  # Country Code
        + _emv_field("59", merchant_name[:25])  # Merchant Name (max 25)
        + _emv_field("60", city[:15])  # Merchant City (max 15)
        + _emv_field("62", _emv_field("05", txid))  # Additional Data (txid)
    )

    # CRC (tag 63, 04 length placeholder + actual CRC)
    payload += "6304"
    crc = _crc16_ccitt(payload)
    return payload + crc


def generate_pix_payload(
    pix_key: str,
    pix_key_type: str,
    amount: Decimal,
    merchant_name: str,
    city: str,
) -> dict:
    """Generate full PIX payload for mobile app.

    Returns dict with pix_copy_paste (EMV string), qr_data (same string for QR rendering),
    and metadata fields.

    Raises ValueError if pix_key is empty.
    """
    if not pix_key:
        raise ValueError("Chave PIX não cadastrada. Entre em contato com o administrador.")

    emv = generate_pix_emv(
        pix_key=pix_key,
        merchant_name=merchant_name,
        city=city,
        amount=amount,
    )

    return {
        "pix_copy_paste": emv,
        "qr_data": emv,
        "pix_key": pix_key,
        "pix_key_type": pix_key_type,
        "amount": f"{amount:.2f}",
        "merchant_name": merchant_name,
    }
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `python -m pytest tests/unit/test_pix_service.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add core/services/pix_service.py tests/unit/test_pix_service.py
git commit -m "feat(pix): add PIX EMV payload generation service"
```

---

## Task 6: Tenant API — Read Endpoints

**Files:**
- Create: `core/viewsets/tenant_views.py`
- Modify: `core/serializers.py`
- Modify: `core/urls.py`
- Test: `tests/integration/test_tenant_api.py`

- [ ] **Step 1: Add tenant-specific serializers**

Add to `core/serializers.py`:

```python
class TenantMeSerializer(serializers.ModelSerializer):
    """Serializer for /api/tenant/me/ — tenant's own data with apartment and lease."""

    apartment = ApartmentSerializer(source="active_lease.apartment", read_only=True)
    lease = LeaseSerializer(source="active_lease", read_only=True)
    dependents = DependentSerializer(many=True, read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "id", "name", "cpf_cnpj", "is_company", "rg", "phone",
            "marital_status", "profession", "due_day", "warning_count",
            "apartment", "lease", "dependents",
        ]

    @property
    def active_lease(self):
        return None  # handled via annotation in viewset


class PaymentProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = [
            "id", "lease", "reference_month", "file", "pix_code",
            "status", "reviewed_by", "reviewed_at", "rejection_reason",
            "created_at",
        ]
        read_only_fields = ["id", "status", "reviewed_by", "reviewed_at", "rejection_reason", "created_at"]


class PaymentProofCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = ["reference_month", "file", "pix_code"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "is_read", "read_at", "sent_at", "data"]
        read_only_fields = ["id", "type", "title", "body", "sent_at", "data"]
```

- [ ] **Step 2: Write integration tests for tenant read endpoints**

Create `tests/integration/test_tenant_api.py`:

```python
import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import (
    Building, Apartment, Tenant, Lease, RentPayment, Notification,
)


@pytest.fixture
def tenant_user(admin_user):
    """Create a tenant with a linked Django user and active lease."""
    building = Building.objects.create(
        street_number="200", name="Test Building",
        created_by=admin_user, updated_by=admin_user,
    )
    apartment = Apartment.objects.create(
        building=building, number=201, rental_value=Decimal("1500.00"),
        cleaning_fee=Decimal("150.00"), max_tenants=2,
        created_by=admin_user, updated_by=admin_user,
    )
    user = User.objects.create_user(username="tenant_test", is_staff=False)
    tenant = Tenant.objects.create(
        name="Maria Tenant", cpf_cnpj="98765432100", phone="(11) 88888-7777",
        marital_status="Solteiro(a)", due_day=15, user=user,
        created_by=admin_user, updated_by=admin_user,
    )
    Lease.objects.create(
        apartment=apartment, responsible_tenant=tenant,
        start_date=timezone.now().date(), validity_months=12,
        rental_value=Decimal("1500.00"), number_of_tenants=1,
        created_by=admin_user, updated_by=admin_user,
    )
    return tenant, user


@pytest.fixture
def tenant_client(tenant_user):
    _, user = tenant_user
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantMe:
    def test_get_own_data(self, tenant_client, tenant_user):
        tenant, _ = tenant_user
        response = tenant_client.get("/api/tenant/me/")
        assert response.status_code == 200
        assert response.data["name"] == "Maria Tenant"
        assert response.data["cpf_cnpj"] == "98765432100"

    def test_admin_cannot_access(self, authenticated_api_client):
        response = authenticated_api_client.get("/api/tenant/me/")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantPayments:
    def test_list_own_payments(self, tenant_client, tenant_user, admin_user):
        tenant, _ = tenant_user
        lease = tenant.leases.first()
        RentPayment.objects.create(
            lease=lease, reference_month=timezone.now().date().replace(day=1),
            amount_paid=Decimal("1500.00"), payment_date=timezone.now().date(),
            created_by=admin_user, updated_by=admin_user,
        )
        response = tenant_client.get("/api/tenant/payments/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.integration
@pytest.mark.django_db
class TestTenantNotifications:
    def test_list_own_notifications(self, tenant_client, tenant_user):
        _, user = tenant_user
        Notification.objects.create(
            recipient=user, type="due_reminder",
            title="Vencimento próximo", body="Seu aluguel vence em 3 dias",
            sent_at=timezone.now(),
        )
        response = tenant_client.get("/api/tenant/notifications/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_mark_as_read(self, tenant_client, tenant_user):
        _, user = tenant_user
        notif = Notification.objects.create(
            recipient=user, type="due_reminder",
            title="Test", body="Test", sent_at=timezone.now(),
        )
        response = tenant_client.patch(f"/api/tenant/notifications/{notif.pk}/read/")
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True
```

- [ ] **Step 3: Run tests — verify they fail**

Run: `python -m pytest tests/integration/test_tenant_api.py -v`

- [ ] **Step 4: Implement tenant_views.py**

Create `core/viewsets/tenant_views.py`:

```python
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import (
    Lease, Notification, PaymentProof, RentAdjustment, RentPayment,
)
from core.permissions import HasActiveLease, IsTenantUser
from core.serializers import (
    NotificationSerializer,
    PaymentProofCreateSerializer,
    PaymentProofSerializer,
    RentAdjustmentSerializer,
    RentPaymentSerializer,
)
from core.services.pix_service import generate_pix_payload


def _get_tenant(request: Request):
    """Get the tenant linked to the authenticated user."""
    return getattr(request.user, "tenant_profile", None)


def _get_active_lease(tenant) -> Lease | None:
    """Get the tenant's active (non-deleted) lease."""
    return (
        tenant.leases
        .filter(is_deleted=False)
        .select_related("apartment", "apartment__building", "apartment__owner")
        .first()
    )


class TenantReadViewSet(ViewSet):
    """Read-only endpoints for tenant's own data."""

    permission_classes = [IsTenantUser]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        data = {
            "id": tenant.pk,
            "name": tenant.name,
            "cpf_cnpj": tenant.cpf_cnpj,
            "is_company": tenant.is_company,
            "rg": tenant.rg,
            "phone": tenant.phone,
            "marital_status": tenant.marital_status,
            "profession": tenant.profession,
            "due_day": tenant.due_day,
            "warning_count": tenant.warning_count,
            "dependents": list(tenant.dependents.values("id", "name", "phone", "cpf_cnpj")),
        }
        if lease:
            apt = lease.apartment
            data["lease"] = {
                "id": lease.pk,
                "start_date": lease.start_date,
                "validity_months": lease.validity_months,
                "rental_value": str(lease.rental_value),
                "pending_rental_value": str(lease.pending_rental_value) if lease.pending_rental_value else None,
                "pending_rental_value_date": lease.pending_rental_value_date,
                "number_of_tenants": lease.number_of_tenants,
                "contract_generated": lease.contract_generated,
            }
            data["apartment"] = {
                "id": apt.pk,
                "number": apt.number,
                "building_name": apt.building.name,
                "building_address": apt.building.street_number,
            }
        return Response(data)

    @action(detail=False, methods=["get"], url_path="contract")
    def contract(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        if not lease or not lease.contract_generated:
            return Response(
                {"error": "Contrato não disponível"},
                status=status.HTTP_404_NOT_FOUND,
            )
        apt = lease.apartment
        pdf_path = f"contracts/{apt.building.street_number}/contract_apto_{apt.number}_{lease.pk}.pdf"
        from django.http import FileResponse
        import os
        from django.conf import settings

        full_path = os.path.join(settings.BASE_DIR, pdf_path)
        if not os.path.exists(full_path):
            return Response({"error": "Arquivo não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(full_path, "rb"), content_type="application/pdf")

    @action(detail=False, methods=["get"], url_path="payments")
    def payments(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        leases = tenant.leases.filter(is_deleted=False)
        payments = RentPayment.objects.filter(lease__in=leases).order_by("-reference_month")
        from core.pagination import CustomPageNumberPagination

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(payments, request)
        serializer = RentPaymentSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="rent-adjustments")
    def rent_adjustments(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        if not lease:
            return Response({"results": []})
        adjustments = RentAdjustment.objects.filter(lease=lease).order_by("-adjustment_date")
        serializer = RentAdjustmentSerializer(adjustments, many=True)
        return Response({"results": serializer.data})


class TenantWriteViewSet(ViewSet):
    """Write endpoints requiring active lease."""

    permission_classes = [IsTenantUser, HasActiveLease]

    @action(detail=False, methods=["post"], url_path="payments/pix")
    def generate_pix(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        apt = lease.apartment

        # Determine PIX key
        if apt.owner:
            pix_key = apt.owner.pix_key
            pix_key_type = apt.owner.pix_key_type
            merchant_name = apt.owner.name
        else:
            from core.models import FinancialSettings
            settings_obj = FinancialSettings.objects.filter(pk=1).first()
            pix_key = settings_obj.default_pix_key if settings_obj else None
            pix_key_type = settings_obj.default_pix_key_type if settings_obj else None
            from core.models import Landlord
            landlord = Landlord.get_active()
            merchant_name = landlord.name if landlord else "Condomínio"

        try:
            payload = generate_pix_payload(
                pix_key=pix_key or "",
                pix_key_type=pix_key_type or "",
                amount=lease.rental_value,
                merchant_name=merchant_name,
                city="Sao Paulo",
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payload)

    @action(detail=False, methods=["post"], url_path="payments/proof", parser_classes=[MultiPartParser])
    def upload_proof(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        serializer = PaymentProofCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        proof = PaymentProof.objects.create(
            lease=lease,
            reference_month=serializer.validated_data["reference_month"],
            file=serializer.validated_data["file"],
            pix_code=serializer.validated_data.get("pix_code", ""),
            created_by=request.user,
            updated_by=request.user,
        )

        # Notify admin
        from core.services.notification_service import notify_new_proof
        notify_new_proof(proof)

        return Response(PaymentProofSerializer(proof).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="payments/proof/(?P<proof_id>[0-9]+)")
    def proof_status(self, request: Request, proof_id: int = None) -> Response:
        tenant = _get_tenant(request)
        try:
            proof = PaymentProof.objects.get(
                pk=proof_id, lease__responsible_tenant=tenant,
            )
        except PaymentProof.DoesNotExist:
            return Response({"error": "Comprovante não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentProofSerializer(proof).data)

    @action(detail=False, methods=["post"], url_path="due-date/simulate")
    def simulate_due_date(self, request: Request) -> Response:
        tenant = _get_tenant(request)
        lease = _get_active_lease(tenant)
        new_due_day = request.data.get("new_due_day")
        if not new_due_day:
            return Response({"error": "new_due_day é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        from core.services.fee_calculator import FeeCalculatorService
        result = FeeCalculatorService.calculate_due_date_change_fee(
            lease=lease, new_due_day=int(new_due_day),
        )
        return Response(result)


class TenantNotificationViewSet(ViewSet):
    """Notification management for tenants."""

    permission_classes = [IsTenantUser]

    @action(detail=False, methods=["get"], url_path="notifications")
    def list_notifications(self, request: Request) -> Response:
        notifications = Notification.objects.filter(recipient=request.user)
        from core.pagination import CustomPageNumberPagination

        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(notifications, request)
        serializer = NotificationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["patch"], url_path=r"notifications/(?P<notif_id>[0-9]+)/read")
    def mark_read(self, request: Request, notif_id: int = None) -> Response:
        try:
            notif = Notification.objects.get(pk=notif_id, recipient=request.user)
        except Notification.DoesNotExist:
            return Response({"error": "Notificação não encontrada"}, status=status.HTTP_404_NOT_FOUND)
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="notifications/read-all")
    def mark_all_read(self, request: Request) -> Response:
        count = Notification.objects.filter(
            recipient=request.user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({"marked_read": count})
```

- [ ] **Step 5: Register tenant URL patterns**

Add to `core/urls.py`:

```python
from core.viewsets.tenant_views import TenantReadViewSet, TenantWriteViewSet, TenantNotificationViewSet

router.register(r"tenant", TenantReadViewSet, basename="tenant-read")
router.register(r"tenant", TenantWriteViewSet, basename="tenant-write")
router.register(r"tenant", TenantNotificationViewSet, basename="tenant-notifications")
```

Note: Multiple viewsets on the same prefix may cause URL conflicts. If needed, combine into a single `TenantViewSet` with all actions.

- [ ] **Step 6: Run tests — verify they pass**

Run: `python -m pytest tests/integration/test_tenant_api.py -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add core/viewsets/tenant_views.py core/serializers.py core/urls.py tests/integration/test_tenant_api.py
git commit -m "feat(tenant-api): add tenant read/write endpoints — me, payments, PIX, proofs, notifications"
```

---

## Task 7: Admin Proofs + WhatsApp Send

**Files:**
- Create: `core/viewsets/proof_views.py`
- Test: `tests/integration/test_admin_proofs_api.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Write tests for admin proof review**

Create `tests/integration/test_admin_proofs_api.py`:

```python
import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from core.models import Building, Apartment, Tenant, Lease, PaymentProof


@pytest.fixture
def proof_setup(admin_user):
    building = Building.objects.create(
        street_number="300", name="Proof Test",
        created_by=admin_user, updated_by=admin_user,
    )
    apartment = Apartment.objects.create(
        building=building, number=301, rental_value=Decimal("1000.00"),
        cleaning_fee=Decimal("100.00"), max_tenants=2,
        created_by=admin_user, updated_by=admin_user,
    )
    tenant = Tenant.objects.create(
        name="Proof Tenant", cpf_cnpj="11122233344", phone="(11) 77777-6666",
        marital_status="Solteiro(a)", due_day=10,
        created_by=admin_user, updated_by=admin_user,
    )
    lease = Lease.objects.create(
        apartment=apartment, responsible_tenant=tenant,
        start_date=timezone.now().date(), validity_months=12,
        rental_value=Decimal("1000.00"), number_of_tenants=1,
        created_by=admin_user, updated_by=admin_user,
    )
    proof = PaymentProof.objects.create(
        lease=lease, reference_month=timezone.now().date().replace(day=1),
        file=SimpleUploadedFile("proof.jpg", b"fake_image", content_type="image/jpeg"),
        status="pending",
        created_by=admin_user, updated_by=admin_user,
    )
    return proof


@pytest.mark.integration
@pytest.mark.django_db
class TestAdminProofs:
    def test_list_pending_proofs(self, authenticated_api_client, proof_setup):
        response = authenticated_api_client.get("/api/admin/proofs/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_approve_proof(self, authenticated_api_client, proof_setup):
        response = authenticated_api_client.post(
            f"/api/admin/proofs/{proof_setup.pk}/review/",
            {"action": "approve"},
        )
        assert response.status_code == 200
        proof_setup.refresh_from_db()
        assert proof_setup.status == "approved"

    def test_reject_proof(self, authenticated_api_client, proof_setup):
        response = authenticated_api_client.post(
            f"/api/admin/proofs/{proof_setup.pk}/review/",
            {"action": "reject", "reason": "Comprovante ilegível"},
        )
        assert response.status_code == 200
        proof_setup.refresh_from_db()
        assert proof_setup.status == "rejected"
        assert proof_setup.rejection_reason == "Comprovante ilegível"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `python -m pytest tests/integration/test_admin_proofs_api.py -v`

- [ ] **Step 3: Implement proof_views.py**

Create `core/viewsets/proof_views.py`:

```python
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import PaymentProof
from core.pagination import CustomPageNumberPagination
from core.serializers import PaymentProofSerializer


class AdminProofViewSet(ViewSet):
    """Admin endpoints for reviewing payment proofs."""

    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        status_filter = request.query_params.get("status", "pending")
        proofs = (
            PaymentProof.objects
            .filter(status=status_filter)
            .select_related("lease", "lease__apartment", "lease__apartment__building", "lease__responsible_tenant")
            .order_by("-created_at")
        )
        paginator = CustomPageNumberPagination()
        page = paginator.paginate_queryset(proofs, request)
        serializer = PaymentProofSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request: Request, pk: int = None) -> Response:
        try:
            proof = PaymentProof.objects.get(pk=pk)
        except PaymentProof.DoesNotExist:
            return Response({"error": "Comprovante não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        action_type = request.data.get("action")
        if action_type not in ("approve", "reject"):
            return Response(
                {"error": "action deve ser 'approve' ou 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()

        if action_type == "approve":
            proof.status = "approved"
        else:
            proof.status = "rejected"
            proof.rejection_reason = request.data.get("reason", "")

        proof.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason"])

        # Send notification to tenant
        from core.services.notification_service import notify_proof_reviewed
        notify_proof_reviewed(proof)

        return Response(PaymentProofSerializer(proof).data)
```

- [ ] **Step 4: Register URL patterns**

Add to `core/urls.py`:

```python
from core.viewsets.proof_views import AdminProofViewSet

router.register(r"admin/proofs", AdminProofViewSet, basename="admin-proofs")
```

- [ ] **Step 5: Run tests — verify they pass**

Run: `python -m pytest tests/integration/test_admin_proofs_api.py -v`

- [ ] **Step 6: Commit**

```bash
git add core/viewsets/proof_views.py tests/integration/test_admin_proofs_api.py core/urls.py
git commit -m "feat(admin): add payment proof review endpoints"
```

---

## Task 8: Device Token Endpoints

**Files:**
- Create: `core/viewsets/device_views.py`
- Test: `tests/integration/test_device_api.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Write tests**

Create `tests/integration/test_device_api.py`:

```python
import pytest
from rest_framework.test import APIClient
from core.models import DeviceToken


@pytest.mark.integration
@pytest.mark.django_db
class TestDeviceToken:
    def test_register_token(self, authenticated_api_client, admin_user):
        response = authenticated_api_client.post("/api/devices/register/", {
            "token": "ExponentPushToken[xxxx]",
            "platform": "android",
        })
        assert response.status_code == 201
        assert DeviceToken.objects.filter(user=admin_user, token="ExponentPushToken[xxxx]").exists()

    def test_register_duplicate_updates(self, authenticated_api_client, admin_user):
        authenticated_api_client.post("/api/devices/register/", {
            "token": "ExponentPushToken[yyyy]", "platform": "ios",
        })
        authenticated_api_client.post("/api/devices/register/", {
            "token": "ExponentPushToken[yyyy]", "platform": "ios",
        })
        assert DeviceToken.objects.filter(token="ExponentPushToken[yyyy]").count() == 1

    def test_unregister_token(self, authenticated_api_client, admin_user):
        DeviceToken.objects.create(
            user=admin_user, token="ExponentPushToken[zzzz]", platform="android",
            created_by=admin_user, updated_by=admin_user,
        )
        response = authenticated_api_client.post("/api/devices/unregister/", {
            "token": "ExponentPushToken[zzzz]",
        })
        assert response.status_code == 200
        assert not DeviceToken.objects.filter(token="ExponentPushToken[zzzz]", is_active=True).exists()
```

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Implement device_views.py**

Create `core/viewsets/device_views.py`:

```python
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.models import DeviceToken


class DeviceTokenViewSet(ViewSet):
    """Register/unregister Expo push notification tokens."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="register")
    def register_token(self, request: Request) -> Response:
        token = request.data.get("token", "").strip()
        platform = request.data.get("platform", "").strip()

        if not token or not platform:
            return Response(
                {"error": "token e platform são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if platform not in ("ios", "android"):
            return Response(
                {"error": "platform deve ser 'ios' ou 'android'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": platform,
                "is_active": True,
                "created_by": request.user,
                "updated_by": request.user,
            },
        )
        return Response(
            {"id": device.pk, "token": device.token, "platform": device.platform},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="unregister")
    def unregister_token(self, request: Request) -> Response:
        token = request.data.get("token", "").strip()
        if not token:
            return Response({"error": "token é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        updated = DeviceToken.objects.filter(token=token, user=request.user).update(is_active=False)
        if updated == 0:
            return Response({"error": "Token não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Token removido"})
```

- [ ] **Step 4: Register URLs**

```python
from core.viewsets.device_views import DeviceTokenViewSet
router.register(r"devices", DeviceTokenViewSet, basename="devices")
```

- [ ] **Step 5: Run tests — verify they pass**

- [ ] **Step 6: Commit**

```bash
git add core/viewsets/device_views.py tests/integration/test_device_api.py core/urls.py
git commit -m "feat(devices): add device token register/unregister endpoints"
```

---

## Task 9: Notification Service

**Files:**
- Create: `core/services/notification_service.py`
- Test: `tests/unit/test_notification_service.py`

- [ ] **Step 1: Write tests**

Create `tests/unit/test_notification_service.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Notification


@pytest.mark.unit
@pytest.mark.django_db
class TestNotificationService:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(username="notif_test")

    def test_create_notification(self, user):
        from core.services.notification_service import create_notification

        notif = create_notification(
            recipient=user,
            notification_type="due_reminder",
            title="Vencimento próximo",
            body="Seu aluguel vence em 3 dias",
        )
        assert notif.pk is not None
        assert notif.recipient == user
        assert notif.type == "due_reminder"
        assert notif.is_read is False

    @patch("core.services.notification_service.requests.post")
    def test_send_push_calls_expo_api(self, mock_post, user):
        from core.models import DeviceToken
        DeviceToken.objects.create(
            user=user, token="ExponentPushToken[test]", platform="android",
            created_by=user, updated_by=user,
        )
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"data": [{"status": "ok"}]})

        from core.services.notification_service import send_push_notification
        send_push_notification(user, "Test Title", "Test Body", data={"screen": "home"})

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://exp.host/--/api/v2/push/send" in call_args[0][0]

    def test_is_idempotent(self, user):
        from core.services.notification_service import create_notification, is_notification_sent_today

        create_notification(
            recipient=user,
            notification_type="due_reminder",
            title="Test",
            body="Test",
        )
        assert is_notification_sent_today(user, "due_reminder") is True
        assert is_notification_sent_today(user, "overdue") is False
```

- [ ] **Step 2: Run tests — verify they fail**

- [ ] **Step 3: Implement notification_service.py**

Create `core/services/notification_service.py`:

```python
from datetime import date

import requests
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import DeviceToken, Notification


def create_notification(
    recipient: User,
    notification_type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    """Create an in-app notification and send push."""
    notif = Notification.objects.create(
        recipient=recipient,
        type=notification_type,
        title=title,
        body=body,
        sent_at=timezone.now(),
        data=data,
    )
    # Fire-and-forget push
    send_push_notification(recipient, title, body, data)
    return notif


def send_push_notification(
    user: User,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    """Send push notification via Expo Push API to all active devices."""
    tokens = list(
        DeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    )
    if not tokens:
        return

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "data": data or {},
            "sound": "default",
        }
        for token in tokens
    ]

    try:
        requests.post(
            "https://exp.host/--/api/v2/push/send",
            json=messages,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
    except requests.RequestException:
        pass  # Push failures are non-critical; log in production


def is_notification_sent_today(user: User, notification_type: str) -> bool:
    """Check if a notification of this type was already sent today (idempotency)."""
    today = timezone.now().date()
    return Notification.objects.filter(
        recipient=user,
        type=notification_type,
        sent_at__date=today,
    ).exists()


def notify_new_proof(proof) -> None:
    """Notify admins that a new payment proof was uploaded."""
    from django.contrib.auth.models import User as AuthUser

    admins = AuthUser.objects.filter(is_staff=True, is_active=True)
    tenant_name = proof.lease.responsible_tenant.name
    apt = proof.lease.apartment

    for admin in admins:
        create_notification(
            recipient=admin,
            notification_type="new_proof",
            title="Novo comprovante",
            body=f"{tenant_name} enviou comprovante para apto {apt.number} ({proof.reference_month:%m/%Y})",
            data={"screen": "proofs", "proof_id": proof.pk},
        )


def notify_proof_reviewed(proof) -> None:
    """Notify tenant that their proof was approved/rejected."""
    tenant = proof.lease.responsible_tenant
    if not tenant.user:
        return

    if proof.status == "approved":
        create_notification(
            recipient=tenant.user,
            notification_type="proof_approved",
            title="Comprovante aprovado",
            body=f"Seu comprovante de {proof.reference_month:%m/%Y} foi aprovado.",
            data={"screen": "payments"},
        )
    elif proof.status == "rejected":
        reason = proof.rejection_reason or "Motivo não informado"
        create_notification(
            recipient=tenant.user,
            notification_type="proof_rejected",
            title="Comprovante rejeitado",
            body=f"Seu comprovante de {proof.reference_month:%m/%Y} foi rejeitado: {reason}",
            data={"screen": "payments"},
        )
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `python -m pytest tests/unit/test_notification_service.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/services/notification_service.py tests/unit/test_notification_service.py
git commit -m "feat(notifications): add notification service with Expo Push API integration"
```

---

## Task 10: Scheduled Notifications Management Command

**Files:**
- Create: `core/management/commands/send_scheduled_notifications.py`
- Create: `core/management/__init__.py` (if needed)
- Create: `core/management/commands/__init__.py` (if needed)

- [ ] **Step 1: Create management command directory**

Run: `mkdir -p core/management/commands && touch core/management/__init__.py core/management/commands/__init__.py`

- [ ] **Step 2: Implement the management command**

Create `core/management/commands/send_scheduled_notifications.py`:

```python
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Lease, Tenant
from core.services.notification_service import create_notification, is_notification_sent_today


class Command(BaseCommand):
    help = "Send scheduled notifications (due reminders, overdue alerts, contract expiry)"

    def handle(self, *args, **options):
        today = timezone.now().date()
        self.stdout.write(f"Processing scheduled notifications for {today}")

        self._send_due_reminders(today)
        self._send_due_today(today)
        self._send_overdue(today)
        self._send_contract_expiring(today)

        self.stdout.write(self.style.SUCCESS("Done"))

    def _send_due_reminders(self, today):
        """Send reminders 3 days before due date."""
        target_day = (today + timedelta(days=3)).day
        leases = Lease.objects.filter(is_deleted=False).select_related(
            "responsible_tenant", "responsible_tenant__user",
        )
        for lease in leases:
            tenant = lease.responsible_tenant
            if not tenant.user or tenant.due_day != target_day:
                continue
            if is_notification_sent_today(tenant.user, "due_reminder"):
                continue
            create_notification(
                recipient=tenant.user,
                notification_type="due_reminder",
                title="Lembrete de vencimento",
                body=f"Seu aluguel de R$ {lease.rental_value:,.2f} vence em 3 dias.",
                data={"screen": "payments"},
            )
            self.stdout.write(f"  due_reminder → {tenant.name}")

    def _send_due_today(self, today):
        """Send notification on the due date."""
        leases = Lease.objects.filter(is_deleted=False).select_related(
            "responsible_tenant", "responsible_tenant__user",
        )
        for lease in leases:
            tenant = lease.responsible_tenant
            if not tenant.user or tenant.due_day != today.day:
                continue
            if is_notification_sent_today(tenant.user, "due_today"):
                continue
            create_notification(
                recipient=tenant.user,
                notification_type="due_today",
                title="Aluguel vence hoje",
                body=f"Seu aluguel de R$ {lease.rental_value:,.2f} vence hoje.",
                data={"screen": "payments"},
            )
            self.stdout.write(f"  due_today → {tenant.name}")

    def _send_overdue(self, today):
        """Send overdue notifications at 1, 5, 15 days late."""
        leases = Lease.objects.filter(is_deleted=False).select_related(
            "responsible_tenant", "responsible_tenant__user",
        )
        for lease in leases:
            tenant = lease.responsible_tenant
            if not tenant.user:
                continue
            # Calculate days since due date this month
            try:
                due_date = today.replace(day=tenant.due_day)
            except ValueError:
                continue  # due_day > days in month
            if due_date >= today:
                continue  # not overdue yet

            days_late = (today - due_date).days
            if days_late not in (1, 5, 15):
                continue
            if is_notification_sent_today(tenant.user, "overdue"):
                continue

            # Check if rent was paid this month
            from core.models import RentPayment
            if RentPayment.objects.filter(
                lease=lease, reference_month=today.replace(day=1),
            ).exists():
                continue

            create_notification(
                recipient=tenant.user,
                notification_type="overdue",
                title="Aluguel atrasado",
                body=f"Seu aluguel está {days_late} dia(s) atrasado.",
                data={"screen": "payments"},
            )
            self.stdout.write(f"  overdue ({days_late}d) → {tenant.name}")

    def _send_contract_expiring(self, today):
        """Notify admins 30 days before contract expiry."""
        from django.contrib.auth.models import User

        target_date = today + timedelta(days=30)
        leases = Lease.objects.filter(is_deleted=False).select_related(
            "responsible_tenant", "apartment", "apartment__building",
        )
        admins = list(User.objects.filter(is_staff=True, is_active=True))

        for lease in leases:
            from dateutil.relativedelta import relativedelta
            end_date = lease.start_date + relativedelta(months=lease.validity_months)
            if end_date != target_date:
                continue

            for admin in admins:
                if is_notification_sent_today(admin, "contract_expiring"):
                    continue
                apt = lease.apartment
                create_notification(
                    recipient=admin,
                    notification_type="contract_expiring",
                    title="Contrato vencendo",
                    body=f"Contrato do apto {apt.number} ({apt.building.name}) vence em 30 dias.",
                    data={"screen": "properties", "lease_id": lease.pk},
                )
            self.stdout.write(f"  contract_expiring → {lease}")
```

- [ ] **Step 3: Verify the command runs**

Run: `python manage.py send_scheduled_notifications`
Expected: "Processing scheduled notifications for YYYY-MM-DD" + "Done"

- [ ] **Step 4: Commit**

```bash
git add core/management/
git commit -m "feat(notifications): add send_scheduled_notifications management command"
```

---

## Task 11: Update Serializers for PIX Fields

**Files:**
- Modify: `core/serializers.py`

- [ ] **Step 1: Add pix_key fields to PersonSerializer**

In `PersonSerializer.Meta.fields`, add `"pix_key"` and `"pix_key_type"`.

- [ ] **Step 2: Add default_pix_key fields to FinancialSettingsSerializer**

In `FinancialSettingsSerializer.Meta.fields`, add `"default_pix_key"` and `"default_pix_key_type"`.

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `python -m pytest tests/ -x --timeout=60`
Expected: All existing tests pass

- [ ] **Step 4: Run type checking**

Run: `ruff check && mypy core/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add core/serializers.py
git commit -m "feat(serializers): add PIX key fields to Person and FinancialSettings serializers"
```

---

## Task 12: MEDIA_ROOT Configuration

**Files:**
- Modify: `condominios_manager/settings.py`
- Modify: `condominios_manager/urls.py`

- [ ] **Step 1: Configure MEDIA settings**

Add to `condominios_manager/settings.py`:

```python
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# File upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

- [ ] **Step 2: Add .gitignore for media/**

Create `media/.gitignore`:
```
*
!.gitignore
```

- [ ] **Step 3: Commit**

```bash
git add condominios_manager/settings.py media/.gitignore
git commit -m "chore(config): add MEDIA_ROOT for payment proof uploads"
```

---

## Self-Review Checklist

### Spec Coverage
- [x] WhatsAppVerification model — Task 1
- [x] DeviceToken model — Task 1
- [x] PaymentProof model — Task 1
- [x] Notification model — Task 1
- [x] PIX fields on Person/FinancialSettings — Task 1, 11
- [x] IsTenantUser, HasActiveLease permissions — Task 2
- [x] DailyControlViewSet permission fix — Task 2
- [x] WhatsApp service (Twilio) — Task 3
- [x] Tenant auth (request/verify) — Task 4
- [x] Set-password endpoint — Task 4
- [x] PIX service — Task 5
- [x] Tenant /me endpoint — Task 6
- [x] Tenant contract PDF — Task 6
- [x] Tenant payments list — Task 6
- [x] Tenant rent adjustments — Task 6
- [x] Tenant PIX generation — Task 6
- [x] Tenant proof upload — Task 6
- [x] Tenant due-date simulate — Task 6
- [x] Tenant notifications (list, read, read-all) — Task 6
- [x] Admin proof review — Task 7
- [x] Device token register/unregister — Task 8
- [x] Notification service — Task 9
- [x] Scheduled notifications command — Task 10
- [x] Serializer updates — Task 11
- [x] MEDIA_ROOT config — Task 12

### Not in this plan (deferred to mobile plans)
- Admin WhatsApp send endpoint (Task 7 of spec) — can be added when admin mobile screens are built
- Rate limiting at Django level (can use django-ratelimit if needed)
- Tenant model related_name verification (Step 6 of Task 2)
