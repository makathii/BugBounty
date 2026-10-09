"""
Tests for account lockout after repeated failed login attempts (Task 4).
"""
import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from users.models import AccountLockout


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccountLockoutModel:
    def test_new_lockout_is_not_locked(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        assert lo.is_locked() is False

    def test_record_failure_increments_counter(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        lo.record_failure()
        lo.refresh_from_db()
        assert lo.failed_attempts == 1

    def test_lockout_triggered_at_threshold(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        for _ in range(AccountLockout.LOCKOUT_THRESHOLD):
            lo.record_failure()
        lo.refresh_from_db()
        assert lo.is_locked() is True
        assert lo.locked_until is not None

    def test_lockout_not_triggered_below_threshold(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        for _ in range(AccountLockout.LOCKOUT_THRESHOLD - 1):
            lo.record_failure()
        lo.refresh_from_db()
        assert lo.is_locked() is False

    def test_reset_clears_lockout(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        for _ in range(AccountLockout.LOCKOUT_THRESHOLD):
            lo.record_failure()
        lo.reset()
        lo.refresh_from_db()
        assert lo.is_locked() is False
        assert lo.failed_attempts == 0

    def test_expired_lockout_auto_clears(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        # Simulate an expired lockout
        past = timezone.now() - timedelta(minutes=AccountLockout.LOCKOUT_DURATION_MINUTES + 1)
        AccountLockout.objects.filter(pk=lo.pk).update(
            failed_attempts=AccountLockout.LOCKOUT_THRESHOLD,
            locked_until=past,
        )
        lo.refresh_from_db()
        assert lo.is_locked() is False  # should auto-clear

    def test_failures_outside_window_reset_counter(self, verified_user):
        lo = AccountLockout.get_or_create_for_user(verified_user)
        # Simulate old failure outside the rolling window
        old_time = timezone.now() - timedelta(minutes=AccountLockout.LOCKOUT_WINDOW_MINUTES + 5)
        AccountLockout.objects.filter(pk=lo.pk).update(
            failed_attempts=AccountLockout.LOCKOUT_THRESHOLD - 1,
            last_failed_at=old_time,
        )
        lo.refresh_from_db()
        lo.record_failure()
        lo.refresh_from_db()
        # Counter should restart from 1, not hit threshold
        assert lo.failed_attempts == 1
        assert lo.is_locked() is False


# ---------------------------------------------------------------------------
# Integration tests via login endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAccountLockoutViaLogin:
    LOGIN_URL = '/api/token/'

    def _fail_login(self, api_client, user, times=1):
        for _ in range(times):
            api_client.post(self.LOGIN_URL, {
                'username': user.username,
                'password': 'wrong-password',
            }, format='json')

    def test_wrong_password_records_failure(self, api_client, verified_user):
        self._fail_login(api_client, verified_user)
        lo = AccountLockout.objects.get(user=verified_user)
        assert lo.failed_attempts >= 1

    def test_account_locked_after_threshold_failures(self, api_client, verified_user):
        self._fail_login(api_client, verified_user, times=AccountLockout.LOCKOUT_THRESHOLD)
        resp = api_client.post(self.LOGIN_URL, {
            'username': verified_user.username,
            'password': 'SafePass123!',  # correct password — still locked
        }, format='json')
        assert resp.status_code == 400
        assert 'locked' in str(resp.data).lower()

    def test_successful_login_clears_lockout(self, api_client, verified_user):
        self._fail_login(api_client, verified_user, times=AccountLockout.LOCKOUT_THRESHOLD - 1)
        # Successful login
        resp = api_client.post(self.LOGIN_URL, {
            'username': verified_user.username,
            'password': 'SafePass123!',
        }, format='json')
        assert resp.status_code == 200
        lo = AccountLockout.objects.get(user=verified_user)
        assert lo.failed_attempts == 0
        assert lo.locked_until is None

    def test_locked_account_still_rejects_correct_password(self, api_client, verified_user):
        """Even a correct password must be rejected while locked — prevents brute-force success."""
        self._fail_login(api_client, verified_user, times=AccountLockout.LOCKOUT_THRESHOLD)
        resp = api_client.post(self.LOGIN_URL, {
            'username': verified_user.username,
            'password': 'SafePass123!',
        }, format='json')
        assert resp.status_code != 200
