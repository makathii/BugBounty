"""Badges: earned from the points ledger, kept once earned, with progress for the rest."""
import pytest
from django.core.management import call_command

from badges import services
from badges.definitions import BADGES
from badges.models import UserBadge
from programs.models import Program
from reports.models import BugReport


@pytest.fixture(autouse=True)
def default_economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


def report(user, program, severity="low", status="accepted", **kw):
    return BugReport.objects.create(
        title=f"{severity} {status} by {user.username}",
        description="A sufficiently long description of the vulnerability for testing.",
        severity=severity, status=status, reporter=user, program=program, **kw,
    )


def keys(user):
    return set(UserBadge.objects.filter(user=user).values_list("key", flat=True))


@pytest.fixture
def programs(program):
    extra = [
        Program.objects.create(company=program.company, name=f"P{i}", description="x",
                               scope_type="public", status="active")
        for i in range(2)
    ]
    return [program, *extra]


@pytest.mark.django_db
class TestAwarding:
    def test_nothing_before_any_accepted_report(self, verified_user, program):
        report(verified_user, program, status="open")
        assert keys(verified_user) == set()

    def test_first_accepted_report_earns_first_blood(self, verified_user, program):
        report(verified_user, program)
        assert keys(verified_user) == {"first_blood"}

    def test_accepting_later_awards_on_the_status_change(self, verified_user, program):
        r = report(verified_user, program, status="triaged")
        assert keys(verified_user) == set()
        r.status = "accepted"
        r.save()
        assert "first_blood" in keys(verified_user)

    def test_critical_thinker(self, verified_user, program):
        report(verified_user, program, "critical")
        assert keys(verified_user) == {"first_blood", "critical_thinker"}

    def test_heavy_hitter_needs_three_high_or_critical(self, verified_user, program):
        report(verified_user, program, "high")
        report(verified_user, program, "critical")
        assert "heavy_hitter" not in keys(verified_user)
        report(verified_user, program, "high")
        assert "heavy_hitter" in keys(verified_user)

    def test_low_reports_do_not_count_toward_heavy_hitter(self, verified_user, program):
        for _ in range(3):
            report(verified_user, program, "low")
        assert "heavy_hitter" not in keys(verified_user)

    def test_collector_at_ten(self, verified_user, program):
        for _ in range(9):
            report(verified_user, program)
        assert "collector" not in keys(verified_user)
        report(verified_user, program)
        assert "collector" in keys(verified_user)

    def test_globetrotter_needs_three_programs(self, verified_user, programs):
        report(verified_user, programs[0])
        report(verified_user, programs[1])
        assert "globetrotter" not in keys(verified_user)
        report(verified_user, programs[2])
        assert "globetrotter" in keys(verified_user)

    def test_standout_when_bonus_added_after_acceptance(self, verified_user, program):
        r = report(verified_user, program)
        assert "standout" not in keys(verified_user)
        r.bonus_points = 10
        r.save()
        assert "standout" in keys(verified_user)

    def test_duplicates_never_count(self, verified_user, program):
        report(verified_user, program, status="duplicate")
        assert keys(verified_user) == set()

    def test_badges_are_per_researcher(self, verified_user, second_verified_user, program):
        report(verified_user, program)
        assert keys(second_verified_user) == set()


@pytest.mark.django_db
class TestStreak:
    def test_five_in_a_row(self, verified_user, program):
        for _ in range(5):
            report(verified_user, program)
        assert "clean_streak" in keys(verified_user)

    def test_a_rejection_resets_the_streak(self, verified_user, program):
        for _ in range(4):
            report(verified_user, program)
        report(verified_user, program, status="rejected")
        report(verified_user, program)  # streak is now 1, not 5
        assert "clean_streak" not in keys(verified_user)

    def test_streak_recovers_after_five_more(self, verified_user, program):
        report(verified_user, program, status="rejected")
        for _ in range(5):
            report(verified_user, program)
        assert "clean_streak" in keys(verified_user)

    def test_duplicates_and_open_reports_are_neutral(self, verified_user, program):
        for _ in range(4):
            report(verified_user, program)
        report(verified_user, program, status="duplicate")
        report(verified_user, program, status="open")
        assert "clean_streak" not in keys(verified_user)
        report(verified_user, program)
        assert "clean_streak" in keys(verified_user)


@pytest.mark.django_db
class TestKeepingBadges:
    def test_badge_survives_the_report_being_rejected_later(self, verified_user, program):
        r = report(verified_user, program, "critical")
        assert "critical_thinker" in keys(verified_user)
        r.status = "rejected"
        r.save()
        assert {"first_blood", "critical_thinker"} <= keys(verified_user)

    def test_evaluate_is_idempotent(self, verified_user, program):
        report(verified_user, program)
        assert services.evaluate(verified_user) == []
        assert services.evaluate(verified_user) == []
        assert UserBadge.objects.filter(user=verified_user).count() == 1

    def test_awarded_at_is_kept(self, verified_user, program):
        report(verified_user, program)
        first = UserBadge.objects.get(user=verified_user, key="first_blood").awarded_at
        report(verified_user, program)
        assert UserBadge.objects.get(user=verified_user, key="first_blood").awarded_at == first


@pytest.mark.django_db
class TestAPI:
    def test_requires_auth(self, api_client):
        assert api_client.get("/api/badges/").status_code == 401

    def test_lists_every_badge_with_status_and_progress(self, api_client, verified_user, program):
        for _ in range(4):
            report(verified_user, program)
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/badges/").data
        assert data["total"] == len(BADGES) and data["earned_count"] == 1
        by_key = {b["key"]: b for b in data["badges"]}
        assert by_key["first_blood"]["earned"] and by_key["first_blood"]["awarded_at"]
        collector = by_key["collector"]
        assert not collector["earned"] and collector["awarded_at"] is None
        assert collector["progress"] == {"current": 4, "target": 10}
        assert by_key["first_blood"]["progress"] == {"current": 1, "target": 1}  # capped

    def test_only_sees_own_badges(self, api_client, verified_user, second_verified_user, program):
        report(second_verified_user, program)
        api_client.force_authenticate(user=verified_user)
        assert api_client.get("/api/badges/").data["earned_count"] == 0

    def test_reading_catches_up_pre_existing_researchers(self, api_client, verified_user, program):
        report(verified_user, program)
        UserBadge.objects.all().delete()  # as if badges were added after the points were earned
        api_client.force_authenticate(user=verified_user)
        assert api_client.get("/api/badges/").data["earned_count"] == 1

    def test_read_only(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        assert api_client.post("/api/badges/", {"key": "hoarder"}, format="json").status_code == 405


@pytest.mark.django_db
def test_award_badges_command_backfills(verified_user, program):
    report(verified_user, program, "critical")
    UserBadge.objects.all().delete()
    call_command("award_badges")
    assert {"first_blood", "critical_thinker"} <= keys(verified_user)


@pytest.mark.django_db
def test_badge_keys_are_unique_and_fit_the_column():
    assert len({b.key for b in BADGES}) == len(BADGES)
    assert all(len(b.key) <= 40 for b in BADGES)
