from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request, 'user', None) and getattr(request.user, 'is_active', False))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_active and user.role == 'admin')


class IsAnalyst(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_active and user.role == 'analyst')

