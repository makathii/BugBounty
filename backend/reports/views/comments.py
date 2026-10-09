from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.roles import is_admin_or_triager

from ..models import Comment
from ..serializers import CommentSerializer


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    """Flat, read-only comment feed. Threads and writes live under /reports/{id}/comments/."""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
       # Users can see comments only for reports they have access to
        user = self.request.user

        qs = Comment.objects.select_related("author")
        if is_admin_or_triager(self.request):
            return qs.order_by("-created_at")
        # Researchers see public comments only, and only on their own reports
        return qs.filter(report__reporter=user, is_internal=False).order_by("-created_at")
