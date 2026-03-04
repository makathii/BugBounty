from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle

class LoginThrottle(UserRateThrottle):
    scope = 'login'

class RegisterThrottle(UserRateThrottle):
    scope = 'register'

class SubmissionThrottle(ScopedRateThrottle):
    scope = 'submission'
    scope_attr = 'throttle_scope'

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'