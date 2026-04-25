import secrets
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from .models import PasswordResetToken

class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'groups')
        read_only_fields = ('id', 'groups')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(
        choices=[('researcher', 'Researcher'), ('company', 'Company')],
        default='researcher',
        write_only=True
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name', 'role')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        from django.utils import timezone
        validated_data.pop('password2')
        validated_data.pop('role', None)  # Remove role before creating user
        user = User.objects.create_user(**validated_data, is_active=False)

        token = secrets.token_urlsafe(32)
        profile = user.profile
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

        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """Step 1: user submits their email address."""
    email = serializers.EmailField()

    def validate_email(self, value):
        # Always return a generic message — never leak whether the email exists
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Step 2: user submits token + new password."""
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(
                token=attrs['token']
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid or expired reset token."})

        if not reset_token.is_valid():
            raise serializers.ValidationError({"token": "This reset link has expired. Please request a new one."})

        attrs['reset_token'] = reset_token
        return attrs

    def save(self):
        reset_token = self.validated_data['reset_token']
        user = reset_token.user

        # Consume token before changing password (prevents re-use even if save() errors)
        reset_token.consume()

        user.set_password(self.validated_data['password'])
        user.save()

        # Invalidate all other pending reset tokens for this user
        PasswordResetToken.objects.filter(user=user, used=False).delete()

        # Send confirmation email
        send_mail(
            subject="Your BugBounty password has been changed",
            message=(
                f"Hi {user.first_name or user.username},\n\n"
                "Your password was successfully reset.\n\n"
                "If you did not make this change, please contact support immediately.\n\n"
                "— BugBounty Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        return user