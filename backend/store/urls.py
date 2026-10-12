from django.urls import path

from .views import StoreViewSet

items = StoreViewSet.as_view({"get": "items"})
inventory = StoreViewSet.as_view({"get": "inventory"})
loadout = StoreViewSet.as_view({"get": "loadout"})
purchase = StoreViewSet.as_view({"post": "purchase"})
equip = StoreViewSet.as_view({"post": "equip"})
unequip = StoreViewSet.as_view({"post": "unequip"})

urlpatterns = [
    path("store/items/", items, name="store-items"),
    path("store/items/<slug:slug>/purchase/", purchase, name="store-purchase"),
    path("store/items/<slug:slug>/equip/", equip, name="store-equip"),
    path("store/items/<slug:slug>/unequip/", unequip, name="store-unequip"),
    path("store/inventory/", inventory, name="store-inventory"),
    path("store/loadout/", loadout, name="store-loadout"),
    path("store/loadout/<int:user_id>/", loadout, name="store-loadout-user"),
]
