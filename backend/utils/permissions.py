"""
Custom permission classes for InvoiceForge.
Implements role-based access control for the API.
"""

from rest_framework import permissions

from apps.accounts.models import User


class IsAdminUser(permissions.BasePermission):
    """Only allow users with the admin role."""

    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsManagerOrAbove(permissions.BasePermission):
    """Allow users with admin or manager role."""

    message = "Only managers and administrators can perform this action."

    ALLOWED_ROLES = {User.Role.ADMIN, User.Role.MANAGER}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsAccountantOrAbove(permissions.BasePermission):
    """Allow admin, manager, and accountant roles."""

    message = "You do not have permission to perform this action."

    ALLOWED_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.ACCOUNTANT}

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: allow access only if the user owns the object
    or has the admin role. Objects must have a `user` field.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True
        return getattr(obj, "user", None) == request.user


class ReadOnlyOrAdmin(permissions.BasePermission):
    """
    Allow read-only access for any authenticated user.
    Write access only for admins.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role == User.Role.ADMIN


class ViewerReadOnly(permissions.BasePermission):
    """
    Viewers can only use safe (read-only) HTTP methods.
    All other roles have full access.
    """

    message = "Viewers have read-only access."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.VIEWER:
            return request.method in permissions.SAFE_METHODS
        return True
