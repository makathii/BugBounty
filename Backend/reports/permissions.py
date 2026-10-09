from rest_framework import permissions

from core.roles import is_admin_or_triager


class IsReporterOrTriagerOrAdmin(permissions.BasePermission):
    # Custom permission to only allow:
    # - Reporters to access their own reports
    # - Triagers and Admins to access all reports

    def has_object_permission(self, request, view, obj):
        # Triagers and Admins can access everything
        if is_admin_or_triager(request):
            return True

        # Reporters can only access their own reports
        return obj.reporter == request.user


class CanChangeReportStatus(permissions.BasePermission):
    # Only Triagers and Admins can change report status

    def has_permission(self, request, view):
        if request.method in ['PUT', 'PATCH']:
            return is_admin_or_triager(request)
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in ['PUT', 'PATCH']:
            return is_admin_or_triager(request)
        return True