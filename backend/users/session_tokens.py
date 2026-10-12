"""
Revocable sessions on top of stateless JWTs.

Every login mints a random session id (``sid``) that is carried by BOTH the access and the refresh
token (so it survives refresh rotation) and stored in ``UserSession.jti``. Revoking a session
(logout, "sign out everywhere", a password reset) marks that row inactive, and
``is_session_revoked`` is checked on every authenticated request and every token refresh, so a
revoked token stops working immediately instead of living until it expires.

Tokens issued before this existed carry no ``sid``; they are left alone (they expire on their own)
except by ``revoke_all_sessions``, which also blacklists the user's outstanding refresh tokens.
"""
import uuid

from .models import UserSession

SESSION_CLAIM = "sid"


def new_session_id():
    return uuid.uuid4().hex


def tag_with_new_session(refresh):
    """Give a freshly created RefreshToken its session id (before deriving the access token)."""
    refresh[SESSION_CLAIM] = new_session_id()
    # simplejwt records the refresh token string when it is created; keep that record in step
    # with the token we actually hand out (matters to anything that looks tokens up by string).
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        OutstandingToken.objects.filter(jti=refresh["jti"]).update(token=str(refresh))
    except Exception:
        pass  # blacklist app not installed / token not recorded: nothing to keep in step
    return refresh


def session_id_of(token):
    """The session id carried by an access/refresh token (dict-like), or None for legacy tokens."""
    try:
        return token.get(SESSION_CLAIM)
    except Exception:
        return None


def is_session_revoked(token):
    sid = session_id_of(token)
    return bool(sid) and UserSession.objects.filter(jti=sid, is_active=False).exists()


def revoke_all_sessions(user):
    """Sign the user out everywhere: deactivate every session and blacklist every outstanding
    refresh token (the latter also covers legacy tokens that carry no ``sid``)."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    count = UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)
    return count
