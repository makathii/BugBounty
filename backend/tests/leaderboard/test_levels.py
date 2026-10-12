"""Levels: a pure function of lifetime points, exposed on the leaderboard, wallet and /api/levels/."""
import pytest

from leaderboard import levels
from reports.models import BugReport
from wallet import services as wallet


@pytest.fixture(autouse=True)
def default_economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


def accepted(user, program, severity="critical"):
    return BugReport.objects.create(
        title=f"{severity} issue by {user.username}",
        description="A sufficiently long description of the vulnerability for testing.",
        severity=severity, status="accepted", reporter=user, program=program,
    )


class TestLevelFor:
    @pytest.mark.parametrize("points,level,title", [
        (0, 1, "Bug Sprout"), (49, 1, "Bug Sprout"),
        (50, 2, "Bug Hatchling"), (149, 2, "Bug Hatchling"),
        (150, 3, "Bug Scout"), (350, 4, "Bug Hunter"),
        (3499, 7, "Bug Whisperer"), (3500, 8, "Bug Legend"), (10**6, 8, "Bug Legend"),
    ])
    def test_boundaries(self, points, level, title):
        result = levels.level_for(points)
        assert (result["level"], result["title"]) == (level, title)

    def test_progress_and_next(self):
        result = levels.level_for(100)  # halfway from 50 to 150
        assert result["next_title"] == "Bug Scout" and result["next_at"] == 150
        assert result["points_to_next"] == 50 and result["progress"] == 0.5

    def test_top_level_has_no_next(self):
        result = levels.level_for(5000)
        assert result["next_title"] is None and result["next_at"] is None
        assert result["points_to_next"] == 0 and result["progress"] == 1.0

    @pytest.mark.parametrize("junk", [None, -20, "", 0])
    def test_junk_counts_as_zero(self, junk):
        assert levels.level_for(junk)["level"] == 1

    def test_custom_table(self, settings):
        settings.LEADERBOARD_LEVELS = [(0, "Newbie"), (10, "Pro")]
        assert levels.level_for(10)["title"] == "Pro"

    @pytest.mark.parametrize("bad", [[], [(5, "x")], [(0, "a"), (10, "b"), (10, "c")], [(0, "a"), (9, "b"), (3, "c")]])
    def test_invalid_table_is_rejected(self, settings, bad):
        settings.LEADERBOARD_LEVELS = bad
        with pytest.raises(ValueError):
            levels.level_table()


@pytest.mark.django_db
class TestLevelsInTheApp:
    def test_level_follows_lifetime_points_not_spending(self, api_client, verified_user, program):
        accepted(verified_user, program, "critical")      # 150 -> Bug Scout
        wallet.spend(verified_user, 140, "big purchase")  # balance 10, lifetime still 150
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/levels/me/").data
        assert data["lifetime_points"] == 150 and data["title"] == "Bug Scout"
        assert api_client.get("/api/wallet/").data["level"]["level"] == 3

    def test_levels_me_for_someone_with_no_points(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/levels/me/").data
        assert (data["level"], data["lifetime_points"], data["points_to_next"]) == (1, 0, 50)

    def test_ladder_listing(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        ladder = api_client.get("/api/levels/").data
        assert ladder[0] == {"level": 1, "title": "Bug Sprout", "min_points": 0}
        assert len(ladder) == 8

    def test_requires_auth(self, api_client):
        assert api_client.get("/api/levels/").status_code == 401
        assert api_client.get("/api/levels/me/").status_code == 401

    def test_revoked_points_lower_the_level(self, api_client, verified_user, program):
        report = accepted(verified_user, program, "critical")
        api_client.force_authenticate(user=verified_user)
        assert api_client.get("/api/levels/me/").data["level"] == 3
        report.status = "rejected"
        report.save()
        assert api_client.get("/api/levels/me/").data["level"] == 1

    def test_leaderboard_rows_carry_lifetime_level_even_in_a_short_window(
        self, api_client, verified_user, program
    ):
        from datetime import timedelta
        from django.utils import timezone
        from leaderboard.models import ScoreEvent

        old = accepted(verified_user, program, "critical")   # 150, long ago
        ScoreEvent.objects.filter(report=old).update(awarded_at=timezone.now() - timedelta(days=90))
        accepted(verified_user, program, "low")              # 10, this week
        api_client.force_authenticate(user=verified_user)

        row = api_client.get("/api/leaderboard/?period=weekly").data["results"][0]
        assert row["total_points"] == 10                      # the window's points...
        assert (row["level"], row["level_title"]) == (3, "Bug Scout")  # ...but the lifetime level

    def test_leaderboard_me_and_retrieve_include_level(self, api_client, verified_user, program):
        accepted(verified_user, program, "high")
        api_client.force_authenticate(user=verified_user)
        me = api_client.get("/api/leaderboard/me/").data["result"]
        assert me["level"] == 2 and me["level_title"] == "Bug Hatchling"
        one = api_client.get(f"/api/leaderboard/{verified_user.pk}/").data["result"]
        assert one["level"] == 2

    def test_leaderboard_level_lookup_is_one_extra_query(
        self, api_client, verified_user, second_verified_user, program, django_assert_max_num_queries
    ):
        accepted(verified_user, program)
        accepted(second_verified_user, program)
        api_client.force_authenticate(user=verified_user)
        api_client.get("/api/leaderboard/")  # warm the cache
        with django_assert_max_num_queries(6):
            api_client.get("/api/leaderboard/")
