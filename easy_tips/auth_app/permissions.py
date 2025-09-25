from rest_framework import permissions

class IsAuthenticatedUserData(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'is_authenticated') and request.user.is_authenticated)