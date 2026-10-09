from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle, AnonRateThrottle

class LoginThrottle(UserRateThrottle):
    scope = 'login'

class RegisterThrottle(UserRateThrottle):
    scope = 'register'

class SubmissionThrottle(ScopedRateThrottle):
    scope = 'submission'
    scope_attr = 'throttle_scope'

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class PasswordResetThrottle(AnonRateThrottle):
    """Per-IP throttle for password reset requests.

    AnonRateThrottle keys on the client IP address so even unauthenticated
    callers are limited.  This prevents brute-force reset requests from a
    single source IP.
    """
    scope = 'password_reset'

class PasswordResetEmailThrottle(AnonRateThrottle):
    """Per-target-email throttle for password reset requests.

    An attacker with rotating IPs can bypass the per-IP throttle but still
    flood a victim's inbox.  This throttle keys on the *target email address*
    so each email address is limited independently of the source IP.
    Rate is defined by 'password_reset_email' in DEFAULT_THROTTLE_RATES.
    """
    scope = 'password_reset_email'

    def get_cache_key(self, request, view):
        # Extract email from the POST body (safe — no auth required).
        email = (request.data.get('email') or '').lower().strip()
        if not email:
            # No email in body → fall back to IP (parent behaviour).
            return super().get_cache_key(request, view)
        ident = f"pwd_reset_email:{email}"
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }

class PasswordResetConfirmThrottle(AnonRateThrottle):
    """Per-IP throttle for password reset confirmation.

    AnonRateThrottle (IP-keyed) prevents a single source from brute-forcing
    reset tokens even if the tokens are somehow predictable.
    """
    scope = 'password_reset_confirm'


class TokenRefreshThrottle(AnonRateThrottle):
    """Throttle the cookie-refresh endpoint. AnonRateThrottle keys on IP so
    it works whether or not the client is currently authenticated."""
    scope = 'token_refresh'


class OAuthInitThrottle(AnonRateThrottle):
    """Throttle the OAuth `start` endpoint by IP."""
    scope = 'oauth_init'


class OAuthCallbackThrottle(AnonRateThrottle):
    """Throttle the OAuth callback. The provider redirects the *user's
    browser* here with an authorization code, so IP throttling is the right
    key — multiple users behind the same NAT will share a bucket but the
    rate is generous enough to absorb that."""
    scope = 'oauth_callback'


class MfaCodeThrottle(UserRateThrottle):
    """Limits endpoints that check a TOTP/backup code for an already
    authenticated user, so a stolen session cannot brute-force the 6-digit
    code (or disable 2FA) at full speed."""
    scope = 'mfa_code'


class MfaEnrollThrottle(AnonRateThrottle):
    """Pre-login 2FA enrollment endpoints, keyed by IP (the caller has no
    session yet; the signed enrollment token is the credential)."""
    scope = 'mfa_enroll'
