"""
Cookie-based JWT authentication.

The auth model:
  - Login (and OAuth callback) sets `bb_access` and `bb_refresh` as HttpOnly,
    Secure (in prod), SameSite=Strict cookies.
  - The browser sends them automatically on every request to this origin.
  - Because the cookies are HttpOnly, *no JavaScript* can read them — XSS bugs
    in the React app cannot exfiltrate the tokens, which is the single biggest
    weakness of the previous localStorage-based scheme.
  - Because they are SameSite=Strict, third-party sites can't trick the
    browser into sending them. We *also* enforce Django's CSRF middleware on
    every state-changing cookie-authenticated request as belt-and-braces.

This module provides:
  - JWTCookieAuthentication: a DRF auth class that pulls the access token out
    of the cookie (or, as a fallback, the Authorization header so existing
    Bearer-token clients keep working).
  - set_jwt_cookies / clear_jwt_cookies: helpers for login/refresh/logout to
    issue or clear the cookie pair on a Response.
"""
from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


# ---------------------------------------------------------------------------
# Helpers — one place that knows how cookies are set and torn down
# ---------------------------------------------------------------------------

def _cookie_kwargs(*, refresh: bool = False) -> dict:
    """Build the kwargs we pass to response.set_cookie().

    Centralised so login, refresh, OAuth callback, and logout all agree on
    the cookie shape (httponly / secure / samesite / path / max_age).
    """
    if refresh:
        max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        path = settings.JWT_AUTH_REFRESH_COOKIE_PATH
    else:
        max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        path = settings.JWT_AUTH_COOKIE_PATH
    return {
        "max_age": max_age,
        "httponly": settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        "secure": settings.JWT_AUTH_COOKIE_SECURE,
        "samesite": settings.JWT_AUTH_COOKIE_SAMESITE,
        "path": path,
    }


def set_jwt_cookies(response, *, access: str, refresh: str | None = None):
    """Attach the access (and optionally refresh) cookie to a Response."""
    response.set_cookie(
        settings.JWT_AUTH_COOKIE,
        access,
        **_cookie_kwargs(refresh=False),
    )
    if refresh is not None:
        response.set_cookie(
            settings.JWT_AUTH_REFRESH_COOKIE,
            refresh,
            **_cookie_kwargs(refresh=True),
        )
    return response


def clear_jwt_cookies(response):
    """Delete both auth cookies — used on logout."""
    response.delete_cookie(
        settings.JWT_AUTH_COOKIE,
        path=settings.JWT_AUTH_COOKIE_PATH,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_AUTH_REFRESH_COOKIE,
        path=settings.JWT_AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE,
    )
    return response


# ---------------------------------------------------------------------------
# CSRF helper — DRF normally turns CSRF off, so when we authenticate via
# cookie we have to put it back on for state-changing requests.
# ---------------------------------------------------------------------------

class _DRFCsrfCheck(CsrfViewMiddleware):
    """A small CsrfViewMiddleware shim used inside DRF auth.

    The base middleware calls reject() with a reason string when the check
    fails; we just need to re-raise that as a DRF AuthenticationFailed so
    the framework returns 403 instead of silently letting the request through.
    """

    def _reject(self, request, reason):
        return reason  # surfaced by the auth class below


def enforce_csrf(request):
    """Run Django's CSRF check against `request`. Raises PermissionDenied if
    the token is missing or wrong."""
    check = _DRFCsrfCheck(get_response=lambda r: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise exceptions.PermissionDenied(f"CSRF Failed: {reason}")


# ---------------------------------------------------------------------------
# DRF authentication class
# ---------------------------------------------------------------------------

class JWTCookieAuthentication(JWTAuthentication):
    """JWT auth that prefers the HttpOnly cookie over the Authorization header.

    Behaviour:
      1. If the request carries the access cookie, validate that token and
         (for unsafe methods) enforce CSRF.
      2. Otherwise fall back to JWTAuthentication (Authorization: Bearer ...).
         This keeps old Bearer-token integrations and tests working during
         the migration.
    """

    def authenticate(self, request):
        cookie_name = getattr(settings, "JWT_AUTH_COOKIE", "bb_access")
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            # No cookie — try the Authorization header.
            return super().authenticate(request)

        # Cookie path. Validate the token first (so a junk cookie 401s rather
        # than blocking the request on CSRF).
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        # CSRF: only enforce for cookie-authenticated unsafe requests, and
        # only if the project opted in.
        if (
            getattr(settings, "JWT_AUTH_CSRF_ENFORCED", True)
            and request.method not in ("GET", "HEAD", "OPTIONS", "TRACE")
        ):
            enforce_csrf(request)

        return (user, validated_token)
