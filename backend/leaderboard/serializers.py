from rest_framework import serializers


class LeaderboardEntrySerializer(serializers.Serializer):
    """
    One ranked row. Backed by the plain dicts produced by
    ``services.leaderboard_rows`` / ``services.rank_for`` rather than a model,
    because rows are aggregates, not ScoreEvent instances.
    """
    rank = serializers.IntegerField()
    researcher_id = serializers.IntegerField()
    username = serializers.CharField()
    total_points = serializers.IntegerField()
    report_count = serializers.IntegerField()
    last_awarded_at = serializers.DateTimeField()
    # Lifetime level (not the window's points); filled in by the view.
    level = serializers.IntegerField(required=False)
    level_title = serializers.CharField(required=False)
