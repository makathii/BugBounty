from rest_framework import permissions
from django.contrib.auth.models import Group


class IsProgramOwnerOrAdmin(permissions.BasePermission):
    """Permission to allow only program owners or admins to edit/delete"""

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the program owner or admin
        return obj.company == request.user or request.user.groups.filter(name='Admin').exists()


class IsResearcher(permissions.BasePermission):
    """Permission to allow only researchers"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Researcher').exists()


class CanAccessProgram(permissions.BasePermission):
    """Permission to check if user can access a program"""

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admins can access everything
        if user.is_superuser or user.groups.filter(name='Admin').exists():
            return True

        # Program owner can access
        if obj.company == user:
            return True

        # Triagers can access active programs
        if user.groups.filter(name='Triager').exists() and obj.status == 'active':
            return True

        # Check if program is public and active
        if obj.scope_type == 'public' and obj.status == 'active':
            return True

        # Check if user is a researcher with access to private program
        if user.groups.filter(name='Researcher').exists():
            # Check if invited and accepted
            invited = obj.invitations.filter(
                researcher=user,
                status='accepted'
            ).exists()

            # Check if applied and approved
            applied = obj.applications.filter(
                researcher=user,
                status='approved'
            ).exists()

            return invited or applied

        return False


class CanSubmitToProgram(permissions.BasePermission):
    """Permission to check if user can submit reports to a program"""

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Check if program is active
        if not obj.is_active:
            return False

        # Check if program has ended
        if obj.end_date and obj.end_date < timezone.now().date():
            return False

        # Admins and triagers can submit
        if user.groups.filter(name__in=['Admin', 'Triager']).exists():
            return True

        # Program owner can submit
        if obj.company == user:
            return True

        # Check if user is a researcher with access
        if user.groups.filter(name='Researcher').exists():
            # Public programs allow all researchers
            if obj.scope_type == 'public':
                return True

            # Private programs require invitation or application
            if obj.scope_type == 'private':
                # Check if invited and accepted
                invited = obj.invitations.filter(
                    researcher=user,
                    status='accepted'
                ).exists()

                # Check if applied and approved
                applied = obj.applications.filter(
                    researcher=user,
                    status='approved'
                ).exists()

                return invited or applied

        return False