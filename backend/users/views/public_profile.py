"""
Public researcher profiles: the page other researchers open from the leaderboard.

Shows only what is already public on the leaderboard plus the fun parts (character, level, earned
badges, a short bio). Never email, real name or report contents. A researcher can hide the page.
"""
from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.roles import is_admin_or_triager

from ..models import Profile


class OwnProfileSettingsSerializer(serializers.Serializer):
    bio = serializers.CharField(max_length=160, allow_blank=True, required=False, trim_whitespace=True)
    is_public = serializers.BooleanField(required=False)


def _settings_payload(profile):
    return {"bio": profile.bio, "is_public": profile.profile_public}


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def own_profile_settings(request):
    """GET/PATCH /api/users/profile/public/ : the caller's bio and whether their page is visible."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        serializer = OwnProfileSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "bio" in data:
            profile.bio = data["bio"]
        if "is_public" in data:
            profile.profile_public = data["is_public"]
        profile.save(update_fields=["bio", "profile_public"])
    return Response(_settings_payload(profile))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def researcher_profile(request, username):
    """GET /api/users/researchers/<username>/"""
    from badges.definitions import BADGES, researcher_stats
    from badges.models import UserBadge
    from leaderboard import levels, services as leaderboard
    from store import services as store

    user = (
        get_user_model().objects.filter(username__iexact=username, is_active=True)
        .select_related("profile").first()
    )
    if user is None or not user.groups.filter(name="Researcher").exists():
        return Response({"error": "No researcher with that name."}, status=status.HTTP_404_NOT_FOUND)

    profile = getattr(user, "profile", None)
    is_public = profile.profile_public if profile else True
    is_self = user.pk == request.user.pk
    if not is_public and not is_self and not is_admin_or_triager(request):
        # Same answer as for a name that does not exist: a hidden profile is not even confirmed.
        return Response({"error": "No researcher with that name."}, status=status.HTTP_404_NOT_FOUND)

    lifetime = levels.lifetime_points([user.pk]).get(user.pk, 0)
    stats = researcher_stats(user)
    standing = leaderboard.rank_for(user)
    earned = {row.key: row for row in UserBadge.objects.filter(user=user)}
    return Response({
        "username": user.username,
        "member_since": user.date_joined,
        "bio": profile.bio if profile else "",
        "is_self": is_self,
        "is_public": is_public,
        "level": levels.level_for(lifetime),
        "lifetime_points": lifetime,
        "rank": standing["rank"] if standing else None,
        "stats": {
            "accepted": stats["accepted"],
            "critical": stats["critical"],
            "programs": stats["programs"],
            "streak": stats["streak"],
        },
        "badges": [
            {
                "key": b.key, "name": b.name, "icon": b.icon, "description": b.description,
                "awarded_at": earned[b.key].awarded_at,
            }
            for b in BADGES if b.key in earned
        ],
        "badge_total": len(BADGES),
        "loadout": {
            slot: {
                "slug": item.slug, "name": item.name, "slot": item.slot,
                "rarity": item.rarity, "art": item.art, "image_url": item.image_url,
            }
            for slot, item in store.loadout(user.pk).items()
        },
    })
