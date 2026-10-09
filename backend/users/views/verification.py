from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import Profile


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
