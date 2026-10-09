import os

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.roles import is_admin_or_triager

from core.captcha import verify_recaptcha
from ..models import Attachment
from ..serializers import AttachmentSerializer
from ..validators import (
    detect_mime,
    strip_exif,
    validate_extension,
    validate_image_dimensions,
    validate_mime,
    validate_size,
)


class AttachmentActionsMixin:
    """Attachment endpoints for BugReportViewSet (list / upload / download)."""

    def _can_access_report(self, report):
        u = self.request.user
        return u.is_superuser or u == report.reporter or is_admin_or_triager(self.request)

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
        except (ValidationError, DjangoValidationError) as e:
            return Response({"detail": str(e)}, status=400)

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in f.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            try:
                mime = detect_mime(tmp_path)
                validate_mime(mime)
            except (ValidationError, DjangoValidationError) as e:
                return Response({"detail": str(e)}, status=400)

            # Image-specific checks: reject decompression bombs and strip EXIF
            try:
                validate_image_dimensions(tmp_path)
            except (ValidationError, DjangoValidationError) as e:
                return Response({"detail": str(e)}, status=400)
            strip_exif(tmp_path)  # best-effort; never blocks upload on failure

            # ClamAV scan — clamd runs in its own container and cannot read the
            # backend's filesystem, so stream the bytes over the socket
            # (INSTREAM) instead of asking it to scan a local path.
            from pyclamd import ClamdNetworkSocket
            cd = ClamdNetworkSocket(host=os.getenv("CLAMAV_HOST", "clamav"),
                                    port=int(os.getenv("CLAMAV_PORT", "3310")))
            try:
                with open(tmp_path, "rb") as scan_fh:
                    scan_result = cd.scan_stream(scan_fh.read())
                scan_ok = True
            except Exception:
                scan_result = None
                scan_ok = False
            if not scan_ok:
                return Response({"detail": "Upload blocked: scan status 'failed'."}, status=400)
            # scan_stream returns None when the file is clean, or
            # {'stream': ('FOUND', '<signature>')} when infected.
            if scan_result:
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
