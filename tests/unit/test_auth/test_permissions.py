"""
Unit tests for Custom Permission Classes.

Tests all custom permission classes for proper access control.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

import pytest

from core.models import Building, Lease, Tenant
from core.permissions import (
    CanGenerateContract,
    CanModifyLease,
    IsAdminUser,
    IsAuthenticatedAndActive,
    IsAuthenticatedOrReadOnly,
    IsOwnerOrAdmin,
    IsTenantOrAdmin,
    ReadOnlyForNonAdmin,
)
from tests.fixtures.factories import ApartmentFactory, BuildingFactory, LeaseFactory, TenantFactory

User = get_user_model()


@pytest.mark.django_db
class TestIsAuthenticatedOrReadOnly:
    """Test IsAuthenticatedOrReadOnly permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsAuthenticatedOrReadOnly()
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_allows_read_for_unauthenticated_users(self):
        """Test that unauthenticated users can perform read operations."""
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is True

    def test_denies_write_for_unauthenticated_users(self):
        """Test that unauthenticated users cannot perform write operations."""
        request = self.factory.post("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is False

    def test_allows_read_for_authenticated_users(self):
        """Test that authenticated users can perform read operations."""
        request = self.factory.get("/test/")
        request.user = self.user
        assert self.permission.has_permission(request, None) is True

    def test_allows_write_for_authenticated_users(self):
        """Test that authenticated users can perform write operations."""
        request = self.factory.post("/test/")
        request.user = self.user
        assert self.permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestIsAdminUser:
    """Test IsAdminUser permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsAdminUser()
        self.regular_user = User.objects.create_user(username="regular", password="testpass123")
        self.staff_user = User.objects.create_user(username="staff", password="testpass123", is_staff=True)
        self.superuser = User.objects.create_superuser(username="admin", password="adminpass123")

    def test_denies_unauthenticated_users(self):
        """Test that unauthenticated users are denied."""
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is False

    def test_denies_regular_users(self):
        """Test that regular users are denied."""
        request = self.factory.get("/test/")
        request.user = self.regular_user
        assert self.permission.has_permission(request, None) is False

    def test_allows_staff_users(self):
        """Test that staff users are allowed."""
        request = self.factory.get("/test/")
        request.user = self.staff_user
        assert self.permission.has_permission(request, None) is True

    def test_allows_superusers(self):
        """Test that superusers are allowed."""
        request = self.factory.get("/test/")
        request.user = self.superuser
        assert self.permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestIsOwnerOrAdmin:
    """Test IsOwnerOrAdmin permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrAdmin()
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")

    def test_allows_owner_to_access_own_object(self):
        """Test that owners can access their own objects."""

        # Create a mock object with 'user' attribute
        class MockObject:
            def __init__(self, user):
                self.user = user

        obj = MockObject(user=self.user1)
        request = self.factory.get("/test/")
        request.user = self.user1

        assert self.permission.has_object_permission(request, None, obj) is True

    def test_denies_non_owner_to_access_object(self):
        """Test that non-owners cannot access objects they don't own."""

        class MockObject:
            def __init__(self, user):
                self.user = user

        obj = MockObject(user=self.user1)
        request = self.factory.get("/test/")
        request.user = self.user2

        assert self.permission.has_object_permission(request, None, obj) is False

    def test_allows_admin_to_access_any_object(self):
        """Test that admins can access any object."""

        class MockObject:
            def __init__(self, user):
                self.user = user

        obj = MockObject(user=self.user1)
        request = self.factory.get("/test/")
        request.user = self.admin

        assert self.permission.has_object_permission(request, None, obj) is True

    def test_works_with_created_by_field(self):
        """Test that permission works with 'created_by' field."""

        class MockObject:
            def __init__(self, created_by):
                self.created_by = created_by

        obj = MockObject(created_by=self.user1)
        request = self.factory.get("/test/")
        request.user = self.user1

        assert self.permission.has_object_permission(request, None, obj) is True


@pytest.mark.django_db
class TestReadOnlyForNonAdmin:
    """Test ReadOnlyForNonAdmin permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = ReadOnlyForNonAdmin()
        self.regular_user = User.objects.create_user(username="regular", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")

    def test_denies_unauthenticated_users(self):
        """Test that unauthenticated users are denied."""
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is False

    def test_allows_authenticated_users_to_read(self):
        """Test that authenticated users can read."""
        request = self.factory.get("/test/")
        request.user = self.regular_user
        assert self.permission.has_permission(request, None) is True

    def test_denies_regular_users_to_write(self):
        """Test that regular users cannot write."""
        request = self.factory.post("/test/")
        request.user = self.regular_user
        assert self.permission.has_permission(request, None) is False

    def test_allows_admin_to_write(self):
        """Test that admins can write."""
        request = self.factory.post("/test/")
        request.user = self.admin
        assert self.permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestCanModifyLease:
    """Test CanModifyLease permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = CanModifyLease()
        self.regular_user = User.objects.create_user(username="regular", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")
        self.lease = LeaseFactory()

    def test_denies_unauthenticated_users(self):
        """Test that unauthenticated users are denied."""
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is False

    def test_allows_authenticated_users_to_read(self):
        """Test that authenticated users can read leases."""
        request = self.factory.get("/test/")
        request.user = self.regular_user
        assert self.permission.has_permission(request, None) is True

    def test_denies_regular_users_to_modify(self):
        """Test that regular users cannot modify leases."""
        request = self.factory.put("/test/")
        request.user = self.regular_user
        assert self.permission.has_permission(request, None) is False

    def test_allows_admin_to_modify(self):
        """Test that admins can modify leases."""
        request = self.factory.put("/test/")
        request.user = self.admin
        assert self.permission.has_permission(request, None) is True

    def test_object_permission_for_read(self):
        """Test object-level permission for read operations."""
        request = self.factory.get("/test/")
        request.user = self.regular_user
        # Regular users can read but need additional checks for object access
        assert self.permission.has_permission(request, None) is True

    def test_object_permission_denies_unauthenticated(self):
        """Test object permission denies unauthenticated users."""
        lease = self.lease
        request = self.factory.get("/test/")
        request.user = AnonymousUser()

        assert self.permission.has_object_permission(request, None, lease) is False

    def test_object_permission_allows_admin_read(self):
        """Test object permission allows admin to read."""
        lease = self.lease
        request = self.factory.get("/test/")
        request.user = self.admin

        assert self.permission.has_object_permission(request, None, lease) is True

    def test_object_permission_denies_non_tenant_read(self):
        """Test object permission denies non-tenant users from reading."""
        lease = self.lease
        # Create a different user who is not a tenant
        other_user = User.objects.create_user(username="other", password="testpass123")
        request = self.factory.get("/test/")
        request.user = other_user

        # Should check tenants list but find no match (tenants don't have user field)
        assert self.permission.has_object_permission(request, None, lease) is False

    def test_object_permission_denies_regular_user_write(self):
        """Test object permission denies regular users from writing."""
        lease = self.lease
        request = self.factory.put("/test/")
        request.user = self.regular_user

        assert self.permission.has_object_permission(request, None, lease) is False

    def test_object_permission_allows_admin_write(self):
        """Test object permission allows admin to write."""
        lease = self.lease
        request = self.factory.put("/test/")
        request.user = self.admin

        assert self.permission.has_object_permission(request, None, lease) is True


@pytest.mark.django_db
class TestIsTenantOrAdmin:
    """Test IsTenantOrAdmin permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsTenantOrAdmin()
        self.regular_user = User.objects.create_user(username="regular", password="testpass123")
        self.other_user = User.objects.create_user(username="other", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")

    def test_allows_admin_access(self):
        """Test that admins can access any lease."""
        lease = LeaseFactory()
        request = self.factory.get("/test/")
        request.user = self.admin

        assert self.permission.has_object_permission(request, None, lease) is True

    def test_denies_when_tenant_has_no_user_field(self):
        """Test that access is denied when tenants don't have user field."""
        lease = LeaseFactory()
        # Tenants don't have user field by default (see permission code comment)
        request = self.factory.get("/test/")
        request.user = self.other_user

        # Should check tenants list but find no user match
        assert self.permission.has_object_permission(request, None, lease) is False

    def test_allows_responsible_tenant(self):
        """Test that responsible tenant can access lease."""
        lease = LeaseFactory()
        # Set responsible tenant with user
        lease.responsible_tenant.user = self.regular_user
        lease.responsible_tenant.save()

        request = self.factory.get("/test/")
        request.user = self.regular_user

        assert self.permission.has_object_permission(request, None, lease) is True

    def test_denies_non_tenant_users(self):
        """Test that non-tenants are denied access."""
        lease = LeaseFactory()
        request = self.factory.get("/test/")
        request.user = self.other_user

        assert self.permission.has_object_permission(request, None, lease) is False


@pytest.mark.django_db
class TestCanGenerateContract:
    """Test CanGenerateContract permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = CanGenerateContract()
        self.regular_user = User.objects.create_user(username="regular", password="testpass123")
        self.other_user = User.objects.create_user(username="other", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")

    def test_allows_admin_to_generate(self):
        """Test that admins can generate contracts."""
        lease = LeaseFactory()
        request = self.factory.post("/test/")
        request.user = self.admin

        assert self.permission.has_object_permission(request, None, lease) is True

    def test_allows_responsible_tenant_to_generate(self):
        """Test that responsible tenant can generate contract."""
        lease = LeaseFactory()
        lease.responsible_tenant.user = self.regular_user
        lease.responsible_tenant.save()

        request = self.factory.post("/test/")
        request.user = self.regular_user

        assert self.permission.has_object_permission(request, None, lease) is True

    def test_denies_non_responsible_tenant(self):
        """Test that non-responsible tenants cannot generate."""
        lease = LeaseFactory()
        request = self.factory.post("/test/")
        request.user = self.other_user

        assert self.permission.has_object_permission(request, None, lease) is False

    def test_denies_when_no_responsible_tenant(self):
        """Test that access is denied when lease has no responsible_tenant."""

        # Create a mock object without responsible_tenant
        class MockLease:
            pass

        lease = MockLease()
        request = self.factory.post("/test/")
        request.user = self.regular_user

        assert self.permission.has_object_permission(request, None, lease) is False


@pytest.mark.django_db
class TestIsAuthenticatedAndActive:
    """Test IsAuthenticatedAndActive permission."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.permission = IsAuthenticatedAndActive()
        self.active_user = User.objects.create_user(username="active", password="testpass123", is_active=True)
        self.inactive_user = User.objects.create_user(username="inactive", password="testpass123", is_active=False)

    def test_denies_unauthenticated_users(self):
        """Test that unauthenticated users are denied."""
        request = self.factory.get("/test/")
        request.user = AnonymousUser()
        assert self.permission.has_permission(request, None) is False

    def test_allows_active_authenticated_users(self):
        """Test that active authenticated users are allowed."""
        request = self.factory.get("/test/")
        request.user = self.active_user
        assert self.permission.has_permission(request, None) is True

    def test_denies_inactive_users(self):
        """Test that inactive users are denied."""
        request = self.factory.get("/test/")
        request.user = self.inactive_user
        assert self.permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestGetPermissionClasses:
    """Test get_permission_classes helper function."""

    def test_returns_default_for_unknown_type(self):
        """Test that unknown types return authenticated default."""
        from core.permissions import get_permission_classes

        result = get_permission_classes("nonexistent_type")
        # Should return the authenticated default
        assert result is not None
        assert len(result) > 0
