import os, tempfile

from django.conf.global_settings import DEFAULT_FROM_EMAIL
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from django.db import models
from django.core.mail import send_mail
from .models import BugReport, Comment
from .serializers import BugReportSerializer, CommentSerializer, ActivityLogSerializer
from .permissions import IsReporterOrTriagerOrAdmin
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse, Http404
from django.conf import settings
from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from .models_attachment import Attachment
from .serializers import AttachmentSerializer
from .services import ActivityLogger
from .validators import validate_extension, validate_size, validate_mime, detect_mime
from users.throttles import SubmissionThrottle, BurstRateThrottle
from .captcha import verify_recaptcha
from rest_framework.exceptions import ValidationError
from users.models import Profile
from rest_framework.exceptions import PermissionDenied

class BugReportViewSet(viewsets.ModelViewSet):
    queryset = BugReport.objects.all().order_by("-created_at")
    serializer_class = BugReportSerializer
    permission_classes = [IsAuthenticated, IsReporterOrTriagerOrAdmin]
    throttle_classes=[SubmissionThrottle, BurstRateThrottle]
    throttle_scope="submission"

    def get_queryset(self):
        user = self.request.user
        queryset = BugReport.objects.all().order_by("-created_at")

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
        is_admin_or_triager = user.groups.filter(name__in=['Triager', 'Admin']).exists()
        is_program_owner = user.groups.filter(name='ProgramOwner').exists()

        # Admin / Triager → see everything
        if is_admin_or_triager:
            return queryset

        # Program Owner → see reports for programs they own
        if is_program_owner:
            return queryset.filter(program__owner=user)

        # Regular user → only their reports
        return queryset.filter(reporter=user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def triage_dashboard(self, request):
        """Specialized endpoint for triage dashboard with counts"""
        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
            return Response(
                {"error": "Only Triagers and Admins can access triage dashboard"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get counts for dashboard
        counts = {
            'total': BugReport.objects.count(),
            'open': BugReport.objects.filter(status='open').count(),
            'triaged': BugReport.objects.filter(status='triaged').count(),
            'accepted': BugReport.objects.filter(status='accepted').count(),
            'rejected': BugReport.objects.filter(status='rejected').count(),
            'assigned_to_me': BugReport.objects.filter(assigned_to=request.user).count(),
            'unassigned': BugReport.objects.filter(assigned_to__isnull=True).count(),
        }

        # Get recent reports for the dashboard
        recent_reports = BugReport.objects.filter(
            status__in=['open', 'triaged']
        ).order_by('-created_at')[:10]

        report_serializer = BugReportSerializer(recent_reports, many=True)

        return Response({
            'counts': counts,
            'recent_reports': report_serializer.data
        })

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            if not getattr(self.request.user, "profile", None) or not self.request.user.profile.email_verified:
                raise PermissionDenied("Please verify your email before submitting a report.")

        report=serializer.save(reporter=self.request.user)
        self.send_submission_notification(report)

    def send_submission_notification(self,report):
        # send email notif to adming regarding new submission
        try:
            subject = f"New Bug Report Submitted: {report.title}"
            message = f"""
New bug report has been submitted:

Title: {report.title}
Reporter: {report.reporter.username}
Severity: {report.severity}
Description: {report.description[:200]}...

View and manage at: http://localhost:8000/admin/reports/bugreport/{report.id}/
            """

            # send to all admin users
            from django.contrib.auth.models import User
            admin_emails=User.objects.filter(
                groups__name='Admin',
                email__isnull=False
            ).values_list('email',flat=True)

            if admin_emails and hasattr(settings, 'EMAIL_BACKEND'):
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    list(admin_emails),
                    fail_silently=True,
                )
        except Exception as e:
            print(f"Error sending mail: {e}")

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def comment(self, request, pk=None):
        report = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user, report=report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
    def change_status(self, request, pk=None):
        # Only Triagers and Admins can change status
        report = self.get_object()

        # Check if user has permission to change status
        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
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

        # Attachment Methods

    def _can_access_report(self, report):
        u = self.request.user
        return u.is_superuser or u == report.reporter or u.groups.filter(name__in=['Triager', 'Admin']).exists()

    @action(detail=True, methods=["GET"])
    def attachments(self, request, pk=None):
        report = self.get_object()
        if not self._can_access_report(report):
            return Response(status=status.HTTP_403_FORBIDDEN)
        qs = report.attachments.order_by("-created_at")
        return Response(AttachmentSerializer(qs, many=True).data)

    @action(detail=True, methods=["POST"])
    def upload_attachment(self, request, pk=None):
        report = self.get_object()
        if not self._can_access_report(report):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # Require verified email before uploads
        if not request.user.profile.email_verified:
            return Response(
                {"detail": "Email verification required before submitting reports"},
                status=status.HTTP_403_FORBIDDEN
            )
        # ---- reCAPTCHA check ----
        captcha_token = (
            request.data.get("g-recaptcha-response")
            or request.data.get("captcha")
        )
        try:
            verify_recaptcha(captcha_token, request.META.get("REMOTE_ADDR"))
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        f = request.data.get("file")
        if not f:
            return Response({"detail": "No file"}, status=400)
        try:
            validate_extension(f.name);
            validate_size(f.size)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=400)

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            mime = detect_mime(tmp_path);
            validate_mime(mime)

            # ClamAV scan
            from pyclamd import ClamdNetworkSocket
            cd = ClamdNetworkSocket(host=os.getenv("CLAMAV_HOST", "clamav"),
                                    port=int(os.getenv("CLAMAV_PORT", "3310")))
            try:
                scan_result = cd.scan_file(tmp_path)
            except Exception:
                scan_result = None
            if not scan_result:
                os.unlink(tmp_path)
                return Response({"detail": "Upload blocked: scan status 'failed'."}, status=400)
            status_tuple = list(scan_result.values())[0]
            scan_status = "infected" if status_tuple and status_tuple[0] == "FOUND" else "clean"
            if scan_status != "clean":
                os.unlink(tmp_path)
                return Response({"detail": "Upload blocked: scan status 'infected'."}, status=400)

            f.seek(0)
            att = Attachment.objects.create(
                report=report, uploader=request.user, original_name=f.name, file=f,
                size=f.size, mime=mime, sha256=Attachment.sha256_of(f), scan_status="clean",
            )
            return Response(AttachmentSerializer(att).data, status=201)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @action(detail=True, methods=["GET"], url_path="download/(?P<att_id>[^/.]+)")
    def download_attachment(self, request, pk=None, att_id=None):
        report = self.get_object()
        if not self._can_access_report(report):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            att = report.attachments.get(id=att_id, scan_status="clean")
        except Attachment.DoesNotExist:
            raise Http404()
        resp = FileResponse(att.file.open("rb"), as_attachment=True, filename=att.original_name)
        resp["X-Content-Type-Options"] = "nosniff"
        return resp

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def assign_to_me(self, request, pk=None):
        """Assign report to current user"""
        report = self.get_object()

        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
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
        """Accept a report for bounty"""
        report = self.get_object()

        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
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
        bounty_amount = request.data.get('bounty_amount')

        # Update report
        report.status = 'accepted'
        report.verification_notes = verification_notes
        if bounty_amount:
            report.bounty_amount = bounty_amount
        report.save()

        # Log activity
        ActivityLogger.log_verification(report, request.user, 'accept', verification_notes)

        return Response({
            "message": "Report accepted successfully",
            "status": report.status,
            "bounty_amount": report.bounty_amount
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a report"""
        report = self.get_object()

        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
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

        if not request.user.groups.filter(name__in=['Triager', 'Admin']).exists():
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

    @action(detail=True, methods=['get'])
    def activity_logs(self, request, pk=None):
        """Get activity logs for a report"""
        report = self.get_object()
        if not self._can_access_report(report):
            return Response(status=status.HTTP_403_FORBIDDEN)

        logs = report.activity_logs.order_by('-created_at')
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data)

class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
       # Users can see comments only for reports they have access to
        user = self.request.user

        if user.groups.filter(name__in=['Triager', 'Admin']).exists():
            return Comment.objects.all().order_by("-created_at")
        else:
            # Researchers see comments only on their own reports
            return Comment.objects.filter(report__reporter=user).order_by("-created_at")
        


parser_classes = (MultiPartParser, FormParser)

def _can_access_report(self, report):
    u = self.request.user
    return u.is_superuser or u == report.reporter or u.groups.filter(name__in=['Triager','Admin']).exists()

@action(detail=True, methods=["GET"])
def attachments(self, request, pk=None):
    report = self.get_object()
    if not self._can_access_report(report):
        return Response(status=status.HTTP_403_FORBIDDEN)
    qs = report.attachments.order_by("-created_at")
    return Response(AttachmentSerializer(qs, many=True).data)

@action(detail=True, methods=["POST"])
def upload_attachment(self, request, pk=None):
    report = self.get_object()
    if not self._can_access_report(report):
        return Response(status=status.HTTP_403_FORBIDDEN)
    f = request.data.get("file")
    if not f:
        return Response({"detail":"No file"}, status=400)
    try:
        validate_extension(f.name); validate_size(f.size)
    except ValidationError as e:
        return Response({"detail": str(e)}, status=400)

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        for chunk in f.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    try:
        mime = detect_mime(tmp_path); validate_mime(mime)

        # ClamAV scan
        from pyclamd import ClamdNetworkSocket
        cd = ClamdNetworkSocket(host=os.getenv("CLAMAV_HOST","clamav"), port=int(os.getenv("CLAMAV_PORT","3310")))
        try:
            scan_result = cd.scan_file(tmp_path)
        except Exception:
            scan_result = None
        if not scan_result:
            os.unlink(tmp_path)
            return Response({"detail":"Upload blocked: scan status 'failed'."}, status=400)
        status_tuple = list(scan_result.values())[0]
        scan_status = "infected" if status_tuple and status_tuple[0] == "FOUND" else "clean"
        if scan_status != "clean":
            os.unlink(tmp_path)
            return Response({"detail":"Upload blocked: scan status 'infected'."}, status=400)

        f.seek(0)
        att = Attachment.objects.create(
            report=report, uploader=request.user, original_name=f.name, file=f,
            size=f.size, mime=mime, sha256=Attachment.sha256_of(f), scan_status="clean",
        )
        return Response(AttachmentSerializer(att).data, status=201)
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass

@action(detail=True, methods=["GET"], url_path="download/(?P<att_id>[^/.]+)")
def download_attachment(self, request, pk=None, att_id=None):
    report = self.get_object()
    if not self._can_access_report(report):
        return Response(status=status.HTTP_403_FORBIDDEN)
    try:
        att = report.attachments.get(id=att_id, scan_status="clean")
    except Attachment.DoesNotExist:
        raise Http404()
    resp = FileResponse(att.file.open("rb"), as_attachment=True, filename=att.original_name)
    resp["X-Content-Type-Options"] = "nosniff"
    return resp