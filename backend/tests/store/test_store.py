"""The points store: buying (atomic with the wallet), inventory, equipping, and the API."""
import threading

import pytest
from django.core.management import call_command
from django.db import connection

from reports.models import BugReport
from store import services
from store.models import EquippedItem, Item, UserItem
from wallet import services as wallet
from wallet.models import WalletTransaction


@pytest.fixture(autouse=True)
def default_economy(settings):
    settings.LEADERBOARD_SEVERITY_POINTS = {"low": 10, "medium": 30, "high": 70, "critical": 150}


def earn(user, program, severity="critical"):
    return BugReport.objects.create(
        title=f"{severity} issue by {user.username}",
        description="A sufficiently long description of the vulnerability for testing.",
        severity=severity, status="accepted", reporter=user, program=program,
    )


def make_item(slug="party-hat", slot="hat", price=40, **kw):
    return Item.objects.create(slug=slug, name=slug.replace("-", " ").title(), slot=slot, price=price, **kw)


@pytest.fixture
def rich(verified_user, program):
    """150 lifetime points (level 3), balance 150."""
    earn(verified_user, program, "critical")
    return verified_user


@pytest.mark.django_db
class TestPurchase:
    def test_buying_charges_the_wallet_and_fills_the_inventory(self, rich):
        item = make_item(price=40)
        owned = services.purchase(rich, item)
        assert (owned.user, owned.item, owned.price_paid) == (rich, item, 40)
        assert wallet.balance(rich) == 110
        tx = owned.transaction
        assert (tx.amount, tx.kind, tx.reference) == (-40, "purchase", f"item:{item.pk}")

    def test_buying_never_lowers_lifetime_points_or_level(self, rich):
        services.purchase(rich, make_item(price=150))
        assert wallet.balance(rich) == 0
        assert wallet.summary(rich)["lifetime_earned"] == 150
        assert wallet.summary(rich)["level"]["level"] == 3

    def test_cannot_afford(self, verified_user, program):
        earn(verified_user, program, "low")  # 10 points
        item = make_item(price=40)
        with pytest.raises(services.InsufficientPoints):
            services.purchase(verified_user, item)
        assert not UserItem.objects.exists() and not WalletTransaction.objects.exists()

    def test_cannot_buy_twice(self, rich):
        item = make_item(price=10)
        services.purchase(rich, item)
        with pytest.raises(services.AlreadyOwned):
            services.purchase(rich, item)
        assert wallet.balance(rich) == 140  # charged once

    def test_level_gate(self, verified_user, program):
        earn(verified_user, program, "low")  # 10 pts: level 1
        earn(verified_user, program, "critical")  # +150 -> level 3
        gated = make_item("wizard-hat", price=10, min_level=4)
        with pytest.raises(services.LevelTooLow) as exc:
            services.purchase(verified_user, gated)
        assert (exc.value.required, exc.value.current) == (4, 3)
        assert wallet.balance(verified_user) == 160  # nothing charged

    def test_level_gate_uses_lifetime_points_not_balance(self, rich):
        services.purchase(rich, make_item("a", price=140))  # balance 10, lifetime 150
        gated = make_item("b", slot="face", price=5, min_level=3)
        assert services.purchase(rich, gated)

    def test_retired_items_cannot_be_bought(self, rich):
        item = make_item(is_active=False)
        with pytest.raises(services.ItemUnavailable):
            services.purchase(rich, item)

    def test_free_item_costs_nothing_and_leaves_no_transaction(self, verified_user):
        owned = services.purchase(verified_user, make_item("starter-cap", price=0))
        assert owned.price_paid == 0 and owned.transaction is None
        assert not WalletTransaction.objects.exists()

    def test_price_change_after_purchase_does_not_rewrite_history(self, rich):
        item = make_item(price=40)
        owned = services.purchase(rich, item)
        Item.objects.filter(pk=item.pk).update(price=999)
        owned.refresh_from_db()
        assert owned.price_paid == 40

    def test_uses_current_price_not_a_stale_object(self, rich):
        item = make_item(price=40)
        Item.objects.filter(pk=item.pk).update(price=100)
        services.purchase(rich, item)  # `item` still says 40
        assert wallet.balance(rich) == 50

    def test_a_failed_purchase_rolls_everything_back(self, rich, monkeypatch):
        item = make_item(price=40)

        def boom(*a, **k):
            raise RuntimeError("db hiccup")

        monkeypatch.setattr(UserItem.objects, "create", boom)
        with pytest.raises(RuntimeError):
            services.purchase(rich, item)
        assert wallet.balance(rich) == 150  # the points were not kept


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor == "sqlite", reason="needs row locks (PostgreSQL)")
def test_concurrent_purchases_cannot_overdraw_or_duplicate(verified_user, program):
    earn(verified_user, program, "low")  # 10 points
    items = [make_item(f"i{n}", price=10) for n in range(3)]
    same = items[0]
    results = []

    def buy(item):
        try:
            services.purchase(verified_user, item)
            results.append("ok")
        except (services.InsufficientPoints, services.AlreadyOwned):
            results.append("denied")
        finally:
            connection.close()

    threads = [threading.Thread(target=buy, args=(i,)) for i in (*items, same, same)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count("ok") == 1
    assert wallet.balance(verified_user) == 0


@pytest.mark.django_db
class TestEquip:
    def test_equip_and_swap_within_a_slot(self, rich):
        a, b = make_item("a", price=10), make_item("b", price=10)
        services.purchase(rich, a)
        services.purchase(rich, b)
        services.equip(rich, a)
        assert services.loadout(rich.pk) == {"hat": a}
        services.equip(rich, b)
        assert services.loadout(rich.pk) == {"hat": b}
        assert EquippedItem.objects.filter(user=rich).count() == 1

    def test_different_slots_stack(self, rich):
        hat, shades = make_item("h", "hat", 10), make_item("s", "face", 10)
        for item in (hat, shades):
            services.purchase(rich, item)
            services.equip(rich, item)
        assert services.loadout(rich.pk) == {"hat": hat, "face": shades}

    def test_cannot_equip_what_you_dont_own(self, rich):
        with pytest.raises(services.NotOwned):
            services.equip(rich, make_item())

    def test_cannot_equip_someone_elses_item(self, rich, second_verified_user, program):
        earn(second_verified_user, program)
        item = make_item(price=10)
        services.purchase(second_verified_user, item)
        with pytest.raises(services.NotOwned):
            services.equip(rich, item)

    def test_unequip(self, rich):
        item = make_item(price=10)
        services.purchase(rich, item)
        services.equip(rich, item)
        assert services.unequip(rich, item) is True
        assert services.unequip(rich, item) is False  # idempotent
        assert services.loadout(rich.pk) == {}

    def test_retired_items_can_still_be_worn_by_owners(self, rich):
        item = make_item(price=10)
        services.purchase(rich, item)
        Item.objects.filter(pk=item.pk).update(is_active=False)
        services.equip(rich, item)
        assert services.loadout(rich.pk) == {"hat": item}


@pytest.mark.django_db
class TestRefund:
    def test_refund_returns_points_and_unequips(self, rich):
        item = make_item(price=40)
        owned = services.purchase(rich, item)
        services.equip(rich, item)
        services.refund(owned)
        assert wallet.balance(rich) == 150
        assert not UserItem.objects.exists() and not EquippedItem.objects.exists()
        assert services.purchase(rich, item)  # can buy again afterwards

    def test_refunding_a_free_item_just_removes_it(self, verified_user):
        owned = services.purchase(verified_user, make_item("free", price=0))
        services.refund(owned)
        assert not UserItem.objects.exists()


@pytest.mark.django_db
class TestShopAPI:
    def test_requires_auth(self, api_client):
        for url in ("/api/store/items/", "/api/store/inventory/", "/api/store/loadout/"):
            assert api_client.get(url).status_code == 401
        assert api_client.post("/api/store/items/x/purchase/").status_code == 401

    def test_shop_flags(self, api_client, rich):
        cheap = make_item("cheap", price=40)
        pricey = make_item("pricey", "face", price=500)
        gated = make_item("gated", "body", price=10, min_level=5)
        services.purchase(rich, cheap)
        services.equip(rich, cheap)
        make_item("retired", "pet", is_active=False)
        api_client.force_authenticate(user=rich)
        data = api_client.get("/api/store/items/").data
        assert (data["balance"], data["level"]) == (110, 3)
        by = {i["slug"]: i for i in data["items"]}
        assert set(by) == {"cheap", "pricey", "gated"}  # retired hidden
        assert by["cheap"]["owned"] and by["cheap"]["equipped"]
        assert not by["pricey"]["can_afford"] and not by["pricey"]["locked"]
        assert by["gated"]["locked"] and by["gated"]["can_afford"]

    def test_filters(self, api_client, rich):
        make_item("h", "hat", 10)
        make_item("f", "face", 10, rarity="rare")
        api_client.force_authenticate(user=rich)
        assert [i["slug"] for i in api_client.get("/api/store/items/?slot=face").data["items"]] == ["f"]
        assert [i["slug"] for i in api_client.get("/api/store/items/?rarity=rare").data["items"]] == ["f"]

    def test_purchase_success(self, api_client, rich):
        make_item("cap", price=40)
        api_client.force_authenticate(user=rich)
        resp = api_client.post("/api/store/items/cap/purchase/")
        assert resp.status_code == 201
        assert resp.data["balance"] == 110 and resp.data["item"]["owned"] is True

    def test_purchase_errors_have_codes(self, api_client, verified_user, program):
        earn(verified_user, program, "low")  # 10 pts, level 1
        make_item("pricey", price=40)
        make_item("gated", "face", price=1, min_level=3)
        make_item("free", "body", price=0)
        make_item("gone", "pet", price=1, is_active=False)
        api_client.force_authenticate(user=verified_user)

        r = api_client.post("/api/store/items/pricey/purchase/")
        assert (r.status_code, r.data["code"], r.data["balance"], r.data["needed"]) == (
            400, "insufficient_points", 10, 40)
        r = api_client.post("/api/store/items/gated/purchase/")
        assert (r.status_code, r.data["code"], r.data["required_level"]) == (403, "level_too_low", 3)
        assert api_client.post("/api/store/items/free/purchase/").status_code == 201
        r = api_client.post("/api/store/items/free/purchase/")
        assert (r.status_code, r.data["code"]) == (409, "already_owned")
        assert api_client.post("/api/store/items/gone/purchase/").status_code == 404
        assert api_client.post("/api/store/items/nope/purchase/").status_code == 404
        assert wallet.balance(verified_user) == 10  # only the free item "bought"

    def test_purchase_requires_post(self, api_client, rich):
        make_item("cap")
        api_client.force_authenticate(user=rich)
        assert api_client.get("/api/store/items/cap/purchase/").status_code == 405

    def test_inventory(self, api_client, rich, second_verified_user):
        mine = make_item("mine", price=10)
        services.purchase(rich, mine)
        api_client.force_authenticate(user=rich)
        inv = api_client.get("/api/store/inventory/").data
        assert [i["slug"] for i in inv] == ["mine"] and inv[0]["price_paid"] == 10
        api_client.force_authenticate(user=second_verified_user)
        assert api_client.get("/api/store/inventory/").data == []

    def test_equip_unequip_and_loadout(self, api_client, rich):
        make_item("cap", price=10)
        api_client.force_authenticate(user=rich)
        assert api_client.post("/api/store/items/cap/equip/").status_code == 403  # not owned yet
        api_client.post("/api/store/items/cap/purchase/")
        resp = api_client.post("/api/store/items/cap/equip/")
        assert resp.status_code == 200 and resp.data["hat"]["slug"] == "cap"
        assert api_client.get("/api/store/loadout/").data["hat"]["art"] == ""
        resp = api_client.post("/api/store/items/cap/unequip/")
        assert resp.status_code == 200 and resp.data == {}

    def test_anyone_can_see_a_loadout_but_not_change_it(
        self, api_client, rich, second_verified_user
    ):
        make_item("cap", price=10)
        services.purchase(rich, Item.objects.get(slug="cap"))
        services.equip(rich, Item.objects.get(slug="cap"))
        api_client.force_authenticate(user=second_verified_user)
        assert api_client.get(f"/api/store/loadout/{rich.pk}/").data["hat"]["slug"] == "cap"
        assert api_client.get("/api/store/loadout/999999/").status_code == 404
        assert api_client.post("/api/store/items/cap/equip/").status_code == 403
        assert services.loadout(rich.pk)["hat"].slug == "cap"  # untouched

    def test_shop_query_count_is_flat(self, api_client, rich, django_assert_max_num_queries):
        for n in range(15):
            make_item(f"i{n}", price=1)
        api_client.force_authenticate(user=rich)
        with django_assert_max_num_queries(12):
            assert api_client.get("/api/store/items/").status_code == 200


@pytest.mark.django_db
def test_seed_store_is_idempotent_and_keeps_edits():
    call_command("seed_store")
    count = Item.objects.count()
    assert count >= 10 and Item.objects.filter(price=0).exists()
    Item.objects.filter(slug="party-hat").update(price=77)
    call_command("seed_store")
    assert Item.objects.count() == count
    assert Item.objects.get(slug="party-hat").price == 77
    assert len({i.slug for i in Item.objects.all()}) == count


@pytest.mark.django_db
class TestLeaderboardShowsOutfits:
    def test_rows_carry_the_loadout(self, api_client, rich, second_verified_user, program):
        earn(second_verified_user, program, "low")
        hat = make_item("cap", price=10, art="🧢")
        services.purchase(rich, hat)
        services.equip(rich, hat)
        api_client.force_authenticate(user=rich)
        rows = {r["username"]: r for r in api_client.get("/api/leaderboard/").data["results"]}
        assert rows[rich.username]["loadout"]["hat"]["art"] == "🧢"
        assert rows[second_verified_user.username]["loadout"] == {}
        me = api_client.get("/api/leaderboard/me/").data["result"]
        assert me["loadout"]["hat"]["slug"] == "cap"

    def test_loadouts_for_is_one_query(self, rich, second_verified_user, django_assert_num_queries):
        with django_assert_num_queries(1):
            services.loadouts_for([rich.pk, second_verified_user.pk])
