from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .models import WalletTransaction
from .serializers import WalletTransactionSerializer

RECENT = 10
DEFAULT_LIMIT = 25
MAX_LIMIT = 100


class WalletViewSet(viewsets.ViewSet):
    """
    The caller's own points wallet (read-only; spending happens server-side).

      GET /api/wallet/               balance, lifetime earned, total spent, recent activity
      GET /api/wallet/transactions/  paged history (?limit=, ?offset=)
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        recent = WalletTransaction.objects.filter(user=request.user)[:RECENT]
        return Response({
            **services.summary(request.user),
            "recent_transactions": WalletTransactionSerializer(recent, many=True).data,
        })

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        try:
            limit = max(0, min(int(request.query_params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT))
            offset = max(0, int(request.query_params.get("offset", 0)))
        except (TypeError, ValueError):
            return Response(
                {"error": "limit and offset must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = WalletTransaction.objects.filter(user=request.user)
        return Response({
            "count": qs.count(),
            "limit": limit,
            "offset": offset,
            "results": WalletTransactionSerializer(qs[offset:offset + limit], many=True).data,
        })
