"""
reports models, one module per model.

``from reports.models import BugReport`` etc. keeps working: every model is
imported here so Django registers it under the ``reports`` app.
"""

from .activity import ActivityLog
from .attachment import Attachment, report_upload_path
from .bugreport import BugReport
from .comment import Comment


__all__ = ['BugReport', 'Comment', 'ActivityLog', 'Attachment', 'report_upload_path']
