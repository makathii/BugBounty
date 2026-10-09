from django.db import models
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import has_any_role, is_admin_or_triager
from core.tasks import enqueue_after_commit
from users.throttles import BurstRateThrottle, SubmissionThrottle

from ..models import BugReport
from ..permissions import IsReporterOrTriagerOrAdmin
from ..serializers import ActivityLogSerializer, BugReportSerializer
from ..tasks import send_report_submission_notification
from .attachments import AttachmentActionsMixin
from .comment_actions import CommentActionsMixin
from .cvss import CvssActionsMixin
from .triage import TriageActionsMixin


class BugReportViewSet(
    AttachmentActionsMixin,
    CommentActionsMixin,
    TriageActionsMixin,
    CvssActionsMixin,
    viewsets.ModelViewSet,
):
    queryset = BugReport.objects.all().order_by("-created_at")
    serializer_class = BugReportSerializer
    permission_classes = [IsAuthenticated, IsReporterOrTriagerOrAdmin]
    throttle_classes=[SubmissionThrottle, BurstRateThrottle]
    throttle_scope="submission"

    def get_queryset(self):
        user = self.request.user
        queryset = BugReport.objects.select_related("assigned_to", "program", "reporter", "score_event").order_by("-created_at")

        # Apply filters for triage dashboard
        status_filter = self.request.query_params.get('status')
        severity_filter = self.request.query_params.get('severity')
        assigned_to_filter = self.request.query_params.get('assigned_to')
        search_term = self.request.query_params.get('search')

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        if assigned_to_filter:
            if assigned_to_filter == 'me':
                queryset = queryset.filter(assigned_to=user)
            elif assigned_to_filter == 'unassigned':
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to__username=assigned_to_filter)
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        # Permission-based filtering
        admin_or_triager = is_admin_or_triager(self.request)
        is_program_owner = has_any_role(self.request, 'ProgramOwner')

        # Admin / Triager → see everything
        if admin_or_triager:
            return queryset

        # Program Owner → see reports for programs they own
        if is_program_owner:
            return queryset.filter(program__company=user)

        # Regular user → only their reports
        return queryset.filter(reporter=user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def check_duplicates(self, request):
        """Check for potential duplicates without creating the report"""
        # Extract data from request
        title = request.data.get('title', '')
        description = request.data.get('description', '')
        affected_url = request.data.get('affected_url', '')
        program_id = request.data.get('program')

        if not title or not description:
            return Response(
                {"error": "Title and description are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create temporary instance to check duplicates
        temp_report = BugReport(
            title=title,
            description=description,
            affected_url=affected_url,
            program_id=program_id
        )

        duplicates = temp_report.find_potential_duplicates(threshold=0.7)

        return Response({
            "has_duplicates": len(duplicates) > 0,
            "potential_duplicates": [
                {
                    "id": dup.id,
                    "title": dup.title,
                    "severity": dup.severity,
                    "status": dup.status,
                    "similarity": round(score, 2),
                    "created_at": dup.created_at.isoformat() if dup.created_at else None,
                    "reporter": dup.reporter.username if dup.reporter else None,
                }
                for dup, score in duplicates
            ]
        })

    def perform_create(self, serializer):
        # Require email verification before allowing report submission
        if not self.request.user.is_superuser:
            if not getattr(self.request.user, "profile", None) or not self.request.user.profile.email_verified:
                raise PermissionDenied("Please verify your email before submitting a report.")

        report=serializer.save(reporter=self.request.user)
        self.send_submission_notification(report)

    def send_submission_notification(self, report):
        # Email Admin users about the new submission, off the request path.
        try:
            enqueue_after_commit(send_report_submission_notification, report.id)
        except Exception as e:  # never fail a submission because of mail
            print(f"Error sending mail: {e}")

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def change_status(self, request, pk=None):
        # Only Triagers and Admins can change status
        report = self.get_object()

        # Check if user has permission to change status
        if not is_admin_or_triager(request):
            return Response(
                {"error": "Only Triagers and Admins can change report status"},
                status=status.HTTP_403_FORBIDDEN
            )

        new_status = request.data.get('status')
        if new_status not in dict(BugReport.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        report.status = new_status
        report.save()

        return Response(BugReportSerializer(report).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_for_review(self, request, pk=None):
        # Submit a draft report for official review"""
        report = self.get_object()

        if report.reporter != request.user:
            return Response(
                {"error": "You can only submit your own reports for review"},
                status=status.HTTP_403_FORBIDDEN
            )

        if report.status != 'open':
            return Response(
                {"error": "Only reports with 'open' status can be submitted for review"},
                status=status.HTTP_400_BAD_REQUEST
            )

        report.status = 'triaged'
        report.save()

        return Response({
            "message": "Report submitted for review",
            "status": report.status
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_submissions(self, request):
        # Get current user's submissions with optional filtering"""
        reports = self.get_queryset().filter(reporter=request.user)

        # filtering
        status_filter = request.query_params.get('status')
        severity_filter = request.query_params.get('severity')

        if status_filter:
            reports = reports.filter(status=status_filter)
        if severity_filter:
            reports = reports.filter(severity=severity_filter)

        # Pagination
        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(reports, many=True)
        return Response({
            "count": reports.count(),
            "results": serializer.data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        # Get submission statistics for current user"""
        user_reports = BugReport.objects.filter(reporter=request.user)

        stats = {
            "total_submissions": user_reports.count(),
            "by_status": dict(user_reports.values_list('status').annotate(count=models.Count('id'))),
            "by_severity": dict(user_reports.values_list('severity').annotate(count=models.Count('id'))),
            "last_submission": user_reports.order_by(
                '-created_at').first().created_at if user_reports.exists() else None
        }

        return Response(stats)

    
    @action(detail=True, methods=['get'])
    def activity_logs(self, request, pk=None):
        """Get activity logs for a report"""
        report = self.get_object()
        if not self._can_access_report(report):
            return Response(status=status.HTTP_403_FORBIDDEN)

        logs = report.activity_logs.order_by('-created_at')
        if not is_admin_or_triager(request):
            # internal-note entries would reveal that staff-only notes exist
            logs = logs.exclude(details__is_internal=True)
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data)
