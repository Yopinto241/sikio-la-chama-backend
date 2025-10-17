from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsPollAdmin(BasePermission):
    """
    Custom permission to allow either:
    - Django admin/staff users, or
    - Users with user_type='admin'
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.user_type == 'admin')
        )

class IsPollAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff