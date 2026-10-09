from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from . import levels, services
from .serializers import LeaderboardEntrySerializer

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _parse_params(request):
    """
    Pull and validate the shared query params. Returns (params, error_response).
    If error_response is not None, the caller should return it directly.
    """
    period = request.query_params.get("period", "all").lower()
    if period not in services.VALID_PERIODS:
        return None, Response(
            {"error": f"Invalid period. Choose one of: {', '.join(services.VALID_PERIODS)}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    program = request.query_params.get("program")
    if program is not None:
        try:
            program = int(program)
        except (TypeError, ValueError):
            return None, Response(
                {"error": "program must be an integer program id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return {"period": period, "program": program}, None


def _with_levels(rows):
    """Attach each researcher's lifetime level to ranking rows (one query for the page)."""
    info = levels.level_info_for_users([row["researcher_id"] for row in rows])
    return [
        {**row, "level": info[row["researcher_id"]]["level"],
         "level_title": info[row["researcher_id"]]["title"]}
        for row in rows
    ]


class LeaderboardViewSet(viewsets.ViewSet):
    """
    Read-only, computed leaderboard ranking researchers by severity-weighted
    points earned from accepted / resolved reports.

    Endpoints (all require authentication):
      GET /api/leaderboard/                  global ranking
      GET /api/leaderboard/?program=<id>     ranking scoped to one program
      GET /api/leaderboard/?period=weekly    rolling 7-day window
      GET /api/leaderboard/?period=monthly   rolling 30-day window
      GET /api/leaderboard/me/               the caller's own standing
      GET /api/leaderboard/<researcher_id>/  one researcher's standing

    Common query params: period=all|monthly|weekly, program=<id>,
    limit (<= 200), offset.
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        params, err = _parse_params(request)
        if err:
            return err

        try:
            limit = min(int(request.query_params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
            offset = int(request.query_params.get("offset", 0))
        except (TypeError, ValueError):
            return Response(
                {"error": "limit and offset must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        limit = max(limit, 0)
        offset = max(offset, 0)

        page, total = services.leaderboard_page(
            period=params["period"], program=params["program"],
            limit=limit, offset=offset,
        )

        return Response({
            "period": params["period"],
            "program": params["program"],
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": LeaderboardEntrySerializer(_with_levels(page), many=True).data,
        })

    @action(detail=False, methods=["get"])
    def me(self, request):
        """The authenticated caller's own ranking in the selected window."""
        params, err = _parse_params(request)
        if err:
            return err

        row = services.rank_for(
            request.user, period=params["period"], program=params["program"]
        )
        if row is None:
            return Response({
                "period": params["period"],
                "program": params["program"],
                "ranked": False,
                "detail": "No points earned in this window yet.",
            })
        return Response({
            "period": params["period"],
            "program": params["program"],
            "ranked": True,
            "result": LeaderboardEntrySerializer(_with_levels([row])[0]).data,
        })

    def retrieve(self, request, pk=None):
        """One researcher's standing, looked up by their user id."""
        params, err = _parse_params(request)
        if err:
            return err
        try:
            researcher_id = int(pk)
        except (TypeError, ValueError):
            return Response(
                {"error": "researcher id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        row = services.rank_for(
            researcher_id, period=params["period"], program=params["program"]
        )
        if row is None:
            return Response(
                {
                    "period": params["period"],
                    "program": params["program"],
                    "ranked": False,
                    "detail": "This researcher has no points in this window.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            "period": params["period"],
            "program": params["program"],
            "ranked": True,
            "result": LeaderboardEntrySerializer(_with_levels([row])[0]).data,
        })


class LevelViewSet(viewsets.ViewSet):
    """
    GET /api/levels/     the whole ladder (level, title, points needed)
    GET /api/levels/me/  the caller's level and progress toward the next one
    """
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return Response(levels.levels_overview())

    @action(detail=False, methods=["get"])
    def me(self, request):
        points = levels.lifetime_points([request.user.pk]).get(request.user.pk, 0)
        return Response({"lifetime_points": points, **levels.level_for(points)})
