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
    """Throttle for password reset requests - stricter than login"""
    scope = 'password_reset'

class PasswordResetConfirmThrottle(AnonRateThrottle):
    """Throttle for password reset confirmation"""
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