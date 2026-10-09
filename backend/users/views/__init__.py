"""
users API views, grouped by concern:

  accounts        registration, profile, role groups
  auth            login token serializer/view, cookie refresh, logout, CSRF
  verification    email verification + resend
  password_reset  password reset request / confirm
  sessions        list / revoke login sessions
  mfa             TOTP setup, confirm, disable, backup codes, forced enrollment

Everything is re-exported here so ``from users.views import ...`` keeps working.
"""

from .accounts import UserProfileView, UserRegistrationView, user_groups
from .auth import (
    CSRFTokenView,
    CookieTokenRefreshView,
    EmailVerificationTokenSerializer,
    ThrottledTokenObtainPairView,
    logout,
)
from .mfa import (
    mfa_confirm,
    mfa_disable,
    mfa_enroll_confirm,
    mfa_enroll_setup,
    mfa_regenerate_backup_codes,
    mfa_setup,
    mfa_status,
)
from .password_reset import PasswordResetConfirmView, PasswordResetRequestView
from .sessions import list_sessions, revoke_all_sessions, revoke_session
from .verification import resend_verification_email, verify_email


__all__ = [
    'UserRegistrationView', 'UserProfileView', 'user_groups',
    'EmailVerificationTokenSerializer', 'ThrottledTokenObtainPairView',
    'CookieTokenRefreshView', 'logout', 'CSRFTokenView',
    'verify_email', 'resend_verification_email',
    'PasswordResetRequestView', 'PasswordResetConfirmView',
    'list_sessions', 'revoke_session', 'revoke_all_sessions',
    'mfa_setup', 'mfa_confirm', 'mfa_disable', 'mfa_regenerate_backup_codes',
    'mfa_enroll_setup', 'mfa_enroll_confirm', 'mfa_status',
]
