from django.contrib.auth.models import User
from django.db import models

from .bugreport import BugReport


class Comment(models.Model):
    report = models.ForeignKey(BugReport, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
