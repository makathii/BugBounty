from django.db import models
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import is_admin_or_triager

from ..models import BugReport
from ..serializers import BugReportSerializer
from ..services import ActivityLogger


# Upper bound on a single triager bonus, so a typo can't mint a fortune.
MAX_BONUS_POINTS = 1000


class TriageActionsMixin:
    """Triager/admin workflow endpoints for BugReportViewSet."""

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def triage_dashboard(self, request):
        """Specialized endpoint for triage dashboard with counts"""
        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can access triage dashboard"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get counts for dashboard
        counts = BugReport.objects.aggregate(
            total=models.Count('id'),
            open=models.Count('id', filter=Q(status='open')),
            triaged=models.Count('id', filter=Q(status='triaged')),
            accepted=models.Count('id', filter=Q(status='accepted')),
            rejected=models.Count('id', filter=Q(status='rejected')),
            assigned_to_me=models.Count('id', filter=Q(assigned_to=request.user)),
            unassigned=models.Count('id', filter=Q(assigned_to__isnull=True)),
        )

        # Get recent reports for the dashboard
        recent_reports = BugReport.objects.select_related(
            'assigned_to', 'program', 'reporter', 'score_event'
        ).filter(
            status__in=['open', 'triaged']
        ).order_by('-created_at')[:10]

        report_serializer = BugReportSerializer(recent_reports, many=True)

        return Response({
            'counts': counts,
            'recent_reports': report_serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def assign_to_me(self, request, pk=None):
        """Assign report to current user"""
        report = self.get_object()

        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can assign reports"},
                status=status.HTTP_403_FORBIDDEN
            )

        report.assigned_to = request.user
        report.save()

        ActivityLogger.log_assignment(report, request.user, request.user)

        return Response({
            "message": f"Report assigned to {request.user.username}",
            "assigned_to": request.user.username
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def accept(self, request, pk=None):
        """Accept a report. Optionally award ``bonus_points`` on top of the severity points."""
        report = self.get_object()

        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can accept reports"},
                status=status.HTTP_403_FORBIDDEN
            )

        if not report.can_be_accepted():
            return Response(
                {"error": "Report cannot be accepted in current status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification_notes = request.data.get('verification_notes', '')
        try:
            bonus_points = int(request.data.get('bonus_points') or 0)
        except (TypeError, ValueError):
            bonus_points = -1
        if not 0 <= bonus_points <= MAX_BONUS_POINTS:
            return Response(
                {"error": f"bonus_points must be a whole number from 0 to {MAX_BONUS_POINTS}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update report
        report.status = 'accepted'
        report.verification_notes = verification_notes
        report.bonus_points = bonus_points
        report.save()

        # Log activity
        ActivityLogger.log_verification(report, request.user, 'accept', verification_notes)

        return Response({
            "message": "Report accepted successfully",
            "status": report.status,
            "bonus_points": report.bonus_points,
            "points_awarded": report.points_awarded,
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a report"""
        report = self.get_object()

        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can reject reports"},
                status=status.HTTP_403_FORBIDDEN
            )

        if not report.can_be_rejected():
            return Response(
                {"error": "Report cannot be rejected in current status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason', '')

        # Update report
        report.status = 'rejected'
        report.verification_notes = rejection_reason
        report.save()

        # Log activity
        ActivityLogger.log_verification(report, request.user, 'reject', rejection_reason)

        return Response({
            "message": "Report rejected",
            "status": report.status
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reopen(self, request, pk=None):
        """Reopen a closed report"""
        report = self.get_object()

        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can reopen reports"},
                status=status.HTTP_403_FORBIDDEN
            )

        if report.status not in ['accepted', 'rejected', 'resolved']:
            return Response(
                {"error": "Report cannot be reopened from current status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        report.status = 'triaged'
        report.save()

        ActivityLogger.log_verification(report, request.user, 'reopen', 'Report reopened for review')

        return Response({
            "message": "Report reopened for review",
            "status": report.status
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_as_duplicate(self, request, pk=None):
        """Mark a report as duplicate of another report"""
        report = self.get_object()

        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can mark reports as duplicates"},
                status=status.HTTP_403_FORBIDDEN
            )

        duplicate_of_id = request.data.get('duplicate_of')
        duplicate_reason = request.data.get('duplicate_reason', '')

        if not duplicate_of_id:
            return Response(
                {"error": "duplicate_of field is required (report ID this is a duplicate of)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the original report
        try:
            original_report = BugReport.objects.get(id=duplicate_of_id)
        except BugReport.DoesNotExist:
            return Response(
                {"error": "Original report not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent marking as duplicate of itself
        if str(report.id) == str(duplicate_of_id):
            return Response(
                {"error": "A report cannot be marked as duplicate of itself"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent circular duplicates
        if original_report.duplicate_of:
            return Response(
                {"error": "Cannot mark as duplicate of a report that is itself a duplicate"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update report
        report.status = 'duplicate'
        report.duplicate_of = original_report
        report.duplicate_reason = duplicate_reason
        report.save()

        # Log activity
        ActivityLogger.log_verification(
            report,
            request.user,
            'mark_duplicate',
            f"Marked as duplicate of report #{original_report.id}. Reason: {duplicate_reason}"
        )

        return Response({
            "message": f"Report marked as duplicate of #{original_report.id}",
            "status": report.status,
            "duplicate_of": original_report.id,
            "original_report_title": original_report.title
        })
