import secrets
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings

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