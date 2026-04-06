from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to Admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')

class IsUser(permissions.BasePermission):
    """
    Allows access to both Admin and User roles.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['admin', 'user'])

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    The request is authenticated as a user, but only admins can edit.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
