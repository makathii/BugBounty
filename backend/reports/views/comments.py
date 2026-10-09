from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import is_admin_or_triager

from ..models import Comment
from ..serializers import CommentSerializer, with_author_loadouts


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    """Flat, read-only comment feed. Threads and writes live under /reports/{id}/comments/."""
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        comments = list(self.filter_queryset(self.get_queryset()))
        context = with_author_loadouts(comments, self.get_serializer_context())
        return Response(CommentSerializer(comments, many=True, context=context).data)

    def get_queryset(self):
       # Users can see comments only for reports they have access to
        user = self.request.user

        qs = Comment.objects.select_related("author")
        if is_admin_or_triager(self.request):
            return qs.order_by("-created_at")
        # Researchers see public comments only, and only on their own reports
        return qs.filter(report__reporter=user, is_internal=False).order_by("-created_at")
