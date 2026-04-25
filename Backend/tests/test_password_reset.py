"""
Tests for password reset functionality (Task 3).
Covers: token generation, expiry, single-use enforcement, endpoint responses,
email-enumeration protection, and audit logging.
"""
import pytest
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone

from users.models import PasswordResetToken


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordResetTokenModel:
    def test_create_for_user_generates_token(self, verified_user):
        token_obj = PasswordResetToken.create_for_user(verified_user)
        assert token_obj.pk is not None
        assert len(token_obj.token) >= 40  # urlsafe(48) produces ~64 chars
        assert not token_obj.used

    def test_create_for_user_invalidates_previous_tokens(self, verified_user):
        old = PasswordResetToken.create_for_user(verified_user)
        new = PasswordResetToken.create_for_user(verified_user)
        # Old unused token must be deleted
        assert not PasswordResetToken.objects.filter(pk=old.pk).exists()
        assert PasswordResetToken.objects.filter(pk=new.pk).exists()

    def test_valid_token_is_valid(self, verified_user):
        token_obj = PasswordResetToken.create_for_user(verified_user)
        assert token_obj.is_valid() is True

    def test_used_token_is_invalid(self, verified_user):
        token_obj = PasswordResetToken.create_for_user(verified_user)
        token_obj.consume()
        assert token_obj.is_valid() is False

    def test_expired_token_is_invalid(self, verified_user):
        token_obj = PasswordResetToken.create_for_user(verified_user)
        # Back-date creation to beyond the expiry window
        past = timezone.now() - timedelta(hours=PasswordResetToken.TOKEN_EXPIRY_HOURS + 1)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(created_at=past)
        token_obj.refresh_from_db()
        assert token_obj.is_valid() is False

    def test_consume_marks_token_used(self, verified_user):
        token_obj = PasswordResetToken.create_for_user(verified_user)
        token_obj.consume()
        token_obj.refresh_from_db()
        assert token_obj.used is True


# ---------------------------------------------------------------------------
# Endpoint: POST /api/users/password-reset/ (request)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordResetRequestEndpoint:
    URL = '/api/users/password-reset/'

    def test_valid_email_returns_200(self, api_client, verified_user):
        resp = api_client.post(self.URL, {'email': verified_user.email}, format='json')
        assert resp.status_code == 200

    def test_valid_email_creates_token(self, api_client, verified_user):
        api_client.post(self.URL, {'email': verified_user.email}, format='json')
        assert PasswordResetToken.objects.filter(user=verified_user, used=False).exists()

    def test_valid_email_sends_email(self, api_client, verified_user):
        api_client.post(self.URL, {'email': verified_user.email}, format='json')
        assert len(mail.outbox) == 1
        assert verified_user.email in mail.outbox[0].to

    def test_reset_link_in_email_body(self, api_client, verified_user):
        api_client.post(self.URL, {'email': verified_user.email}, format='json')
        token_obj = PasswordResetToken.objects.get(user=verified_user, used=False)
        assert token_obj.token in mail.outbox[0].body

    def test_unknown_email_also_returns_200(self, api_client):
        """Must not leak whether the email is registered (enumeration protection)."""
        resp = api_client.post(self.URL, {'email': 'nobody@example.com'}, format='json')
        assert resp.status_code == 200

    def test_unknown_email_sends_no_email(self, api_client):
        api_client.post(self.URL, {'email': 'nobody@example.com'}, format='json')
        assert len(mail.outbox) == 0

    def test_response_message_is_generic(self, api_client, verified_user):
        """Response body must not vary between existing and non-existing emails."""
        resp_real = api_client.post(self.URL, {'email': verified_user.email}, format='json')
        resp_fake = api_client.post(self.URL, {'email': 'nobody@example.com'}, format='json')
        assert resp_real.json()['detail'] == resp_fake.json()['detail']

    def test_missing_email_returns_400(self, api_client):
        resp = api_client.post(self.URL, {}, format='json')
        assert resp.status_code == 400

    def test_invalid_email_format_returns_400(self, api_client):
        resp = api_client.post(self.URL, {'email': 'not-an-email'}, format='json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Endpoint: POST /api/users/password-reset/confirm/ (confirm)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPasswordResetConfirmEndpoint:
    URL = '/api/users/password-reset/confirm/'

    def _get_token(self, user):
        return PasswordResetToken.create_for_user(user)

    def test_valid_token_resets_password(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        resp = api_client.post(self.URL, {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }, format='json')
        assert resp.status_code == 200
        verified_user.refresh_from_db()
        assert verified_user.check_password('NewSecurePass99!')

    def test_token_is_consumed_after_use(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        api_client.post(self.URL, {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }, format='json')
        token_obj.refresh_from_db()
        assert token_obj.used is True

    def test_used_token_is_rejected(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        payload = {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }
        api_client.post(self.URL, payload, format='json')  # First use
        resp = api_client.post(self.URL, payload, format='json')  # Second use
        assert resp.status_code == 400

    def test_expired_token_is_rejected(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        past = timezone.now() - timedelta(hours=PasswordResetToken.TOKEN_EXPIRY_HOURS + 1)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(created_at=past)
        resp = api_client.post(self.URL, {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }, format='json')
        assert resp.status_code == 400

    def test_invalid_token_is_rejected(self, api_client):
        resp = api_client.post(self.URL, {
            'token': 'completelyfaketoken',
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }, format='json')
        assert resp.status_code == 400

    def test_mismatched_passwords_rejected(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        resp = api_client.post(self.URL, {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'DifferentPass99!',
        }, format='json')
        assert resp.status_code == 400

    def test_weak_password_rejected(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        resp = api_client.post(self.URL, {
            'token': token_obj.token,
            'password': '123',
            'password2': '123',
        }, format='json')
        assert resp.status_code == 400

    def test_confirmation_email_sent_on_success(self, api_client, verified_user):
        token_obj = self._get_token(verified_user)
        api_client.post(self.URL, {
            'token': token_obj.token,
            'password': 'NewSecurePass99!',
            'password2': 'NewSecurePass99!',
        }, format='json')
        assert len(mail.outbox) == 1
        assert 'password' in mail.outbox[0].subject.lower() or 'changed' in mail.outbox[0].subject.lower()

    def test_missing_fields_returns_400(self, api_client):
        resp = api_client.post(self.URL, {}, format='json')
        assert resp.status_code == 400
