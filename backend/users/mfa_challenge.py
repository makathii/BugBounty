"""
Second step of login for accounts that have 2FA enabled.

Password-correct login returns a short-lived, signed **challenge token** instead
of JWTs. The client then posts ``{mfa_token, totp_code}`` (no password again) to
the same login endpoint. The token alone grants nothing: it only lets the holder
*attempt* a code, and every wrong attempt counts toward the account lockout.
It expires after 5 minutes and dies if the password changes.
"""
from django.contrib.auth.models import User
from django.core import signing
from rest_framework.exceptions import APIException

CHALLENGE_SALT = 'users.mfa-challenge.v1'
CHALLENGE_MAX_AGE = 5 * 60  # seconds


class MfaChallengeRequired(APIException):
    """Login response: password accepted, now send the 2FA code."""
    status_code = 400
    default_code = 'mfa_required'

    def __init__(self, token):
        super().__init__(detail={
            'detail': 'Enter the code from your authenticator app.',
            'code': 'mfa_required',
            'mfa_token': token,
            # Kept for API clients that predate the challenge token.
            'totp_code': ['A 2FA code is required to log in to this account.'],
        })


class MfaChallengeExpired(APIException):
    """The challenge token is bad/expired/revoked: the client must start over."""
    status_code = 400
    default_code = 'mfa_token_expired'

    def __init__(self, message='This sign-in step has expired. Please sign in again.'):
        super().__init__(detail={'detail': message, 'code': 'mfa_token_expired'})


class InvalidChallengeToken(Exception):
    pass


def _fingerprint(user):
    return user.password[-16:]


def make_challenge_token(user):
    return signing.dumps({'uid': user.pk, 'pw': _fingerprint(user)}, salt=CHALLENGE_SALT)


def user_for_challenge_token(token):
    expired = InvalidChallengeToken('This sign-in step has expired. Please sign in again.')
    try:
        data = signing.loads(token, salt=CHALLENGE_SALT, max_age=CHALLENGE_MAX_AGE)
        user = User.objects.get(pk=data['uid'])
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError):
        raise expired
    if data.get('pw') != _fingerprint(user):
        raise expired
    return user
