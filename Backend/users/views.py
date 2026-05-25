from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.middleware.csrf import get_token as csrf_get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from .serializers import UserSerializer, UserRegistrationSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from .throttles import (
    LoginThrottle, RegisterThrottle,
    PasswordResetThrottle, PasswordResetEmailThrottle, PasswordResetConfirmThrottle,
    TokenRefreshThrottle,
)
from .models import Profile, PasswordResetToken, AccountLockout, UserSession, UserMFA, BackupCode
from .jwt_cookies import set_jwt_cookies, clear_jwt_cookies
from reports.captcha import verify_recaptcha


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [RegisterThrottle]

    def create(self, request, *args, **kwargs):
        # Validate reCAPTCHA
        captcha_token = request.data.get('captcha')
        try:
            verify_recaptcha(captcha_token, request.META.get('REMOTE_ADDR'))
        except Exception as e:
            return Response({"captcha": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        role = serializer.validated_data.get('role', 'researcher')
        group_name = 'ProgramOwner' if role == 'company' else 'Researcher'

        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "Registration successful. Please check your email to verify your account before logging in."
            },
            status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_groups(request):
    groups = list(request.user.groups.values_list('name', flat=True))
    return Response({
        "groups": groups,
        "is_researcher": 'Researcher' in groups,
        "is_company": 'ProgramOwner' in groups,
        "is_program_owner": 'ProgramOwner' in groups,
        "is_triager": 'Triager' in groups,
        "is_admin": request.user.is_superuser or 'Admin' in groups,
    })


# ---------------------------------------------------------------------------
# Token with email verification check
# ---------------------------------------------------------------------------

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class EmailVerificationTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        from django.contrib.auth import authenticate
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
        user_groups_set = set(user.groups.values_list('name', flat=True))
        if UserMFA.REQUIRED_GROUPS & user_groups_set:
            try:
                mfa = user.mfa
                if not mfa.is_enabled:
                    raise serializers.ValidationError(
                        '2FA is required for your account role. '
                        'Please set up two-factor authentication before logging in.'
                    )
            except UserMFA.DoesNotExist:
                raise serializers.ValidationError(
                    '2FA is required for your account role. '
                    'Please set up two-factor authentication before logging in.'
                )
            # Validate the provided OTP/backup code
            totp_code = attrs.get('totp_code') or self.context.get('request', {}).data.get('totp_code') if hasattr(self.context.get('request', {}), 'data') else None
            if not totp_code:
                raise serializers.ValidationError(
                    {'totp_code': 'A 2FA code is required to log in to this account.'}
                )
            try:
                mfa = user.mfa
                if not mfa.verify_code(str(totp_code)):
                    # Try backup codes
                    if not BackupCode.use_code(user, str(totp_code)):
                        raise serializers.ValidationError(
                            {'totp_code': 'Invalid or expired 2FA code.'}
                        )
            except UserMFA.DoesNotExist:
                raise serializers.ValidationError({'totp_code': 'Invalid or expired 2FA code.'})

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


# ---------------------------------------------------------------------------
# Refresh — reads refresh token from the HttpOnly cookie, rotates it, and
# sets fresh cookies. SimpleJWT's ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
# already handle blacklisting the old token, so reuse of a stolen refresh
# token will fail (and the old session is dead).
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Logout — blacklists the refresh token (so the session is dead immediately)
# and clears both auth cookies. Accepts the refresh token from either the
# cookie or the body.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# CSRF token endpoint — the React app calls this once on app load to get a
# csrftoken cookie it can read and forward as the X-CSRFToken header on
# state-changing requests. AllowAny because you need a CSRF token *before*
# you can log in.
# ---------------------------------------------------------------------------

@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({"csrfToken": csrf_get_token(request)})


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)
        profile.email_verified = True
        profile.email_verification_token = None
        profile.email_verification_sent_at = None
        profile.save()

        # Activate the user
        user = profile.user
        user.is_active = True
        user.save()

        return Response({"detail": "Email verified successfully. You can now log in."})
    except Profile.DoesNotExist:
        return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """Resend verification email to the user"""
    from django.utils import timezone
    from datetime import timedelta

    email = request.data.get('email')
    if not email:
        return Response({"detail": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
        profile = user.profile

        if profile.email_verified:
            return Response({"detail": "Email is already verified"}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limiting: can only resend every 2 minutes
        if profile.email_verification_sent_at:
            time_since_last = timezone.now() - profile.email_verification_sent_at
            if time_since_last < timedelta(minutes=2):
                wait_seconds = int(120 - time_since_last.total_seconds())
                return Response(
                    {"detail": f"Please wait {wait_seconds} seconds before requesting another email"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )

        # Generate new token and send
        import secrets
        from django.core.mail import send_mail
        from django.conf import settings
        token = secrets.token_urlsafe(32)
        profile.email_verification_token = token
        profile.email_verification_sent_at = timezone.now()
        profile.save()

        verify_url = f"http://localhost:3000/verify-email/{token}"

        send_mail(
            subject="Verify your email - BugBounty Platform",
            message=f"Hi {user.first_name or user.username},\n\nPlease click the link below to verify your email address:\n\n{verify_url}\n\nIf you didn't create an account, you can ignore this email.\n\nBest regards,\nBugBounty Team",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"detail": "Verification email sent successfully"})

    except User.DoesNotExist:
        # Don't reveal if email exists or not for security
        return Response({"detail": "If an account exists with this email, a verification email has been sent"})


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class PasswordResetRequestView(generics.GenericAPIView):
    """
    POST /api/users/password-reset/
    Accepts an email address and sends a reset link if the account exists.
    Always returns 200 to prevent email enumeration.
    """
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    # Two independent throttle axes:
    # 1. PasswordResetThrottle   — per source IP (blocks mass requests from one attacker IP)
    # 2. PasswordResetEmailThrottle — per target email (blocks inbox flooding via rotating IPs)
    throttle_classes = [PasswordResetThrottle, PasswordResetEmailThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        GENERIC_RESPONSE = {
            "detail": "If an account with that email exists, a password reset link has been sent."
        }

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Always return 200 — don't leak whether the email is registered
            return Response(GENERIC_RESPONSE, status=status.HTTP_200_OK)

        from django.core.mail import send_mail
        from django.conf import settings as django_settings

        reset_token = PasswordResetToken.create_for_user(user)
        frontend_base = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_base}/reset-password/{reset_token.token}"

        send_mail(
            subject="Reset your BugBounty password",
            message=(
                f"Hi {user.first_name or user.username},\n\n"
                "We received a request to reset your password. Click the link below:\n\n"
                f"{reset_url}\n\n"
                "This link expires in 1 hour and can only be used once.\n\n"
                "If you didn't request a password reset, you can ignore this email.\n\n"
                "— BugBounty Team"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response(GENERIC_RESPONSE, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    POST /api/users/password-reset/confirm/
    Validates the token and sets the new password.
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Audit log the successful reset
        try:
            from audit.models import SecurityAuditLog
            SecurityAuditLog.objects.create(
                user=user,
                action=SecurityAuditLog.ACTION_PASSWORD_RESET_COMPLETE,
                ip_address=request.META.get('REMOTE_ADDR'),
                severity=SecurityAuditLog.SEVERITY_INFO,
                details={"method": "token"},
            )
        except Exception:
            pass  # Audit failure must never block a password reset

        return Response(
            {"detail": "Password has been reset successfully. You can now log in with your new password."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """
    GET /api/users/sessions/
    Returns all active sessions for the current user.
    """
    sessions = UserSession.objects.filter(user=request.user, is_active=True)
    data = [
        {
            'id': s.id,
            'device_name': s.device_name,
            'ip_address': s.ip_address,
            'created_at': s.created_at,
            'last_active': s.last_active,
        }
        for s in sessions
    ]
    return Response({'sessions': data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_id):
    """
    DELETE /api/users/sessions/<id>/
    Revokes a specific session belonging to the current user.
    """
    try:
        session = UserSession.objects.get(id=session_id, user=request.user)
    except UserSession.DoesNotExist:
        return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    session.is_active = False
    session.save(update_fields=['is_active'])
    return Response({'detail': 'Session revoked.'}, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def revoke_all_sessions(request):
    """
    DELETE /api/users/sessions/revoke-all/
    Revokes all active sessions for the current user (logout everywhere).
    """
    count = UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
    return Response({'detail': f'Revoked {count} session(s).'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Two-Factor Authentication (TOTP)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_setup(request):
    """
    POST /api/users/mfa/setup/
    Generates a new TOTP secret and provisioning URI (QR code data).
    Does NOT enable 2FA yet — user must confirm with a valid code first.
    """
    mfa, _ = UserMFA.objects.get_or_create(
        user=request.user,
        defaults={'secret': UserMFA.generate_secret()},
    )
    if not mfa.is_enabled:
        # (Re)generate secret for fresh setup
        mfa.secret = UserMFA.generate_secret()
        mfa.save(update_fields=['secret'])

    return Response({
        'secret': mfa.secret,
        'provisioning_uri': mfa.get_provisioning_uri(),
        'message': 'Scan the QR code with your authenticator app, then confirm with POST /api/users/mfa/confirm/',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_confirm(request):
    """
    POST /api/users/mfa/confirm/  { "code": "123456" }
    Verifies the first TOTP code and activates 2FA. Also generates backup codes.
    """
    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa = request.user.mfa
    except UserMFA.DoesNotExist:
        return Response({'detail': 'Run /api/users/mfa/setup/ first.'}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa.verify_code(str(code)):
        return Response({'detail': 'Invalid code. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa.is_enabled = True
    mfa.save(update_fields=['is_enabled'])

    backup_codes = BackupCode.generate_for_user(request.user)

    return Response({
        'detail': '2FA enabled successfully.',
        'backup_codes': backup_codes,
        'warning': 'Save these backup codes securely. They will not be shown again.',
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_disable(request):
    """
    POST /api/users/mfa/disable/  { "code": "123456" }
    Disables 2FA after verifying the current TOTP code (or a backup code).
    """
    code = request.data.get('code')
    if not code:
        return Response({'detail': 'code is required to disable 2FA.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        mfa = request.user.mfa
    except UserMFA.DoesNotExist:
        return Response({'detail': '2FA is not set up on this account.'}, status=status.HTTP_400_BAD_REQUEST)

    if not mfa.is_enabled:
        return Response({'detail': '2FA is already disabled.'}, status=status.HTTP_400_BAD_REQUEST)

    # Must be a required-group member — they cannot disable 2FA
    user_groups_set = set(request.user.groups.values_list('name', flat=True))
    if UserMFA.REQUIRED_GROUPS & user_groups_set:
        return Response(
            {'detail': '2FA cannot be disabled for Admin/Triager accounts.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not mfa.verify_code(str(code)) and not BackupCode.use_code(request.user, str(code)):
        return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

    mfa.is_enabled = False
    mfa.save(update_fields=['is_enabled'])
    BackupCode.objects.filter(user=request.user).delete()

    return Response({'detail': '2FA has been disabled.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    """
    GET /api/users/mfa/status/
    Returns 2FA setup status for the current user.
    """
    try:
        mfa = request.user.mfa
        enabled = mfa.is_enabled
    except UserMFA.DoesNotExist:
        enabled = False

    user_groups_set = set(request.user.groups.values_list('name', flat=True))
    required = bool(UserMFA.REQUIRED_GROUPS & user_groups_set)

    return Response({
        'is_enabled': enabled,
        'is_required': required,
        'backup_codes_remaining': BackupCode.objects.filter(
            user=request.user, used=False
        ).count() if enabled else 0,
    })
