"""
Custom Permission Classes

Provides fine-grained access control for API endpoints.
Defines various permission policies for different user types and operations.
"""

from rest_framework import permissions


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access to unauthenticated users.
    Require authentication for write operations (POST, PUT, PATCH, DELETE).

    Use case: Public data that anyone can view but only authenticated users can modify.
    """

    def has_permission(self, request, view):
        # Read permissions (GET, HEAD, OPTIONS) allowed to anyone
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only allowed to authenticated users
        return request.user and request.user.is_authenticated


class IsAdminUser(permissions.BasePermission):
    """
    Only allow admin users (staff or superuser) to access.

    Use case: Admin-only endpoints like bulk operations, system configuration, etc.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allow owners to access their own objects, and admins to access any object.

    Use case: User profiles, tenant data where users should only see their own data
    unless they are admins.

    Requires the object to have a 'user' field or implement a custom ownership check.
    """

    def has_object_permission(self, request, view, obj):
        # Admins can access any object
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if object has a 'user' attribute
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Check if object has a 'created_by' attribute
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user

        # If no ownership field found, deny access
        return False


class IsTenantOrAdmin(permissions.BasePermission):
    """
    Allow tenants to access their own lease data, and admins to access any lease.

    Use case: Lease endpoints where tenants should only see leases they are part of.

    Note: Currently, Tenant model does not have a 'user' foreign key,
    so this permission effectively only allows admin access.
    When user authentication is fully integrated, update this to check tenant.user.
    """

    def has_object_permission(self, request, view, obj):
        # Admins can access any lease
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check if user is a tenant in this lease
        # NOTE: Tenant model currently does not have a 'user' field
        # This check is a placeholder for future implementation
        if hasattr(obj, "tenants"):
            # Check if any tenant has a user field matching the request user
            for tenant in obj.tenants.all():
                if hasattr(tenant, "user") and tenant.user == request.user:
                    return True

        # Check if user is the responsible tenant
        if hasattr(obj, "responsible_tenant"):
            if (
                hasattr(obj.responsible_tenant, "user")
                and obj.responsible_tenant.user == request.user
            ):
                return True

        # If no tenant relationship found, deny access
        return False


class ReadOnlyForNonAdmin(permissions.BasePermission):
    """
    Allow read-only access to authenticated users.
    Only admins can perform write operations.

    Use case: Reference data (buildings, furniture) that regular users need to see
    but should not modify.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not (request.user and request.user.is_authenticated):
            return False

        # Read permissions allowed to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admins
        return request.user.is_staff or request.user.is_superuser


class CanGenerateContract(permissions.BasePermission):
    """
    Allow contract generation only for admins or the responsible tenant.

    Use case: Contract generation endpoint should be restricted to prevent abuse.
    """

    def has_object_permission(self, request, view, obj):
        # Admins can always generate contracts
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Responsible tenant can generate contract for their lease
        if hasattr(obj, "responsible_tenant"):
            return (
                hasattr(obj.responsible_tenant, "user")
                and obj.responsible_tenant.user == request.user
            )

        return False


class CanModifyLease(permissions.BasePermission):
    """
    Allow lease modification only for admins.
    Tenants can view but not modify leases.

    Use case: Lease terms should not be modifiable by tenants to prevent unauthorized changes.
    """

    def has_permission(self, request, view):
        # Must be authenticated
        if not (request.user and request.user.is_authenticated):
            return False

        # Read permissions allowed to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Only admins can modify leases
        return request.user.is_staff or request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        # Must be authenticated
        if not (request.user and request.user.is_authenticated):
            return False

        # Read permissions allowed to authenticated users
        if request.method in permissions.SAFE_METHODS:
            # Check if user is a tenant or admin
            if request.user.is_staff or request.user.is_superuser:
                return True
            # Check if user is a tenant in this lease
            # NOTE: Tenant model currently does not have a 'user' field
            if hasattr(obj, "tenants"):
                for tenant in obj.tenants.all():
                    if hasattr(tenant, "user") and tenant.user == request.user:
                        return True
            return False

        # Only admins can modify leases
        return request.user.is_staff or request.user.is_superuser


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Require authentication and active user status.

    Use case: All authenticated endpoints should verify user is active.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_active


# Permission class mapping for easy import and documentation
PERMISSION_CLASSES = {
    "public_read": [IsAuthenticatedOrReadOnly],
    "admin_only": [IsAdminUser],
    "owner_or_admin": [IsAuthenticatedAndActive, IsOwnerOrAdmin],
    "tenant_or_admin": [IsAuthenticatedAndActive, IsTenantOrAdmin],
    "read_only_for_non_admin": [ReadOnlyForNonAdmin],
    "can_generate_contract": [IsAuthenticatedAndActive, CanGenerateContract],
    "can_modify_lease": [CanModifyLease],
    "authenticated": [IsAuthenticatedAndActive],
}


def get_permission_classes(permission_type="authenticated"):
    """
    Helper function to get permission classes by type.

    Args:
        permission_type: String key from PERMISSION_CLASSES dict

    Returns:
        List of permission classes

    Example:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = get_permission_classes('admin_only')
    """
    return PERMISSION_CLASSES.get(permission_type, PERMISSION_CLASSES["authenticated"])
