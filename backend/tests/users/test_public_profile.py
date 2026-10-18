"""Public researcher profiles: what is shown, what is never shown, and the opt-out."""
import pytest
from django.contrib.auth.models import Group, User

from reports.models import BugReport
from store.models import Item
from store import services as store

URL = "/api/users/researchers/{}/"


@pytest.fixture(autouse=True)
def default_economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


@pytest.fixture
def ada(db, program):
    user = User.objects.create_user("ada", "ada-private@example.com", "x" * 12, is_active=True,
                                    first_name="Ada", last_name="Lovelace")
    user.groups.add(Group.objects.get_or_create(name="Researcher")[0])
    BugReport.objects.create(
        title="Critical thing", description="A sufficiently long description of the vulnerability for testing.",
        severity="critical", status="accepted", reporter=user, program=program,
    )
    return user


def get(client, viewer, username="ada"):
    client.force_authenticate(user=viewer)
    return client.get(URL.format(username))


@pytest.mark.django_db
class TestVisible:
    def test_shows_level_rank_stats_and_badges(self, api_client, ada, verified_user):
        resp = get(api_client, verified_user)
        assert resp.status_code == 200, resp.data
        d = resp.data
        assert d["username"] == "ada" and d["lifetime_points"] == 150
        assert d["level"]["level"] == 3 and d["rank"] == 1
        assert d["stats"]["accepted"] == 1 and d["stats"]["critical"] == 1
        assert {b["key"] for b in d["badges"]} == {"first_blood", "critical_thinker"}
        assert d["badge_total"] >= 8 and d["is_self"] is False

    def test_never_leaks_private_details(self, api_client, ada, verified_user):
        text = str(get(api_client, verified_user).data)
        for secret in ("ada-private@example.com", "Lovelace", "Critical thing"):
            assert secret not in text

    def test_shows_what_they_wear(self, api_client, ada, verified_user):
        hat = Item.objects.create(slug="cap", name="Cap", slot="hat", price=0, art="🧢")
        store.purchase(ada, hat)
        store.equip(ada, hat)
        assert get(api_client, verified_user).data["loadout"]["hat"]["art"] == "🧢"

    def test_lookup_ignores_case(self, api_client, ada, verified_user):
        assert get(api_client, verified_user, "ADA").data["username"] == "ada"

    def test_researcher_without_points_has_a_page(self, api_client, verified_user):
        resp = get(api_client, verified_user, verified_user.username)
        assert resp.status_code == 200
        assert resp.data["rank"] is None and resp.data["badges"] == [] and resp.data["is_self"] is True

    def test_needs_login(self, api_client, ada):
        assert api_client.get(URL.format("ada")).status_code == 401


@pytest.mark.django_db
class TestNotFound:
    def test_unknown_name(self, api_client, verified_user):
        assert get(api_client, verified_user, "nobody").status_code == 404

    def test_companies_have_no_researcher_page(self, api_client, verified_user, company_user):
        assert get(api_client, verified_user, company_user.username).status_code == 404

    def test_inactive_accounts(self, api_client, ada, verified_user):
        ada.is_active = False
        ada.save()
        assert get(api_client, verified_user).status_code == 404


@pytest.mark.django_db
class TestOptOut:
    def hide(self, client, user, **data):
        client.force_authenticate(user=user)
        return client.patch("/api/users/profile/public/", {"is_public": False, **data}, format="json")

    def test_hidden_profile_looks_like_it_does_not_exist(self, api_client, ada, verified_user):
        assert self.hide(api_client, ada).status_code == 200
        assert get(api_client, verified_user).status_code == 404

    def test_owner_still_sees_their_own_hidden_page(self, api_client, ada):
        self.hide(api_client, ada)
        resp = get(api_client, ada)
        assert resp.status_code == 200 and resp.data["is_public"] is False and resp.data["is_self"] is True

    def test_staff_can_still_open_it(self, api_client, ada, triager_user):
        self.hide(api_client, ada)
        assert get(api_client, triager_user).status_code == 200

    def test_can_show_it_again(self, api_client, ada, verified_user):
        self.hide(api_client, ada)
        api_client.force_authenticate(user=ada)
        api_client.patch("/api/users/profile/public/", {"is_public": True}, format="json")
        assert get(api_client, verified_user).status_code == 200


@pytest.mark.django_db
class TestOwnSettings:
    def test_defaults_then_update_bio(self, api_client, ada, verified_user):
        api_client.force_authenticate(user=ada)
        assert api_client.get("/api/users/profile/public/").data == {"bio": "", "is_public": True}
        resp = api_client.patch("/api/users/profile/public/", {"bio": "  Fuzzing since 2019 "}, format="json")
        assert resp.data["bio"] == "Fuzzing since 2019"
        assert get(api_client, verified_user).data["bio"] == "Fuzzing since 2019"

    def test_bio_is_capped(self, api_client, ada):
        api_client.force_authenticate(user=ada)
        assert api_client.patch("/api/users/profile/public/", {"bio": "x" * 161}, format="json").status_code == 400

    def test_a_bio_is_plain_text_data_not_markup_we_render(self, api_client, ada, verified_user):
        api_client.force_authenticate(user=ada)
        api_client.patch("/api/users/profile/public/", {"bio": "<script>alert(1)</script>"}, format="json")
        # stored verbatim; React escapes it on display (covered by the frontend test)
        assert get(api_client, verified_user).data["bio"] == "<script>alert(1)</script>"

    def test_needs_login(self, api_client):
        assert api_client.get("/api/users/profile/public/").status_code == 401
