"""
OAuth2 provider definitions for client-login (GitHub, Google, GitLab).

Each provider knows three things:

  - where to redirect the browser to start the flow (`authorize_url`)
  - where to exchange the authorisation code for an access token (`token_url`)
  - how to fetch the user's profile and normalise it into our internal shape

The standardised shape returned by `fetch_user_info()` is a dict with at
least: ``provider_uid`` (string, stable id at the provider), ``email``,
``email_verified`` (bool — whether the provider asserts the email is
verified), and ``username``.

We do **not** depend on django-allauth or dj-rest-auth. allauth pulls in its
own user model integration and template stack, which would conflict with the
project's existing email-verification, MFA, lockout, and session-tracking
flows. A small auditable implementation is the safer trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import requests
from django.conf import settings


class OAuthError(Exception):
    """Raised on provider misconfiguration or any failed exchange."""


@dataclass
class ProviderConfig:
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    parse_userinfo: Callable[[dict, "OAuthProvider"], dict]
    email_url: str | None = None  # optional second call for providers
                                  # whose userinfo doesn't include email


# --- per-provider userinfo parsers ----------------------------------------

def _parse_github(data: dict, provider: "OAuthProvider") -> dict:
    # GitHub's /user endpoint returns email only if the user made it public.
    # If we got nothing, fetch /user/emails and pick the primary verified one.
    email = data.get("email") or ""
    email_verified = False
    if not email:
        try:
            resp = requests.get(
                "https://api.github.com/user/emails",
                headers=provider._auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                emails = resp.json()
                primary = next(
                    (e for e in emails if e.get("primary") and e.get("verified")),
                    None,
                ) or next((e for e in emails if e.get("verified")), None)
                if primary:
                    email = primary.get("email", "")
                    email_verified = bool(primary.get("verified"))
        except requests.RequestException:
            # Network blip — proceed with what we have rather than 500ing.
            pass
    return {
        "provider_uid": str(data["id"]),
        "email": email,
        "email_verified": email_verified or bool(email),
        "username": data.get("login") or "",
    }


def _parse_google(data: dict, provider: "OAuthProvider") -> dict:
    return {
        "provider_uid": str(data["sub"]),
        "email": data.get("email", ""),
        "email_verified": bool(data.get("email_verified")),
        "username": data.get("email", "").split("@", 1)[0],
    }


def _parse_gitlab(data: dict, provider: "OAuthProvider") -> dict:
    return {
        "provider_uid": str(data["id"]),
        "email": data.get("email", ""),
        # GitLab marks email as confirmed via `confirmed_at`.
        "email_verified": bool(data.get("confirmed_at")),
        "username": data.get("username") or "",
    }


# --- registry --------------------------------------------------------------

PROVIDERS: dict[str, ProviderConfig] = {
    "github": ProviderConfig(
        name="github",
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
        scope="read:user user:email",
        parse_userinfo=_parse_github,
    ),
    "google": ProviderConfig(
        name="google",
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scope="openid email profile",
        parse_userinfo=_parse_google,
    ),
    "gitlab": ProviderConfig(
        name="gitlab",
        authorize_url="https://gitlab.com/oauth/authorize",
        token_url="https://gitlab.com/oauth/token",
        userinfo_url="https://gitlab.com/api/v4/user",
        scope="read_user",
        parse_userinfo=_parse_gitlab,
    ),
}


# --- runtime provider object ----------------------------------------------

class OAuthProvider:
    """Wraps a ProviderConfig with the per-request access token + creds."""

    def __init__(self, name: str):
        if name not in PROVIDERS:
            raise OAuthError(f"Unknown provider: {name}")
        creds = settings.OAUTH_PROVIDERS.get(name, {})
        if not creds.get("client_id") or not creds.get("client_secret"):
            raise OAuthError(f"Provider {name} is not configured.")
        self.name = name
        self.config = PROVIDERS[name]
        self.client_id = creds["client_id"]
        self.client_secret = creds["client_secret"]
        # scope from settings overrides the default
        self.scope = creds.get("scope") or self.config.scope
        self._access_token: str | None = None

    # The redirect_uri must match exactly what's registered with the provider.
    @property
    def redirect_uri(self) -> str:
        base = settings.BACKEND_PUBLIC_URL.rstrip("/")
        return f"{base}/api/users/oauth/{self.name}/callback/"

    def authorize_url(self, *, state: str) -> str:
        from urllib.parse import urlencode
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
            "response_type": "code",
            # `access_type=offline` tells Google to issue a refresh token; harmless
            # to send to other providers but they'll ignore it.
            "access_type": "offline",
            "prompt": "select_account",
        }
        return f"{self.config.authorize_url}?{urlencode(params)}"

    def exchange_code(self, code: str) -> str:
        """Trade authorization code for an access token. Returns the token."""
        resp = requests.post(
            self.config.token_url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code != 200:
            raise OAuthError(f"Token exchange failed ({resp.status_code}).")
        try:
            payload = resp.json()
        except ValueError:
            raise OAuthError("Provider returned non-JSON token response.")
        token = payload.get("access_token")
        if not token:
            raise OAuthError("Provider did not return an access_token.")
        self._access_token = token
        return token

    def _auth_headers(self) -> dict:
        if not self._access_token:
            raise OAuthError("No access token; call exchange_code() first.")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "User-Agent": "BugBountyPlatform-OAuth-Client/1.0",
        }

    def fetch_user_info(self) -> dict:
        """Return a normalised user-info dict (see module docstring)."""
        resp = requests.get(
            self.config.userinfo_url,
            headers=self._auth_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            raise OAuthError(f"User info request failed ({resp.status_code}).")
        try:
            data = resp.json()
        except ValueError:
            raise OAuthError("Provider returned non-JSON userinfo.")
        info = self.config.parse_userinfo(data, self)
        if not info.get("provider_uid"):
            raise OAuthError("Provider did not return a stable user id.")
        return info
