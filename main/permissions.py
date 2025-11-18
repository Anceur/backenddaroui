from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """Allow access only to admin users"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.roles == 'admin')


class IsCashier(permissions.BasePermission):
    """Allow access only to cashier users"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.roles == 'cashier')


class IsChef(permissions.BasePermission):
    """Allow access only to chef users"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.roles == 'chef')


class IsChefOrAdmin(permissions.BasePermission):
    """Allow access to both admin and chef users"""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.roles in ['admin', 'chef']
        )
