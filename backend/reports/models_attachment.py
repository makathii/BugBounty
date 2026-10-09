import hashlib, os, uuid
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from .models import BugReport

def report_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"reports/{instance.report_id}/{uuid.uuid4()}{ext}"

class Attachment(models.Model):
    SCAN_CHOICES = [
        ("pending", "Pending"),
        ("clean", "Clean"),
        ("infected", "Infected"),
        ("failed", "Failed"),
    ]
    report = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="attachments")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=report_upload_path)
    size = models.BigIntegerField()
    mime = models.CharField(max_length=100)
    sha256 = models.CharField(max_length=64)
    scan_status = models.CharField(max_length=10, choices=SCAN_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["report", "scan_status"])]

    def __str__(self):
        return f"{self.original_name} ({self.scan_status})"

    @staticmethod
    def sha256_of(fileobj):
        h = hashlib.sha256()
        for chunk in iter(lambda: fileobj.read(8192), b""):
            h.update(chunk)
        fileobj.seek(0)
        return h.hexdigest()