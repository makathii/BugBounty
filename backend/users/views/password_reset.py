from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import PasswordResetToken
from ..serializers import PasswordResetConfirmSerializer, PasswordResetRequestSerializer
from ..throttles import (
    PasswordResetConfirmThrottle,
    PasswordResetEmailThrottle,
    PasswordResetThrottle,
)


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
