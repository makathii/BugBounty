"""Points wallet: balance = earned (ScoreEvent) + transactions; spending never touches the leaderboard."""
import threading

import pytest
from django.db import IntegrityError, connection

from leaderboard import services as board
from leaderboard.models import ScoreEvent
from reports.models import BugReport
from wallet import services
from wallet.models import WalletTransaction


@pytest.fixture(autouse=True)
def small_point_table(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


def accepted(user, program, severity="high", **kw):
    return BugReport.objects.create(
        title=f"{severity} issue by {user.username}",
        description="A sufficiently long description of the vulnerability for testing.",
        severity=severity, status="accepted", reporter=user, program=program, **kw,
    )


@pytest.mark.django_db
class TestBalance:
    def test_new_user_has_nothing(self, verified_user):
        summary = services.summary(verified_user)
        assert {k: summary[k] for k in ("balance", "lifetime_earned", "total_spent")} == {
            "balance": 0, "lifetime_earned": 0, "total_spent": 0,
        }
        assert summary["level"]["level"] == 1

    def test_earned_points_become_balance(self, verified_user, program):
        accepted(verified_user, program, "high")
        accepted(verified_user, program, "low", bonus_points=5)
        assert services.balance(verified_user) == 70 + 15

    def test_spending_lowers_balance_but_not_leaderboard(self, verified_user, program):
        accepted(verified_user, program, "critical")
        services.spend(verified_user, 100, "Cool hat", reference="item:1")
        assert services.balance(verified_user) == 50
        summary = services.summary(verified_user)
        assert {k: summary[k] for k in ("balance", "lifetime_earned", "total_spent")} == {
            "balance": 50, "lifetime_earned": 150, "total_spent": 100,
        }
        assert summary["level"]["level"] == 3  # level follows lifetime points, not balance
        assert board.rank_for(verified_user)["total_points"] == 150

    def test_revoked_report_reduces_balance(self, verified_user, program):
        report = accepted(verified_user, program, "high")
        report.status = "rejected"
        report.save()
        assert services.balance(verified_user) == 0

    def test_users_are_isolated(self, verified_user, second_verified_user, program):
        accepted(verified_user, program)
        services.spend(verified_user, 10, "x")
        assert services.balance(second_verified_user) == 0


@pytest.mark.django_db
class TestSpend:
    def test_cannot_overspend(self, verified_user, program):
        accepted(verified_user, program, "low")
        with pytest.raises(services.InsufficientPoints) as exc:
            services.spend(verified_user, 11, "too pricey")
        assert (exc.value.balance, exc.value.needed) == (10, 11)
        assert WalletTransaction.objects.count() == 0

    def test_can_spend_exact_balance(self, verified_user, program):
        accepted(verified_user, program, "low")
        services.spend(verified_user, 10, "all in")
        assert services.balance(verified_user) == 0

    @pytest.mark.parametrize("bad", [0, -5, 1.5, "10", True, None])
    def test_rejects_invalid_amounts(self, verified_user, program, bad):
        accepted(verified_user, program)
        with pytest.raises(ValueError):
            services.spend(verified_user, bad, "nope")

    def test_spend_records_a_negative_purchase(self, verified_user, program):
        accepted(verified_user, program)
        tx = services.spend(verified_user, 20, "Party hat", reference="item:7")
        assert (tx.amount, tx.kind, tx.reference) == (-20, "purchase", "item:7")

    def test_long_reason_is_truncated_not_crashing(self, verified_user, program):
        accepted(verified_user, program)
        assert len(services.spend(verified_user, 1, "x" * 500).reason) == 200


@pytest.mark.django_db
class TestRefundAndAdjust:
    def test_refund_returns_points_once(self, verified_user, program):
        accepted(verified_user, program, "high")
        purchase = services.spend(verified_user, 40, "Oops")
        refund = services.refund(purchase)
        assert refund.amount == 40 and refund.kind == "refund"
        assert services.balance(verified_user) == 70
        with pytest.raises(ValueError):
            services.refund(purchase)
        assert services.balance(verified_user) == 70

    def test_only_purchases_can_be_refunded(self, verified_user):
        grant = services.adjust(verified_user, 10, "welcome")
        with pytest.raises(ValueError):
            services.refund(grant)

    def test_adjust_grant_and_clawback(self, verified_user, triager_user):
        services.adjust(verified_user, 50, "Event prize", created_by=triager_user)
        assert services.balance(verified_user) == 50
        tx = services.adjust(verified_user, -20, "Correction", created_by=triager_user)
        assert services.balance(verified_user) == 30 and tx.created_by == triager_user

    @pytest.mark.parametrize("bad", [0, 2.5, None, True])
    def test_adjust_rejects_invalid(self, verified_user, bad):
        with pytest.raises(ValueError):
            services.adjust(verified_user, bad, "x")

    def test_zero_amount_rows_are_blocked_by_the_database(self, verified_user):
        with pytest.raises(IntegrityError):
            WalletTransaction.objects.create(user=verified_user, amount=0, kind="adjustment", reason="x")


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor == "sqlite", reason="needs row locks (PostgreSQL)")
def test_concurrent_spends_cannot_overdraw(verified_user, program):
    accepted(verified_user, program, "low")  # 10 points
    results = []

    def buy():
        try:
            services.spend(verified_user, 10, "race")
            results.append("ok")
        except services.InsufficientPoints:
            results.append("denied")
        finally:
            connection.close()

    threads = [threading.Thread(target=buy) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == ["denied"] * 3 + ["ok"]


@pytest.mark.django_db
class TestWalletAPI:
    def test_requires_auth(self, api_client):
        assert api_client.get("/api/wallet/").status_code == 401
        assert api_client.get("/api/wallet/transactions/").status_code == 401

    def test_summary_and_recent_activity(self, api_client, verified_user, program):
        accepted(verified_user, program, "high")
        services.spend(verified_user, 30, "Sunglasses", reference="item:2")
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/wallet/").data
        assert (data["balance"], data["lifetime_earned"], data["total_spent"]) == (40, 70, 30)
        assert [t["reason"] for t in data["recent_transactions"]] == ["Sunglasses"]
        assert data["recent_transactions"][0]["amount"] == -30
        assert data["recent_transactions"][0]["kind_display"] == "Purchase"

    def test_only_sees_own_wallet(self, api_client, verified_user, second_verified_user, program):
        accepted(second_verified_user, program)
        services.spend(second_verified_user, 10, "theirs")
        api_client.force_authenticate(user=verified_user)
        data = api_client.get("/api/wallet/").data
        assert data["balance"] == 0 and data["recent_transactions"] == []
        assert api_client.get("/api/wallet/transactions/").data["count"] == 0

    def test_transactions_are_paged_newest_first(self, api_client, verified_user):
        for i in range(5):
            services.adjust(verified_user, 1, f"gift {i}")
        api_client.force_authenticate(user=verified_user)
        page = api_client.get("/api/wallet/transactions/?limit=2&offset=1").data
        assert page["count"] == 5
        assert [t["reason"] for t in page["results"]] == ["gift 3", "gift 2"]

    def test_bad_paging_params(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        assert api_client.get("/api/wallet/transactions/?limit=abc").status_code == 400

    def test_wallet_is_read_only(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        assert api_client.post("/api/wallet/", {"amount": 999}, format="json").status_code == 405
        assert api_client.post("/api/wallet/transactions/", {}, format="json").status_code == 405


@pytest.mark.django_db
class TestAcceptEndpointAwardsPoints:
    def accept(self, client, triager, report, **payload):
        client.force_authenticate(user=triager)
        return client.post(f"/api/reports/{report.id}/accept/", payload, format="json")

    def test_accept_awards_severity_points_and_bonus(self, api_client, triager_user, triaged_report):
        resp = self.accept(api_client, triager_user, triaged_report, bonus_points=15)
        assert resp.status_code == 200
        assert resp.data["bonus_points"] == 15
        severity_points = board.points_for_severity(triaged_report.severity)
        assert resp.data["points_awarded"] == severity_points + 15
        assert services.balance(triaged_report.reporter) == severity_points + 15

    def test_accept_without_bonus(self, api_client, triager_user, triaged_report):
        resp = self.accept(api_client, triager_user, triaged_report)
        assert resp.status_code == 200 and resp.data["bonus_points"] == 0
        assert resp.data["points_awarded"] > 0

    @pytest.mark.parametrize("bad", [-1, 1001, "lots", 2.5e10])
    def test_bad_bonus_is_rejected_and_nothing_changes(
        self, api_client, triager_user, triaged_report, bad
    ):
        resp = self.accept(api_client, triager_user, triaged_report, bonus_points=bad)
        assert resp.status_code == 400
        triaged_report.refresh_from_db()
        assert triaged_report.status == "triaged"
        assert not ScoreEvent.objects.filter(report=triaged_report).exists()

    def test_researcher_cannot_set_bonus_when_submitting_or_editing(
        self, api_client, verified_user, own_report
    ):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            f"/api/reports/{own_report.id}/", {"bonus_points": 999}, format="json"
        )
        own_report.refresh_from_db()
        assert own_report.bonus_points == 0, resp.data

    def test_report_api_exposes_points_awarded(self, api_client, triager_user, triaged_report):
        self.accept(api_client, triager_user, triaged_report, bonus_points=5)
        resp = api_client.get(f"/api/reports/{triaged_report.id}/")
        assert resp.data["points_awarded"] == ScoreEvent.objects.get(report=triaged_report).points
        assert resp.data["bonus_points"] == 5
