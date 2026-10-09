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
from ..mfa_enrollment import MfaEnrollmentRequired, make_enrollment_token
from ..models import AccountLockout, BackupCode, UserMFA, UserSession
from ..throttles import LoginThrottle, TokenRefreshThrottle


class EmailVerificationTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        from django.contrib.auth.models import User
        from rest_framework.exceptions import AuthenticationFailed

        # Get credentials
        username = attrs[self.username_field]
        password = attrs['password']

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
            lockout = AccountLockout.get_or_create_for_user(user)
            lockout.record_failure()
            raise AuthenticationFailed('No active account found with the given credentials')

        # ---- 2FA enforcement for privileged roles ----
        needs_enrollment = False
        user_groups_set = set(user.groups.values_list('name', flat=True))
        if UserMFA.REQUIRED_GROUPS & user_groups_set:
            mfa = UserMFA.objects.filter(user=user).first()
            if mfa is None or not mfa.is_enabled:
                # Cannot log in without 2FA, and cannot set it up without logging in:
                # hand out an enrollment token once the checks below pass.
                needs_enrollment = True
            else:
                # Validate the provided OTP/backup code
                totp_code = attrs.get('totp_code') or self.context.get('request', {}).data.get('totp_code') if hasattr(self.context.get('request', {}), 'data') else None
                if not totp_code:
                    raise serializers.ValidationError(
                        {'totp_code': 'A 2FA code is required to log in to this account.'}
                    )
                if not mfa.verify_code(str(totp_code)):
                    # Try backup codes
                    if not BackupCode.use_code(user, str(totp_code)):
                        raise serializers.ValidationError(
                            {'totp_code': 'Invalid or expired 2FA code.'}
                        )

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

        if needs_enrollment:
            raise MfaEnrollmentRequired(make_enrollment_token(user))

        # Now use the parent validate with the verified user
        # Temporarily mark as active so parent validation works
        was_active = user.is_active
        user.is_active = True
        user.save()

        try:
            result = super().validate(attrs)
            # Successful login — clear any lockout state
            AccountLockout.get_or_create_for_user(user).reset()
            # Record the session using the access token's JTI
            try:
                import jwt as pyjwt
                from django.conf import settings as djsettings
                decoded = pyjwt.decode(
                    result['access'],
                    djsettings.SECRET_KEY,
                    algorithms=['HS256'],
                    options={"verify_exp": False},
                )
                jti = decoded.get('jti', '')
                request = self.context.get('request')
                ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
                ip = request.META.get('REMOTE_ADDR') if request else None
                UserSession.objects.create(
                    user=user,
                    jti=jti,
                    device_name=ua[:100] or 'Unknown device',
                    ip_address=ip,
                    user_agent=ua,
                )
            except Exception:
                pass  # Session tracking must never block login
            return result
        finally:
            # Restore original state (should remain active since they're verified now)
            if not was_active:
                user.is_active = True
                user.save()


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

    blacklisted = False
    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
            blacklisted = True
        except Exception:
            # An invalid token shouldn't break logout — we still clear cookies.
            pass

    # Also deactivate the matching UserSession row (best-effort — failure
    # here must never block logout).
    try:
        from .models import UserSession
        if refresh_token and blacklisted:
            import jwt as pyjwt
            decoded = pyjwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                options={"verify_exp": False},
            )
            jti = decoded.get('jti')
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
