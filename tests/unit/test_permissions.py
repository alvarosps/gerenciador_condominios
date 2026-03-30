"""Unit tests for core/permissions.py.

Tests all permission classes with admin, regular user, and unauthenticated
scenarios.  Uses real instances — no mocks of internal code.
"""

from unittest.mock import MagicMock

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from core.permissions import (
    CanGenerateContract,
    CanModifyLease,
    FinancialReadOnly,
    HasActiveLease,
    IsAdminUser,
    IsAuthenticatedAndActive,
    IsAuthenticatedOrReadOnly,
    IsOwnerOrAdmin,
    IsTenantOrAdmin,
    IsTenantUser,
    ReadOnlyForNonAdmin,
    get_permission_classes,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_request(method: str, user=None):
    """Build a DRF Request with the given HTTP method and user."""
    factory = APIRequestFactory()
    raw = getattr(factory, method.lower())("/")
    request = Request(raw)
    if user is not None:
        request.user = user
    return request


class _Obj:
    """Minimal object stub for object-level permission tests."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# IsAuthenticatedOrReadOnly
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsAuthenticatedOrReadOnly:
    perm = IsAuthenticatedOrReadOnly()

    def test_get_allows_unauthenticated(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False})()
        assert self.perm.has_permission(request, None) is True

    def test_post_requires_authentication(self):
        request = make_request("POST")
        request.user = type("U", (), {"is_authenticated": False})()
        assert self.perm.has_permission(request, None) is False

    def test_post_allows_authenticated(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is True


# ---------------------------------------------------------------------------
# IsAdminUser
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsAdminUser:
    perm = IsAdminUser()

    def test_admin_allowed(self, admin_user):
        request = make_request("GET")
        request.user = admin_user
        assert self.perm.has_permission(request, None) is True

    def test_regular_user_denied(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is False

    def test_unauthenticated_denied(self):
        request = make_request("GET")
        request.user = type(
            "U", (), {"is_authenticated": False, "is_staff": False, "is_superuser": False}
        )()
        assert self.perm.has_permission(request, None) is False


# ---------------------------------------------------------------------------
# IsOwnerOrAdmin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsOwnerOrAdmin:
    perm = IsOwnerOrAdmin()

    def test_admin_can_access_any_object(self, admin_user):
        request = make_request("GET")
        request.user = admin_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_owner_can_access_their_object(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        obj = _Obj(user=regular_user)
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_non_owner_denied(self, regular_user, admin_user):
        request = make_request("GET")
        request.user = regular_user
        obj = _Obj(user=admin_user)  # owned by admin
        assert self.perm.has_object_permission(request, None, obj) is False

    def test_created_by_owner_check(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        obj = _Obj(created_by=regular_user)
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_no_ownership_field_denied(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        obj = _Obj()  # no user or created_by field
        assert self.perm.has_object_permission(request, None, obj) is False


# ---------------------------------------------------------------------------
# IsTenantOrAdmin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsTenantOrAdmin:
    perm = IsTenantOrAdmin()

    def test_admin_can_access_any_lease(self, admin_user):
        request = make_request("GET")
        request.user = admin_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_regular_user_without_tenant_link_denied(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        # obj.tenants.all() returns empty iterable
        obj = _Obj(tenants=type("M2M", (), {"all": lambda self: []})())
        obj.responsible_tenant = _Obj()  # no user attr
        assert self.perm.has_object_permission(request, None, obj) is False


# ---------------------------------------------------------------------------
# FinancialReadOnly
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFinancialReadOnly:
    perm = FinancialReadOnly()

    def test_authenticated_user_can_read(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is True

    def test_unauthenticated_denied(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False})()
        assert self.perm.has_permission(request, None) is False

    def test_regular_user_cannot_write(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is False

    def test_admin_user_can_write(self, admin_user):
        request = make_request("POST")
        request.user = admin_user
        assert self.perm.has_permission(request, None) is True


# ---------------------------------------------------------------------------
# ReadOnlyForNonAdmin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadOnlyForNonAdmin:
    perm = ReadOnlyForNonAdmin()

    def test_unauthenticated_denied_even_for_read(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False})()
        assert self.perm.has_permission(request, None) is False

    def test_regular_user_can_read(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is True

    def test_regular_user_cannot_write(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is False

    def test_admin_can_write(self, admin_user):
        request = make_request("POST")
        request.user = admin_user
        assert self.perm.has_permission(request, None) is True

    def test_admin_can_read(self, admin_user):
        request = make_request("GET")
        request.user = admin_user
        assert self.perm.has_permission(request, None) is True


# ---------------------------------------------------------------------------
# CanGenerateContract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCanGenerateContract:
    perm = CanGenerateContract()

    def test_admin_can_generate(self, admin_user):
        request = make_request("POST")
        request.user = admin_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_regular_user_without_responsible_tenant_denied(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        obj = _Obj()  # no responsible_tenant
        assert self.perm.has_object_permission(request, None, obj) is False

    def test_regular_user_with_responsible_tenant_no_user_attr_denied(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        responsible = _Obj()  # no user attribute
        obj = _Obj(responsible_tenant=responsible)
        assert self.perm.has_object_permission(request, None, obj) is False


# ---------------------------------------------------------------------------
# CanModifyLease
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCanModifyLease:
    perm = CanModifyLease()

    def test_unauthenticated_denied(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False})()
        assert self.perm.has_permission(request, None) is False

    def test_regular_user_can_read(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is True

    def test_regular_user_cannot_write(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is False

    def test_admin_can_write(self, admin_user):
        request = make_request("POST")
        request.user = admin_user
        assert self.perm.has_permission(request, None) is True

    def test_object_permission_admin_read(self, admin_user):
        request = make_request("GET")
        request.user = admin_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_object_permission_regular_user_read_no_tenant_link(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        obj = _Obj(tenants=type("M2M", (), {"all": lambda self: []})())
        assert self.perm.has_object_permission(request, None, obj) is False

    def test_object_permission_regular_user_write_denied(self, regular_user):
        request = make_request("POST")
        request.user = regular_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is False

    def test_object_permission_admin_write_allowed(self, admin_user):
        request = make_request("POST")
        request.user = admin_user
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is True

    def test_object_permission_unauthenticated_denied(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False})()
        obj = _Obj()
        assert self.perm.has_object_permission(request, None, obj) is False


# ---------------------------------------------------------------------------
# IsAuthenticatedAndActive
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsAuthenticatedAndActive:
    perm = IsAuthenticatedAndActive()

    def test_active_authenticated_user_allowed(self, regular_user):
        request = make_request("GET")
        request.user = regular_user
        assert self.perm.has_permission(request, None) is True

    def test_unauthenticated_denied(self):
        request = make_request("GET")
        request.user = type("U", (), {"is_authenticated": False, "is_active": False})()
        assert self.perm.has_permission(request, None) is False

    def test_inactive_user_denied(self, django_user_model):
        inactive = django_user_model.objects.create_user(
            username="inactive_perm_test",
            password="pass",
            is_active=False,
        )
        request = make_request("GET")
        request.user = inactive
        assert self.perm.has_permission(request, None) is False


# ---------------------------------------------------------------------------
# get_permission_classes helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetPermissionClasses:
    def test_returns_list_for_known_type(self):
        classes = get_permission_classes("admin_only")
        assert isinstance(classes, list)
        assert IsAdminUser in classes

    def test_returns_default_for_unknown_type(self):
        classes = get_permission_classes("nonexistent_key")
        assert isinstance(classes, list)
        assert len(classes) > 0

    def test_financial_read_only_type(self):
        classes = get_permission_classes("financial_read_only")
        assert FinancialReadOnly in classes


# ---------------------------------------------------------------------------
# IsTenantUser
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# HasActiveLease
# ---------------------------------------------------------------------------


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
