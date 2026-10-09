from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from wallet import services as wallet

from . import services
from .models import EquippedItem, Item, UserItem
from .serializers import ItemSerializer, LoadoutItemSerializer


def _context(user):
    """Per-request facts the item serializer needs: what the user owns/wears, level, balance."""
    owned = set(UserItem.objects.filter(user=user).values_list("item_id", flat=True))
    worn = set(
        EquippedItem.objects.filter(user=user).values_list("user_item__item_id", flat=True)
    )
    summary = wallet.summary(user)
    return {
        "owned_ids": owned,
        "equipped_ids": worn,
        "level": summary["level"]["level"],
        "balance": summary["balance"],
    }


def _error(code, message, http_status, **extra):
    return Response({"code": code, "error": message, **extra}, status=http_status)


class StoreViewSet(viewsets.ViewSet):
    """
    The points store.

      GET  /api/store/items/                  shop (?slot=, ?rarity=); flags owned/equipped/locked/can_afford
      POST /api/store/items/{slug}/purchase/  buy
      POST /api/store/items/{slug}/equip/     wear an owned item
      POST /api/store/items/{slug}/unequip/   take it off
      GET  /api/store/inventory/              what you own
      GET  /api/store/loadout/                what you are wearing, by slot
      GET  /api/store/loadout/{user_id}/      what someone else is wearing
    """
    permission_classes = [permissions.IsAuthenticated]

    def _item(self, slug, *, active_only=False):
        qs = Item.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return get_object_or_404(qs, slug=slug)

    def items(self, request):
        qs = Item.objects.filter(is_active=True)
        slot = request.query_params.get("slot")
        rarity = request.query_params.get("rarity")
        if slot:
            qs = qs.filter(slot=slot)
        if rarity:
            qs = qs.filter(rarity=rarity)
        context = _context(request.user)
        return Response({
            "balance": context["balance"],
            "level": context["level"],
            "items": ItemSerializer(qs, many=True, context=context).data,
        })

    def inventory(self, request):
        owned = UserItem.objects.filter(user=request.user).select_related("item")
        context = _context(request.user)
        return Response([
            {
                **ItemSerializer(row.item, context=context).data,
                "purchased_at": row.purchased_at,
                "price_paid": row.price_paid,
            }
            for row in owned
        ])

    def purchase(self, request, slug):
        item = self._item(slug, active_only=True)
        try:
            services.purchase(request.user, item)
        except services.AlreadyOwned as exc:
            return _error(exc.code, str(exc), status.HTTP_409_CONFLICT)
        except services.ItemUnavailable as exc:
            return _error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
        except services.LevelTooLow as exc:
            return _error(
                exc.code, str(exc), status.HTTP_403_FORBIDDEN,
                required_level=exc.required, level=exc.current,
            )
        except services.InsufficientPoints as exc:
            return _error(
                "insufficient_points", str(exc), status.HTTP_400_BAD_REQUEST,
                balance=exc.balance, needed=exc.needed,
            )
        context = _context(request.user)
        return Response(
            {"item": ItemSerializer(item, context=context).data, "balance": context["balance"]},
            status=status.HTTP_201_CREATED,
        )

    def equip(self, request, slug):
        item = self._item(slug)
        try:
            services.equip(request.user, item)
        except services.NotOwned as exc:
            return _error(exc.code, str(exc), status.HTTP_403_FORBIDDEN)
        return Response(self._loadout_payload(request.user.pk))

    def unequip(self, request, slug):
        item = self._item(slug)
        services.unequip(request.user, item)  # idempotent: not wearing it is fine
        return Response(self._loadout_payload(request.user.pk))

    def loadout(self, request, user_id=None):
        target = request.user.pk
        if user_id is not None:
            target = get_object_or_404(get_user_model(), pk=user_id).pk
        return Response(self._loadout_payload(target))

    @staticmethod
    def _loadout_payload(user_id):
        return {
            slot: LoadoutItemSerializer(item).data
            for slot, item in services.loadout(user_id).items()
        }
