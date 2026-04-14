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