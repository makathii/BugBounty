from rest_framework import permissions

from core.roles import has_any_role, is_admin_or_triager


# What a program owner (company) may do to a report filed against one of its programs: read it and
# join the discussion. Editing, deleting, triage and payouts stay with the reporter / staff.
COMPANY_ACTIONS = {"retrieve", "list", "comment", "comments", "comment_detail", "activity_logs", "attachments",
                   "download_attachment"}


def is_owner_of_reports_program(request, report):
    """True when the requester is the company that owns the report's program."""
    program = getattr(report, "program", None)
    return bool(
        program is not None and request.user.is_authenticated
        and program.company_id == request.user.id
        and has_any_role(request, "ProgramOwner")
    )


class IsReporterOrTriagerOrAdmin(permissions.BasePermission):
    # Custom permission to only allow:
    # - Reporters to access their own reports
    # - Triagers and Admins to access all reports
    # - the owning company to read and discuss reports on its programs

    def has_object_permission(self, request, view, obj):
        # Triagers and Admins can access everything
        if is_admin_or_triager(request):
            return True

        # Reporters can only access their own reports
        if obj.reporter == request.user:
            return True

        # The company that owns the program: read and discuss only
        if is_owner_of_reports_program(request, obj):
            return getattr(view, "action", None) in COMPANY_ACTIONS
        return False


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