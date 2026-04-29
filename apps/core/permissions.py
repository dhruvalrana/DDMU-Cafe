"""
Custom permissions for the POS system.
"""

from rest_framework import permissions


class IsPOSUser(permissions.BasePermission):
    """
    Permission for POS staff users (can create orders, manage sessions).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['admin', 'staff', 'manager']
        )


class IsKitchenUser(permissions.BasePermission):
    """
    Permission for Kitchen Display users.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['admin', 'kitchen', 'manager']
        )


class IsManagerOrAdmin(permissions.BasePermission):
    """
    Permission for manager-level operations (reports, configuration).
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ['admin', 'manager']
        )


class IsAdminUser(permissions.BasePermission):
    """
    Permission for admin-only operations.
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class ReadOnlyOrAuthenticated(permissions.BasePermission):
    """
    Allow read-only access to anyone, write access only to authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins to edit.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        
        # Check if object has user/owner field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'responsible_user'):
            return obj.responsible_user == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
            
        return False
