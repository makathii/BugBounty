"""
Forced 2FA enrollment for roles that must have 2FA (Admin / Triager).

The chicken-and-egg problem: those roles cannot log in until 2FA is enabled,
but every 2FA setup endpoint needs a logged-in session. So when such a user
presents a *correct password* and has no active 2FA, login answers with a
short-lived, signed **enrollment token** instead of JWTs. The token can do
exactly one thing: set up and confirm TOTP for that one user
(``/api/users/mfa/enroll/setup|confirm/``). It grants no API access, and it
stops working as soon as 2FA is enabled, the password changes, or it expires.
After confirming, the user signs in normally with a TOTP / backup code.
"""
from django.contrib.auth.models import User
from django.core import signing
from rest_framework.exceptions import APIException

from .models import UserMFA

ENROLLMENT_SALT = 'users.mfa-enrollment.v1'
ENROLLMENT_MAX_AGE = 15 * 60  # seconds


class MfaEnrollmentRequired(APIException):
    """Login response for a required-2FA user who has not enrolled yet."""
    status_code = 400
    default_code = 'mfa_enrollment_required'

    def __init__(self, token):
        super().__init__(detail={
            'detail': ('Two-factor authentication is required for your account role. '
                       'You will now be guided through setting it up.'),
            'code': 'mfa_enrollment_required',
            'enrollment_token': token,
        })


class InvalidEnrollmentToken(Exception):
    pass


def _password_fingerprint(user):
    # Ties the token to the current password hash: changing it revokes the token.
    return user.password[-16:]


def make_enrollment_token(user):
    return signing.dumps({'uid': user.pk, 'pw': _password_fingerprint(user)}, salt=ENROLLMENT_SALT)


def user_for_enrollment_token(token):
    """Return the user a valid token belongs to, or raise InvalidEnrollmentToken."""
    try:
        data = signing.loads(token, salt=ENROLLMENT_SALT, max_age=ENROLLMENT_MAX_AGE)
        user = User.objects.get(pk=data['uid'])
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError):
        raise InvalidEnrollmentToken('This setup link has expired. Please sign in again.')

    if data.get('pw') != _password_fingerprint(user):
        raise InvalidEnrollmentToken('This setup link has expired. Please sign in again.')

    required = bool(UserMFA.REQUIRED_GROUPS & set(user.groups.values_list('name', flat=True)))
    if not required:
        raise InvalidEnrollmentToken('This setup link is not valid for your account.')

    mfa = UserMFA.objects.filter(user=user).first()
    if mfa and mfa.is_enabled:
        raise InvalidEnrollmentToken('Two-factor authentication is already enabled. Please sign in.')
    return user
