# users/permissions.py
from rest_framework import permissions

class IsResearcher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Researcher').exists()

class IsTriager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Triager').exists()

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Admin').exists()

class CanSubmitReport(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['Researcher', 'Admin']).exists()

class CanEditReport(permissions.BasePermission):
    def has_permission(self, request, view):
        # Researchers can edit their own, Triagers/Admins can edit all
        user_groups = request.user.groups.values_list('name', flat=True)
        return 'Triager' in user_groups or 'Admin' in user_groups