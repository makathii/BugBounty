from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User, Group
from .serializers import UserSerializer, UserRegistrationSerializer
from .throttles import LoginThrottle, RegisterThrottle
from rest_framework.permissions import AllowAny
from .models import Profile
from reports.captcha import verify_recaptcha

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
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

        # Get role from validated data (default to researcher)
        role = serializer.validated_data.get('role', 'researcher')

        # Assign to appropriate group
        if role == 'company':
            group_name = 'Company'
        else:
            group_name = 'Researcher'

        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            group = Group.objects.create(name=group_name)

        user.groups.add(group)

        return Response(
            {
                "user": UserSerializer(user).data,
                "message": "Registration successful. Please check your email to verify your account before logging in."
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_groups(request):
    # Get current user's groups
    groups = request.user.groups.values_list('name', flat=True)
    return Response({"groups": list(groups)})

# users/views.py
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data["refresh_token"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "Successfully logged out"}, status=200)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=400)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def users_api_root(request):
    return Response({
        'register': '/api/users/register/',
        'profile': '/api/users/profile/',
        'groups': '/api/users/groups/'
    })

# Override TokenObtainPairView to add throttling and email verification check
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

class EmailVerificationTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from django.contrib.auth.models import User

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
                raise serializers.ValidationError('No active account found with the given credentials')

        # Check password manually
        if not user.check_password(password):
            raise serializers.ValidationError('No active account found with the given credentials')

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
            return super().validate(attrs)
        finally:
            # Restore original state (should remain active since they're verified now)
            if not was_active:
                user.is_active = True
                user.save()


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]
    serializer_class = EmailVerificationTokenSerializer

#Email verification
@api_view(["GET"])
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