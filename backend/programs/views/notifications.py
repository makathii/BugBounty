from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ProgramNotification
from ..serializers import ProgramNotificationSerializer


class ProgramNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProgramNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProgramNotification.objects.filter(
            user=self.request.user
        ).select_related('program')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response({"message": "Marked as read."})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = ProgramNotification.objects.filter(
            user=request.user, read=False
        ).update(read=True)
        return Response({"message": f"{updated} notification(s) marked as read."})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = ProgramNotification.objects.filter(
            user=request.user, read=False
        ).count()
        return Response({"unread_count": count})
