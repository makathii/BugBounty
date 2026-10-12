from rest_framework import permissions, viewsets
from rest_framework.response import Response

from . import services


class BadgeViewSet(viewsets.ViewSet):
    """
    GET /api/badges/   every badge with the caller's status and progress

    Reading also re-checks the caller's badges, so researchers who earned points before
    badges existed are caught up the first time they look.
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        services.evaluate(request.user)
        badges = services.overview(request.user)
        return Response({
            "earned_count": sum(1 for b in badges if b["earned"]),
            "total": len(badges),
            "badges": badges,
        })
