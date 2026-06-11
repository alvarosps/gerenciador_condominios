"""Integration tests for the tenant×admin permission segregation (Plan P1.2).

Closes the leak where an OTP-authenticated tenant (is_staff=False) could read the
PII of every tenant, every lease, and the entire financial module. Asserts:

- ``GET /api/tenants/`` is scoped to the requesting tenant when non-staff.
- ``GET /api/leases/`` is scoped to the requesting tenant's own leases.
- A tenant cannot retrieve or act on another tenant's lease (404 — queryset scope).
- Every finances/ and legacy core financial endpoint returns 403 for a non-staff user.
- Staff keep full read/write access (no admin regression).
- A superuser without is_staff is treated as admin (single IsAdminUser semantics).
- The tenant portal (/api/tenant/*) keeps working (not touched).
- Login sets a ``role`` cookie; logout clears it.

Fronteira = HTTP via APIClient; no mocking of ORM/services.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Apartment, Building, Lease, Tenant
from tests.constants import TEST_PASSWORD

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _make_tenant_setup(
    admin_user,
    django_user_model,
    street_number: int,
    apt_number: int,
    cpf_cnpj: str,
    tenant_username: str,
) -> dict:
    """Create building, apartment, tenant, lease, and a linked non-staff user."""
    building = Building.objects.create(
        street_number=street_number,
        name=f"Edifício Seg {street_number}",
        address=f"Rua Seg, {street_number}",
        created_by=admin_user,
        updated_by=admin_user,
    )
    apartment = Apartment.objects.create(
        building=building,
        number=apt_number,
        rental_value=Decimal("1500.00"),
        max_tenants=2,
        created_by=admin_user,
        updated_by=admin_user,
    )
    tenant = Tenant.objects.create(
        name=f"Inquilino {street_number}",
        cpf_cnpj=cpf_cnpj,
        phone=f"119{street_number:07d}",
        marital_status="Solteiro(a)",
        profession="Analista",
        due_day=10,
        created_by=admin_user,
        updated_by=admin_user,
    )
    lease = Lease.objects.create(
        apartment=apartment,
        responsible_tenant=tenant,
        start_date=date(2026, 1, 1),
        validity_months=12,
        rental_value=Decimal("1500.00"),
        number_of_tenants=1,
        created_by=admin_user,
        updated_by=admin_user,
    )
    user = django_user_model.objects.create_user(
        username=tenant_username,
        password=TEST_PASSWORD,
        is_staff=False,
        is_active=True,
    )
    tenant.user = user
    tenant.save(update_fields=["user"])

    return {
        "building": building,
        "apartment": apartment,
        "tenant": tenant,
        "lease": lease,
        "user": user,
    }


@pytest.fixture
def tenant_a(admin_user, django_user_model):
    return _make_tenant_setup(
        admin_user,
        django_user_model,
        street_number=7701,
        apt_number=101,
        cpf_cnpj="52998224725",
        tenant_username="seg_tenant_a",
    )


@pytest.fixture
def tenant_b(admin_user, django_user_model):
    return _make_tenant_setup(
        admin_user,
        django_user_model,
        street_number=7702,
        apt_number=201,
        cpf_cnpj="29375235017",
        tenant_username="seg_tenant_b",
    )


@pytest.fixture
def tenant_a_client(api_client, tenant_a):
    api_client.force_authenticate(user=tenant_a["user"])
    return api_client


# ---------------------------------------------------------------------------
# Tenant queryset scoping — tenants
# ---------------------------------------------------------------------------


class TestTenantQuerysetScope:
    def test_tenant_lists_only_own_tenant_record(self, tenant_a_client, tenant_a, tenant_b):
        """A non-staff tenant on GET /api/tenants/ sees only their own record."""
        response = tenant_a_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [tenant_a["tenant"].pk]
        assert tenant_b["tenant"].pk not in ids

    def test_tenant_cannot_retrieve_other_tenant_record(self, tenant_a_client, tenant_b):
        """A tenant retrieving another tenant's record gets 404 (queryset scope)."""
        response = tenant_a_client.get(f"/api/tenants/{tenant_b['tenant'].pk}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_lists_all_tenants(self, authenticated_api_client, tenant_a, tenant_b):
        """Staff sees every tenant (admin not broken)."""
        response = authenticated_api_client.get("/api/tenants/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant_a["tenant"].pk in ids
        assert tenant_b["tenant"].pk in ids


# ---------------------------------------------------------------------------
# Lease queryset scoping
# ---------------------------------------------------------------------------


class TestLeaseQuerysetScope:
    def test_tenant_lists_only_own_leases(self, tenant_a_client, tenant_a, tenant_b):
        """A non-staff tenant on GET /api/leases/ sees only leases where responsible."""
        response = tenant_a_client.get("/api/leases/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [tenant_a["lease"].pk]
        assert tenant_b["lease"].pk not in ids

    def test_tenant_cannot_retrieve_other_tenant_lease(self, tenant_a_client, tenant_b):
        """GET /api/leases/{other}/ → 404 because the lease is outside the scope."""
        response = tenant_a_client.get(f"/api/leases/{tenant_b['lease'].pk}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_tenant_cannot_generate_contract_for_other_lease(self, tenant_a_client, tenant_b):
        """POST /api/leases/{other}/generate_contract/ → 404 (scope fires before action)."""
        response = tenant_a_client.post(
            f"/api/leases/{tenant_b['lease'].pk}/generate_contract/", {}, format="json"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_sees_all_leases(self, authenticated_api_client, tenant_a, tenant_b):
        response = authenticated_api_client.get("/api/leases/")
        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert tenant_a["lease"].pk in ids
        assert tenant_b["lease"].pk in ids


# ---------------------------------------------------------------------------
# Financial endpoints locked to is_staff
# ---------------------------------------------------------------------------

FINANCES_READ_ENDPOINTS = [
    "/api/finances/bills/",
    "/api/finances/finance-categories/",
    "/api/finances/billing-accounts/",
    "/api/finances/reserves/",
    "/api/finances/income-entries/",
    "/api/finances/condo-month-closes/",
    "/api/finances/installment-plans/",
    "/api/finances/employees/",
    "/api/finances/finance-dashboard/combined_calendar/",
    "/api/finances/finance-dashboard/overdue/",
    "/api/finances/finance-cash-flow/projection/?months=3",
]

LEGACY_FINANCIAL_READ_ENDPOINTS = [
    "/api/persons/",
    "/api/expenses/",
    "/api/expense-categories/",
    "/api/incomes/",
    "/api/rent-payments/",
    "/api/financial-dashboard/overview/",
    "/api/financial-settings/current/",
]


class TestFinancesLockedToStaff:
    @pytest.mark.parametrize("url", FINANCES_READ_ENDPOINTS)
    def test_tenant_gets_403_on_finances(self, tenant_a_client, url):
        assert tenant_a_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("url", LEGACY_FINANCIAL_READ_ENDPOINTS)
    def test_tenant_gets_403_on_legacy_financial(self, tenant_a_client, url):
        assert tenant_a_client.get(url).status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("url", FINANCES_READ_ENDPOINTS)
    def test_staff_reads_finances_ok(self, authenticated_api_client, url):
        assert authenticated_api_client.get(url).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("url", LEGACY_FINANCIAL_READ_ENDPOINTS)
    def test_staff_reads_legacy_financial_ok(self, authenticated_api_client, url):
        assert authenticated_api_client.get(url).status_code == status.HTTP_200_OK

    def test_regular_user_without_tenant_also_403(self, regular_authenticated_api_client):
        """A non-staff user with no tenant link is equally locked out of finances."""
        assert (
            regular_authenticated_api_client.get("/api/finances/bills/").status_code
            == status.HTTP_403_FORBIDDEN
        )


# ---------------------------------------------------------------------------
# Single IsAdminUser semantics — superuser without is_staff is admin
# ---------------------------------------------------------------------------


class TestSuperuserNonStaffIsAdmin:
    def test_superuser_non_staff_reads_finances(self, api_client, django_user_model):
        superuser = django_user_model.objects.create_user(
            username="superuser_non_staff",
            password=TEST_PASSWORD,
            is_staff=False,
            is_superuser=True,
            is_active=True,
        )
        api_client.force_authenticate(user=superuser)
        assert api_client.get("/api/finances/bills/").status_code == status.HTTP_200_OK

    def test_superuser_non_staff_reads_month_advance(self, api_client, django_user_model):
        superuser = django_user_model.objects.create_user(
            username="superuser_month_advance",
            password=TEST_PASSWORD,
            is_staff=False,
            is_superuser=True,
            is_active=True,
        )
        api_client.force_authenticate(user=superuser)
        response = api_client.get("/api/month-advance/snapshots/")
        assert response.status_code == status.HTTP_200_OK

    def test_tenant_non_staff_blocked_from_month_advance(self, tenant_a_client):
        assert (
            tenant_a_client.get("/api/month-advance/snapshots/").status_code
            == status.HTTP_403_FORBIDDEN
        )


# ---------------------------------------------------------------------------
# Tenant portal untouched
# ---------------------------------------------------------------------------


class TestTenantPortalStillWorks:
    def test_tenant_portal_me_ok(self, tenant_a_client, tenant_a):
        response = tenant_a_client.get("/api/tenant/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tenant_a["tenant"].pk

    def test_tenant_portal_payments_ok(self, tenant_a_client):
        response = tenant_a_client.get("/api/tenant/payments/")
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Role cookie on login / logout
# ---------------------------------------------------------------------------


class TestRoleCookie:
    def test_login_sets_role_staff_cookie(self, admin_user):
        admin_user.set_password(TEST_PASSWORD)
        admin_user.save(update_fields=["password"])
        client = APIClient()
        response = client.post(
            "/api/auth/token/",
            {"username": admin_user.username, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.cookies["role"].value == "staff"
        assert response.cookies["is_authenticated"].value == "1"
        assert response.cookies["role"]["httponly"] == ""

    def test_login_sets_role_tenant_cookie_for_non_staff(self, tenant_a):
        user = tenant_a["user"]
        user.set_password(TEST_PASSWORD)
        user.save(update_fields=["password"])
        client = APIClient()
        response = client.post(
            "/api/auth/token/",
            {"username": user.username, "password": TEST_PASSWORD},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.cookies["role"].value == "tenant"

    def test_logout_clears_role_cookie(self, admin_user):
        admin_user.set_password(TEST_PASSWORD)
        admin_user.save(update_fields=["password"])
        client = APIClient()
        login = client.post(
            "/api/auth/token/",
            {"username": admin_user.username, "password": TEST_PASSWORD},
            format="json",
        )
        assert login.status_code == status.HTTP_200_OK

        logout = client.post("/api/auth/logout/")
        assert logout.status_code == status.HTTP_204_NO_CONTENT
        # delete_cookie sets an empty value with an expiry in the past.
        assert logout.cookies["role"].value == ""
