from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .bugreport import BugReport


class Comment(models.Model):
    """A message on a report. ``parent`` makes replies; ``is_internal`` marks triager-only notes."""

    report = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies",
    )
    text = models.TextField()
    # Internal notes are visible to (and writable by) Admins/Triagers only.
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    # Soft delete: keeps the thread shape intact when a comment has replies.
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["report", "created_at"], name="cmt_report_created")]

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def depth(self):
        """Number of ancestors (0 for a top-level comment)."""
        depth, node = 0, self.parent
        while node is not None:
            depth += 1
            node = node.parent
        return depth

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
