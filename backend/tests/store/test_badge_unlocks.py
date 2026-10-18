"""Items that belong to badges: free rewards arrive with the badge, priced ones need it first."""
import pytest
from django.core.management import call_command

from badges import services as badge_services
from badges.definitions import BADGES_BY_KEY
from badges.models import UserBadge
from reports.models import BugReport
from store import services
from store.models import Item, UserItem
from wallet import services as wallet


@pytest.fixture(autouse=True)
def default_economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


def accept(user, program, severity="critical"):
    return BugReport.objects.create(
        title=f"{severity} issue", description="A sufficiently long description of the vulnerability for testing.",
        severity=severity, status="accepted", reporter=user, program=program,
    )


def item(slug, price=0, badge="first_blood", **kw):
    return Item.objects.create(slug=slug, name=slug.title(), slot=kw.pop("slot", "hat"), price=price,
                               unlock_badge=badge, **kw)


@pytest.mark.django_db
class TestRewards:
    def test_free_item_arrives_with_the_badge(self, verified_user, program):
        reward = item("bandage", slot="face")
        assert not UserItem.objects.filter(user=verified_user).exists()
        accept(verified_user, program)  # first accepted report: First Blood
        owned = UserItem.objects.get(user=verified_user, item=reward)
        assert owned.price_paid == 0 and owned.transaction is None
        assert wallet.balance(verified_user) == 150  # a gift costs nothing

    def test_other_badges_do_not_unlock_it(self, verified_user, program):
        item("trophy", badge="hoarder")
        accept(verified_user, program)
        assert not UserItem.objects.filter(user=verified_user, item__slug="trophy").exists()

    def test_a_reward_added_later_reaches_people_who_already_have_the_badge(self, verified_user, program):
        accept(verified_user, program)
        late = item("late-reward")
        assert not UserItem.objects.filter(item=late).exists()
        badge_services.evaluate(verified_user)  # what opening the badges page does
        assert UserItem.objects.filter(user=verified_user, item=late).exists()

    def test_granting_twice_gives_one_copy(self, verified_user, program):
        item("once")
        accept(verified_user, program)
        services.grant_badge_rewards(verified_user)
        services.grant_badge_rewards(verified_user)
        assert UserItem.objects.filter(user=verified_user, item__slug="once").count() == 1

    def test_retired_rewards_are_not_granted(self, verified_user, program):
        item("gone", is_active=False)
        accept(verified_user, program)
        assert not UserItem.objects.filter(item__slug="gone").exists()

    def test_a_reward_can_be_worn(self, verified_user, program):
        reward = item("halo")
        accept(verified_user, program)
        services.equip(verified_user, reward)
        assert services.loadout(verified_user.pk)["hat"] == reward


@pytest.mark.django_db
class TestPricedBadgeItems:
    def test_cannot_buy_without_the_badge(self, verified_user, program):
        accept(verified_user, program, "low")  # 10 points: First Blood only
        gated = item("shiny", price=5, badge="critical_thinker")
        with pytest.raises(services.BadgeRequired) as err:
            services.purchase(verified_user, gated)
        assert err.value.badge_key == "critical_thinker"
        assert err.value.badge_name == BADGES_BY_KEY["critical_thinker"].name
        assert wallet.balance(verified_user) == 10  # nothing charged

    def test_can_buy_once_the_badge_is_earned(self, verified_user, program):
        accept(verified_user, program, "critical")  # earns Critical Thinker
        gated = item("shiny", price=5, badge="critical_thinker")
        assert services.purchase(verified_user, gated).price_paid == 5

    def test_priced_items_are_never_given_away(self, verified_user, program):
        item("shiny", price=5, badge="first_blood")
        accept(verified_user, program)
        assert not UserItem.objects.filter(item__slug="shiny").exists()


@pytest.mark.django_db
class TestApi:
    def test_shop_marks_badge_locked_items(self, api_client, verified_user, program):
        accept(verified_user, program, "low")
        item("shiny", price=5, badge="hoarder")
        api_client.force_authenticate(user=verified_user)
        rows = {r["slug"]: r for r in api_client.get("/api/store/items/").data["items"]}
        shiny = rows["shiny"]
        assert shiny["badge_locked"] is True and shiny["unlock_badge_name"] == BADGES_BY_KEY["hoarder"].name

    def test_purchase_error_names_the_badge(self, api_client, verified_user, program):
        accept(verified_user, program, "low")
        item("shiny", price=5, badge="hoarder")
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post("/api/store/items/shiny/purchase/")
        assert resp.status_code == 403
        assert resp.data["code"] == "badge_required" and resp.data["badge"] == "hoarder"

    def test_opening_the_shop_delivers_rewards_for_badges_earned_earlier(self, api_client, verified_user, program):
        accept(verified_user, program)              # badge earned before the item exists
        late = item("late-reward")
        api_client.force_authenticate(user=verified_user)
        rows = {r["slug"]: r for r in api_client.get("/api/store/items/").data["items"]}
        assert rows["late-reward"]["owned"] is True
        assert UserItem.objects.filter(user=verified_user, item=late).exists()

    def test_badges_list_shows_each_badges_rewards(self, api_client, verified_user, program):
        item("bandage", slot="face")
        accept(verified_user, program)
        api_client.force_authenticate(user=verified_user)
        badges = {b["key"]: b for b in api_client.get("/api/badges/").data["badges"]}
        reward = badges["first_blood"]["rewards"][0]
        assert reward["slug"] == "bandage" and reward["owned"] is True
        assert badges["collector"]["rewards"] == []


@pytest.mark.django_db
class TestCatalogue:
    def test_every_badge_has_a_free_reward_and_nothing_points_at_a_missing_badge(self):
        call_command("seed_store")
        gated = Item.objects.exclude(unlock_badge="")
        assert {i.unlock_badge for i in gated} == set(BADGES_BY_KEY)  # one for each of the 8 badges
        assert all(i.price == 0 for i in gated)
        assert Item.objects.count() >= 40
        slots = set(Item.objects.values_list("slot", flat=True))
        assert slots == {"hat", "face", "body", "pet", "background"}

    def test_rewards_are_not_for_sale_without_the_badge(self, api_client, verified_user):
        call_command("seed_store")
        api_client.force_authenticate(user=verified_user)
        assert not UserBadge.objects.filter(user=verified_user).exists()
        rows = api_client.get("/api/store/items/").data["items"]
        assert all(r["badge_locked"] for r in rows if r["unlock_badge"])
