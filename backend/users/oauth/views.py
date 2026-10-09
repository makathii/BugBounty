"""
OAuth2 client login endpoints.

Flow:

  1.  GET  /api/users/oauth/<provider>/start/
      Returns ``{"authorize_url": "..."}``. The frontend redirects the
      browser to that URL. The endpoint also sets a short-lived signed
      ``oauth_state`` cookie tied to a random nonce.

  2.  GET  /api/users/oauth/<provider>/callback/?code=...&state=...
      The provider redirects the user's browser here. We:

      - verify ``state`` against the signed cookie (CSRF protection on the
        OAuth handshake itself)
      - exchange the ``code`` for an access token
      - fetch the user's profile from the provider
      - find or create the matching Django ``User`` and ``SocialAccount``
      - issue our own JWT cookies (HttpOnly, Secure, SameSite=Strict)
      - redirect the browser to ``FRONTEND_URL`` so the React app sees the
        cookie and continues

A misconfigured provider (no client_id/secret in settings) returns 503.
Throttling is per-IP via OAuthInitThrottle / OAuthCallbackThrottle.
"""
from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import signing
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from ..jwt_cookies import set_jwt_cookies
from ..models import Profile, SocialAccount, UserSession
from .providers import OAuthError, OAuthProvider, PROVIDERS
from ..throttles import OAuthCallbackThrottle, OAuthInitThrottle


STATE_COOKIE_NAME = "bb_oauth_state"
STATE_MAX_AGE = 600  # 10 minutes — plenty for a normal OAuth flow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sign_state(payload: dict) -> str:
    return signing.dumps(payload, salt="bb-oauth-state")


def _unsign_state(token: str) -> dict:
    # max_age enforces server-side expiry independent of cookie max_age.
    return signing.loads(token, salt="bb-oauth-state", max_age=STATE_MAX_AGE)


def _provider_or_503(provider_name: str):
    if provider_name not in PROVIDERS:
        return None, Response(
            {"detail": f"Unknown OAuth provider: {provider_name}."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        return OAuthProvider(provider_name), None
    except OAuthError as exc:
        return None, Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def _unique_username(base: str, email: str) -> str:
    """Pick a username that doesn't collide with an existing User row."""
    candidate = (base or email.split("@", 1)[0] or "user").lower()
    candidate = "".join(ch for ch in candidate if ch.isalnum() or ch in "-_") or "user"
    if not User.objects.filter(username=candidate).exists():
        return candidate
    for _ in range(20):
        suffix = secrets.token_hex(3)
        c = f"{candidate}-{suffix}"
        if not User.objects.filter(username=c).exists():
            return c
    # Fall back to a fully random name; collisions are astronomically unlikely.
    return f"user-{secrets.token_hex(6)}"


def _get_or_create_user(provider: str, info: dict) -> User:
    """Return the User this OAuth identity maps to, creating one if needed."""
    # 1. Already linked via SocialAccount? Just return them.
    try:
        social = SocialAccount.objects.get(provider=provider, provider_uid=info["provider_uid"])
        social.email = info.get("email", social.email)
        social.raw_profile = info
        social.last_login_at = timezone.now()
        social.save(update_fields=["email", "raw_profile", "last_login_at"])
        return social.user
    except SocialAccount.DoesNotExist:
        pass

    email = (info.get("email") or "").strip().lower()

    # 2. There's an existing user with this email AND the provider asserts the
    #    email is verified — link them. Without `email_verified=True` we MUST
    #    NOT auto-link, because that would let an attacker who controls
    #    "victim@gmail.com" at a sloppy provider take over the victim's account.
    user = None
    if email and info.get("email_verified"):
        user = User.objects.filter(email__iexact=email).first()

    # 3. No match at all — provision a new user.
    created = False
    if user is None:
        username = _unique_username(info.get("username", ""), email)
        # Random unusable password — login can only happen via OAuth or a
        # password-reset flow that the user explicitly initiates.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=secrets.token_urlsafe(32),
            is_active=True,
        )
        created = True

    # Email coming from an OAuth provider that asserted verification is good
    # enough for us — skip the email-verification gate.
    profile, _ = Profile.objects.get_or_create(user=user)
    if info.get("email_verified") and not profile.email_verified:
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])

    # New users default to the Researcher role on this platform.
    if created:
        researcher, _ = Group.objects.get_or_create(name="Researcher")
        user.groups.add(researcher)

    SocialAccount.objects.create(
        user=user,
        provider=provider,
        provider_uid=info["provider_uid"],
        email=email,
        raw_profile=info,
    )
    return user


def _record_session(user: User, refresh: RefreshToken, request) -> None:
    """Mirror what TokenObtainPairSerializer does so /api/users/sessions/
    sees this OAuth session like any other."""
    try:
        jti = refresh.access_token.get("jti")
        ua = request.META.get("HTTP_USER_AGENT", "")
        ip = request.META.get("REMOTE_ADDR")
        UserSession.objects.create(
            user=user,
            jti=jti or "",
            device_name=(ua[:100] or "OAuth login"),
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        # Never block login on session-tracking failures.
        pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([OAuthInitThrottle])
def oauth_start(request, provider: str):
    """Issue the authorize URL and a signed state cookie."""
    prov, err = _provider_or_503(provider)
    if err is not None:
        return err

    nonce = secrets.token_urlsafe(24)
    next_url = request.GET.get("next") or settings.FRONTEND_URL
    state = _sign_state({"n": nonce, "p": provider, "next": next_url})

    response = Response({"authorize_url": prov.authorize_url(state=state)})
    response.set_cookie(
        STATE_COOKIE_NAME,
        state,
        max_age=STATE_MAX_AGE,
        httponly=True,
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        samesite="Lax",  # Lax (not Strict): the cookie must come back when
                        # the provider redirects the browser to /callback/.
        path="/api/users/oauth/",
    )
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([OAuthCallbackThrottle])
def oauth_callback(request, provider: str):
    """Exchange code, fetch userinfo, mint cookies, redirect to the frontend."""
    prov, err = _provider_or_503(provider)
    if err is not None:
        return err

    code = request.GET.get("code")
    state = request.GET.get("state")
    state_cookie = request.COOKIES.get(STATE_COOKIE_NAME)

    if not code or not state:
        return Response(
            {"detail": "Missing code or state parameter."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not state_cookie or state_cookie != state:
        # State cookie/parameter mismatch — likely a CSRF attempt or a
        # browser that lost the cookie. Refuse.
        return Response(
            {"detail": "Invalid OAuth state."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = _unsign_state(state)
    except signing.BadSignature:
        return Response(
            {"detail": "OAuth state failed signature check."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if payload.get("p") != provider:
        return Response(
            {"detail": "OAuth state does not match this provider."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        prov.exchange_code(code)
        info = prov.fetch_user_info()
    except OAuthError as exc:
        return Response(
            {"detail": f"OAuth exchange failed: {exc}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = _get_or_create_user(provider, info)
    refresh = RefreshToken.for_user(user)
    _record_session(user, refresh, request)

    # Redirect the *browser* back to the frontend. The cookies travel along
    # because they're scoped to this origin.
    redirect_to = payload.get("next") or settings.FRONTEND_URL
    response = HttpResponseRedirect(redirect_to)
    set_jwt_cookies(response, access=str(refresh.access_token), refresh=str(refresh))
    response.delete_cookie(STATE_COOKIE_NAME, path="/api/users/oauth/")
    return response
