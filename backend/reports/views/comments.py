from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.roles import is_admin_or_triager

from ..models import Comment
from ..serializers import CommentSerializer


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
       # Users can see comments only for reports they have access to
        user = self.request.user

        if is_admin_or_triager(self.request):
            return Comment.objects.all().order_by("-created_at")
        else:
            # Researchers see comments only on their own reports
            return Comment.objects.filter(report__reporter=user).order_by("-created_at")
