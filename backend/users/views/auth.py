from django.conf import settings
from django.middleware.csrf import get_token as csrf_get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ..jwt_cookies import clear_jwt_cookies, set_jwt_cookies
from ..mfa_challenge import (
    InvalidChallengeToken,
    MfaChallengeExpired,
    MfaChallengeRequired,
    make_challenge_token,
    user_for_challenge_token,
)
from ..mfa_enrollment import MfaEnrollmentRequired, make_enrollment_token
from ..models import AccountLockout, BackupCode, UserMFA, UserSession
from ..throttles import LoginThrottle, TokenRefreshThrottle


class EmailVerificationTokenSerializer(TokenObtainPairSerializer):
    """
    Login serializer. Two shapes of request:

      {username, password[, totp_code]}   normal login
      {mfa_token, totp_code}              second step after a ``mfa_required`` answer

    Checks, in order: credentials (or challenge token), account lockout, verified
    email, then 2FA (enrollment for required roles without 2FA, code challenge
    for everyone who has it enabled).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # username/password are not needed when completing a 2FA challenge
        self.fields[self.username_field].required = False
        self.fields['password'].required = False
        self.fields['mfa_token'] = serializers.CharField(required=False, allow_blank=True, write_only=True)
        self.fields['totp_code'] = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def _user_from_password(self, attrs):
        from django.contrib.auth.models import User
        from rest_framework.exceptions import AuthenticationFailed

        username = attrs.get(self.username_field)
        password = attrs.get('password')
        if not username or not password:
            raise serializers.ValidationError({'detail': 'Username and password are required.'})

        # Try to get user directly first (to check if inactive due to unverified email)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                raise AuthenticationFailed('No active account found with the given credentials')

        # Check password manually — record failure if wrong
        if not user.check_password(password):
            AccountLockout.get_or_create_for_user(user).record_failure()
            raise AuthenticationFailed('No active account found with the given credentials')
        return user

    def validate(self, attrs):
        mfa_token = attrs.get('mfa_token')
        if mfa_token:
            try:
                user = user_for_challenge_token(mfa_token)
            except InvalidChallengeToken as exc:
                raise MfaChallengeExpired(str(exc))
        else:
            user = self._user_from_password(attrs)

        # Check account lockout before any further processing
        lockout = AccountLockout.get_or_create_for_user(user)
        if lockout.is_locked():
            from django.utils import timezone as tz
            remaining = int((lockout.locked_until - tz.now()).total_seconds() / 60) + 1
            raise serializers.ValidationError(
                f'Account is temporarily locked due to too many failed attempts. '
                f'Please try again in {remaining} minute(s).'
            )

        # Check if email is verified
        if not user.profile.email_verified:
            raise serializers.ValidationError(
                'Email not verified. Please check your email and verify your account before logging in.'
            )

        # ---- 2FA ----
        mfa = UserMFA.objects.filter(user=user).first()
        mfa_enabled = bool(mfa and mfa.is_enabled)
        required = bool(UserMFA.REQUIRED_GROUPS & set(user.groups.values_list('name', flat=True)))

        if mfa_token and not mfa_enabled:
            # 2FA was switched off after the challenge was issued: the token must never
            # turn into a passwordless, codeless login.
            raise MfaChallengeExpired()

        if required and not mfa_enabled:
            # Cannot log in without 2FA, and cannot set it up without logging in:
            # hand out an enrollment token.
            raise MfaEnrollmentRequired(make_enrollment_token(user))

        if mfa_enabled:
            totp_code = (attrs.get('totp_code') or '').strip()
            if not totp_code:
                if mfa_token:
                    raise serializers.ValidationError({'totp_code': 'A 2FA code is required.'})
                # Password accepted: ask for the code via a short-lived challenge token.
                raise MfaChallengeRequired(make_challenge_token(user))
            if not mfa.verify_code(totp_code) and not BackupCode.use_code(user, totp_code):
                lockout.record_failure()  # guessing codes counts toward the lockout
                raise serializers.ValidationError({'totp_code': 'Invalid or expired 2FA code.'})

        if mfa_token:
            # Password was already verified when the challenge was issued.
            self.user = user
            refresh = self.get_token(user)
            result = {'refresh': str(refresh), 'access': str(refresh.access_token)}
            return self._finish_login(user, result)

        # Now use the parent validate with the verified user
        # Temporarily mark as active so parent validation works
        was_active = user.is_active
        user.is_active = True
        user.save()

        try:
            result = super().validate(attrs)
            return self._finish_login(user, result)
        finally:
            # Restore original state (should remain active since they're verified now)
            if not was_active:
                user.is_active = True
                user.save()

    def _finish_login(self, user, result):
        """Clear lockout state and record the session (best-effort) after a successful login."""
        AccountLockout.get_or_create_for_user(user).reset()
        # Record the session using the access token's JTI
        try:
            import jwt as pyjwt
            decoded = pyjwt.decode(
                result['access'],
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_exp": False},
            )
            request = self.context.get('request')
            ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
            ip = request.META.get('REMOTE_ADDR') if request else None
            UserSession.objects.create(
                user=user,
                jti=decoded.get('jti', ''),
                device_name=ua[:100] or 'Unknown device',
                ip_address=ip,
                user_agent=ua,
            )
        except Exception:
            pass  # Session tracking must never block login
        return result


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/token/  -> {access, refresh} JSON body AND HttpOnly cookies.

    The cookies are the security-critical primary auth mechanism. The JSON
    body is retained for backward compatibility with existing Bearer-token
    integrations and tests; web clients should ignore it and rely on cookies.
    """
    throttle_classes = [LoginThrottle]
    serializer_class = EmailVerificationTokenSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code == 200 and isinstance(response.data, dict):
            access = response.data.get('access')
            refresh = response.data.get('refresh')
            if access:
                set_jwt_cookies(response, access=access, refresh=refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshThrottle]

    def post(self, request, *args, **kwargs):
        # Pull the refresh token from the cookie if the client didn't send it
        # in the body. Body is allowed for old clients but the cookie is the
        # standard path.
        refresh_cookie = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if not data.get('refresh') and refresh_cookie:
            data['refresh'] = refresh_cookie

        if not data.get('refresh'):
            return Response(
                {"detail": "Refresh token not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError) as exc:
            # Clear stale cookies on a bad refresh so the client falls back
            # to the login flow cleanly.
            response = Response(
                {"detail": str(exc) or "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return clear_jwt_cookies(response)

        validated = serializer.validated_data
        response = Response(validated, status=status.HTTP_200_OK)
        # ROTATE_REFRESH_TOKENS=True means validated contains a new refresh
        # too; BLACKLIST_AFTER_ROTATION=True already blacklisted the old one.
        set_jwt_cookies(
            response,
            access=validated['access'],
            refresh=validated.get('refresh'),
        )
        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    refresh_token = (
        request.data.get("refresh_token")
        or request.data.get("refresh")
        or request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
    )

    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
        except Exception:
            # An invalid token shouldn't break logout — we still clear cookies.
            pass

    # Also deactivate the matching UserSession row (best-effort — failure
    # here must never block logout). Sessions are keyed by the *access* token's
    # JTI (see login), so match on the access token of this request; the refresh
    # token carries a different JTI and would never match.
    try:
        access = getattr(request, 'auth', None)
        jti = access.get('jti') if access is not None else None
        if jti:
            UserSession.objects.filter(user=request.user, jti=jti).update(is_active=False)
    except Exception:
        pass

    # Audit log the logout event so security analysts can track session ends.
    # Best-effort — a logging failure must never block the logout response.
    try:
        from audit.models import SecurityAuditLog
        audit_info = getattr(request, 'audit_info', {})
        SecurityAuditLog.log_event(
            action=SecurityAuditLog.ACTION_LOGOUT,
            user=request.user,
            ip_address=audit_info.get('ip_address') or request.META.get('REMOTE_ADDR'),
            user_agent=audit_info.get('user_agent') or request.META.get('HTTP_USER_AGENT', ''),
            success=True,
        )
    except Exception:
        pass

    response = Response({"message": "Successfully logged out"})
    return clear_jwt_cookies(response)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({"csrfToken": csrf_get_token(request)})
