"""
reports API views.

  reports      BugReportViewSet (composed from the mixins below)
  attachments  AttachmentActionsMixin: list / upload / download attachments
  triage       TriageActionsMixin: assign, accept, reject, reopen, duplicates, dashboard
  cvss         CvssActionsMixin: CVSS v3.1 scoring
  comments     CommentViewSet
"""

from .comments import CommentViewSet
from .reports import BugReportViewSet


__all__ = ['BugReportViewSet', 'CommentViewSet']
