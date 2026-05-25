from rest_framework import permissions
from django.utils import timezone


def _is_admin(user):
    return user.is_superuser or user.groups.filter(name='Admin').exists()

def _is_company_owner(user, program):
    return program.company == user

def _can_manage(user, program):
    return _is_company_owner(user, program) or _is_admin(user)

def _researcher_has_private_access(user, program):
    invited = program.invitations.filter(researcher=user, status='accepted').exists()
    applied = program.applications.filter(researcher=user, status='approved').exists()
    return invited or applied


class IsProgramOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Read-only actions are open to all authenticated users; write actions
        # (create, update, delete) require ProgramOwner or Admin/superuser.
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user.is_superuser or
            request.user.groups.filter(name__in=['ProgramOwner', 'Admin']).exists()
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        program = obj if hasattr(obj, 'company') else getattr(obj, 'program', None)
        if program is None:
            return False
        return _can_manage(request.user, program)


class IsResearcher(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.groups.filter(name='Researcher').exists()
        )


class IsCompany(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.groups.filter(name='ProgramOwner').exists()
        )


class IsTriager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and
            request.user.groups.filter(name='Triager').exists()
        )


class CanAccessProgram(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if _is_admin(user):
            return True
        if _is_company_owner(user, obj):
            return True
        if user.groups.filter(name='Triager').exists():
            return obj.status == 'active'
        if user.groups.filter(name='Researcher').exists():
            if obj.scope_type in ('public', 'vdp') and obj.status == 'active':
                return True
            if obj.scope_type == 'private' and obj.status == 'active':
                return _researcher_has_private_access(user, obj)
        return False


class CanSubmitToProgram(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not obj.is_active:
            return False
        if obj.end_date and obj.end_date < timezone.now().date():
            return False
        if _is_admin(user):
            return True
        if user.groups.filter(name='Admin').exists():
            return True
        if _is_company_owner(user, obj):
            return True
        if user.groups.filter(name='User').exists():
            if obj.scope_type in ('public', 'vdp'):
                return True
            if obj.scope_type == 'private':
                return _researcher_has_private_access(user, obj)
        return False


class IsOwnerOrAdmin(permissions.BasePermission):
    """Generic permission for Invitation, Application, Favorite, Notification."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        owner = getattr(obj, 'researcher', None) or getattr(obj, 'user', None)
        if owner == request.user:
            return True
        return request.method in permissions.SAFE_METHODS