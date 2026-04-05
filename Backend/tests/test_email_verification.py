import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from users.models import Profile
import uuid


@pytest.fixture
def unique_user_payload():
    """Generate unique user data for each test to avoid rate limiting"""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "SafePass123!",
        "password2": "SafePass123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.mark.django_db
def test_register_creates_unverified_user(api_client, unique_user_payload):
    """Test that new users are created with is_active=False"""
    response = api_client.post("/api/users/register/", unique_user_payload, format="json")

    assert response.status_code == 201

    user = User.objects.get(username=unique_user_payload["username"])
    assert user.is_active is False
    assert user.email == unique_user_payload["email"]

    profile = Profile.objects.get(user=user)
    assert profile.email_verified is False
    assert profile.email_verification_token is not None
    assert len(profile.email_verification_token) > 0
    assert profile.email_verification_sent_at is not None


@pytest.mark.django_db
def test_register_sends_verification_email(api_client, unique_user_payload):
    """Test that registration sends verification email"""
    response = api_client.post("/api/users/register/", unique_user_payload, format="json")

    assert response.status_code == 201
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Verify your email - BugBounty Platform"
    assert unique_user_payload["email"] in mail.outbox[0].to


@pytest.mark.django_db
def test_login_fails_for_unverified_user(api_client, unique_user_payload):
    """Test that login fails when email is not verified"""
    # Create unverified user
    api_client.post("/api/users/register/", unique_user_payload, format="json")

    # Attempt login
    response = api_client.post(
        "/api/token/",
        {"username": unique_user_payload["username"], "password": unique_user_payload["password"]},
        format="json",
    )

    # Should fail with validation error (400) not 401
    assert response.status_code == 400
    # Check response contains email verification error message
    assert "email" in str(response.data).lower() and "verified" in str(response.data).lower()


@pytest.mark.django_db
def test_email_verification_activates_user(api_client, unique_user_payload):
    """Test that verification link activates user and clears token"""
    # Register user
    api_client.post("/api/users/register/", unique_user_payload, format="json")
    user = User.objects.get(username=unique_user_payload["username"])
    profile = Profile.objects.get(user=user)
    token = profile.email_verification_token

    # Verify email
    response = api_client.get(f"/api/users/verify-email/{token}/")

    assert response.status_code == 200
    assert "verified successfully" in response.data["detail"].lower()

    # Refresh from database
    user.refresh_from_db()
    profile.refresh_from_db()

    assert user.is_active is True
    assert profile.email_verified is True
    assert profile.email_verification_token is None
    assert profile.email_verification_sent_at is None


@pytest.mark.django_db
def test_login_succeeds_after_verification(api_client, unique_user_payload):
    """Test that login succeeds after email verification"""
    # Register and verify user
    api_client.post("/api/users/register/", unique_user_payload, format="json")
    user = User.objects.get(username=unique_user_payload["username"])
    profile = Profile.objects.get(user=user)

    # Verify email
    api_client.get(f"/api/users/verify-email/{profile.email_verification_token}/")
    user.refresh_from_db()

    # Now login should work
    response = api_client.post(
        "/api/token/",
        {"username": unique_user_payload["username"], "password": unique_user_payload["password"]},
        format="json",
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_invalid_verification_token_returns_error(api_client):
    """Test that invalid/expired tokens return 400 error"""
    response = api_client.get("/api/users/verify-email/invalid-token/")
    assert response.status_code == 400
    assert "invalid" in response.data["detail"].lower()


@pytest.mark.django_db
def test_verification_token_single_use(api_client, unique_user_payload):
    """Test that verification token is single-use"""
    # Register user
    api_client.post("/api/users/register/", unique_user_payload, format="json")
    user = User.objects.get(username=unique_user_payload["username"])
    profile = Profile.objects.get(user=user)
    token = profile.email_verification_token

    # First verification - should succeed
    response1 = api_client.get(f"/api/users/verify-email/{token}/")
    assert response1.status_code == 200

    # Second verification - should fail
    response2 = api_client.get(f"/api/users/verify-email/{token}/")
    assert response2.status_code == 400


@pytest.mark.django_db
def test_resend_verification_email(api_client, unique_user_payload):
    """Test resending verification email"""
    # Register user
    api_client.post("/api/users/register/", unique_user_payload, format="json")
    user = User.objects.get(username=unique_user_payload["username"])
    profile = Profile.objects.get(user=user)
    old_token = profile.email_verification_token

    # Wait to avoid rate limit by setting sent_at to past
    profile.email_verification_sent_at = timezone.now() - timedelta(minutes=5)
    profile.save()

    # Request resend
    response = api_client.post(
        "/api/users/resend-verification/",
        {"email": unique_user_payload["email"]},
        format="json",
    )

    assert response.status_code == 200

    # Check token was updated
    profile.refresh_from_db()
    assert profile.email_verification_token != old_token
    assert profile.email_verification_token is not None


@pytest.mark.django_db
def test_resend_fails_for_verified_user(api_client, unique_user_payload):
    """Test that resend fails if email already verified"""
    # Register and verify user
    api_client.post("/api/users/register/", unique_user_payload, format="json")
    user = User.objects.get(username=unique_user_payload["username"])
    profile = Profile.objects.get(user=user)

    # Verify email
    api_client.get(f"/api/users/verify-email/{profile.email_verification_token}/")

    # Try to resend
    response = api_client.post(
        "/api/users/resend-verification/",
        {"email": unique_user_payload["email"]},
        format="json",
    )

    assert response.status_code == 400
    assert "already verified" in response.data["detail"].lower()


@pytest.mark.django_db
def test_resend_rate_limiting(api_client, unique_user_payload):
    """Test that resend has rate limiting (2 minute cooldown)"""
    # Register user
    api_client.post("/api/users/register/", unique_user_payload, format="json")

    # Try to resend immediately
    response = api_client.post(
        "/api/users/resend-verification/",
        {"email": unique_user_payload["email"]},
        format="json",
    )

    assert response.status_code == 429
    assert "wait" in response.data["detail"].lower()


@pytest.mark.django_db
def test_register_returns_verification_message(api_client, unique_user_payload):
    """Test that registration returns message about email verification"""
    response = api_client.post("/api/users/register/", unique_user_payload, format="json")

    assert response.status_code == 201
    assert "check your email" in response.data["message"].lower() or "verify" in response.data["message"].lower()
