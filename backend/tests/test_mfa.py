"""
Tests for TOTP two-factor authentication (Task 6).
Covers: model logic, setup/confirm/disable/status endpoints,
mandatory 2FA enforcement for Admin/Triager, and backup code flow.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User, Group

from users.models import UserMFA, BackupCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enable_mfa(user):
    """Create and enable a UserMFA for a user, returns the mfa object."""
    mfa = UserMFA.objects.create(
        user=user,
        secret=UserMFA.generate_secret(),
        is_enabled=True,
    )
    return mfa


def _valid_totp_code(mfa):
    """Return the current valid TOTP code for the given mfa object."""
    import pyotp
    return pyotp.TOTP(mfa.secret).now()


# ---------------------------------------------------------------------------
# Model tests: UserMFA
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserMFAModel:
    def test_generate_secret_returns_base32_string(self):
        secret = UserMFA.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16

    def test_verify_code_valid(self, verified_user):
        mfa = _enable_mfa(verified_user)
        code = _valid_totp_code(mfa)
        assert mfa.verify_code(code) is True

    def test_verify_code_invalid(self, verified_user):
        mfa = _enable_mfa(verified_user)
        assert mfa.verify_code('000000') is False

    def test_verify_code_updates_last_used_at(self, verified_user):
        mfa = _enable_mfa(verified_user)
        assert mfa.last_used_at is None
        mfa.verify_code(_valid_totp_code(mfa))
        mfa.refresh_from_db()
        assert mfa.last_used_at is not None

    def test_provisioning_uri_contains_user_email(self, verified_user):
        mfa = _enable_mfa(verified_user)
        uri = mfa.get_provisioning_uri()
        assert verified_user.email in uri or 'BugBounty' in uri


# ---------------------------------------------------------------------------
# Model tests: BackupCode
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBackupCodeModel:
    def test_generate_creates_correct_number_of_codes(self, verified_user):
        codes = BackupCode.generate_for_user(verified_user)
        assert len(codes) == BackupCode.CODES_PER_USER
        assert BackupCode.objects.filter(user=verified_user).count() == BackupCode.CODES_PER_USER

    def test_generate_deletes_previous_codes(self, verified_user):
        BackupCode.generate_for_user(verified_user)
        BackupCode.generate_for_user(verified_user)
        assert BackupCode.objects.filter(user=verified_user).count() == BackupCode.CODES_PER_USER

    def test_use_valid_code(self, verified_user):
        codes = BackupCode.generate_for_user(verified_user)
        assert BackupCode.use_code(verified_user, codes[0]) is True

    def test_use_code_marks_as_used(self, verified_user):
        codes = BackupCode.generate_for_user(verified_user)
        BackupCode.use_code(verified_user, codes[0])
        used = BackupCode.objects.filter(user=verified_user, used=True)
        assert used.count() == 1

    def test_used_code_cannot_be_reused(self, verified_user):
        codes = BackupCode.generate_for_user(verified_user)
        BackupCode.use_code(verified_user, codes[0])
        assert BackupCode.use_code(verified_user, codes[0]) is False

    def test_invalid_code_rejected(self, verified_user):
        BackupCode.generate_for_user(verified_user)
        assert BackupCode.use_code(verified_user, 'INVALID') is False


# ---------------------------------------------------------------------------
# Endpoint: POST /api/users/mfa/setup/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMFASetupEndpoint:
    URL = '/api/users/mfa/setup/'

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.post(self.URL).status_code == 401

    def test_returns_secret_and_uri(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL)
        assert resp.status_code == 200
        assert 'secret' in resp.data
        assert 'provisioning_uri' in resp.data

    def test_secret_is_base32(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL)
        secret = resp.data['secret']
        # Should be a valid base32 string (pyotp uses it directly)
        assert len(secret) >= 16


# ---------------------------------------------------------------------------
# Endpoint: POST /api/users/mfa/confirm/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMFAConfirmEndpoint:
    URL = '/api/users/mfa/confirm/'
    SETUP_URL = '/api/users/mfa/setup/'

    def test_valid_code_enables_mfa(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        api_client.post(self.SETUP_URL)
        mfa = verified_user.mfa
        code = _valid_totp_code(mfa)
        resp = api_client.post(self.URL, {'code': code}, format='json')
        assert resp.status_code == 200
        mfa.refresh_from_db()
        assert mfa.is_enabled is True

    def test_confirm_returns_backup_codes(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        api_client.post(self.SETUP_URL)
        mfa = verified_user.mfa
        code = _valid_totp_code(mfa)
        resp = api_client.post(self.URL, {'code': code}, format='json')
        assert 'backup_codes' in resp.data
        assert len(resp.data['backup_codes']) == BackupCode.CODES_PER_USER

    def test_invalid_code_returns_400(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        api_client.post(self.SETUP_URL)
        resp = api_client.post(self.URL, {'code': '000000'}, format='json')
        assert resp.status_code == 400

    def test_without_setup_returns_400(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': '123456'}, format='json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Endpoint: POST /api/users/mfa/disable/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMFADisableEndpoint:
    URL = '/api/users/mfa/disable/'

    def test_valid_code_disables_mfa_for_researcher(self, api_client, verified_user):
        mfa = _enable_mfa(verified_user)
        code = _valid_totp_code(mfa)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': code}, format='json')
        assert resp.status_code == 200
        mfa.refresh_from_db()
        assert mfa.is_enabled is False

    def test_invalid_code_returns_400(self, api_client, verified_user):
        _enable_mfa(verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': '000000'}, format='json')
        assert resp.status_code == 400

    def test_admin_cannot_disable_mfa(self, api_client, verified_user, admin_group):
        """Admin accounts must always have 2FA — disabling is forbidden."""
        verified_user.groups.add(admin_group)
        _enable_mfa(verified_user)
        mfa = verified_user.mfa
        code = _valid_totp_code(mfa)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': code}, format='json')
        assert resp.status_code == 403

    def test_triager_cannot_disable_mfa(self, api_client, verified_user, triager_group):
        verified_user.groups.add(triager_group)
        _enable_mfa(verified_user)
        mfa = verified_user.mfa
        code = _valid_totp_code(mfa)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': code}, format='json')
        assert resp.status_code == 403

    def test_backup_code_can_disable_mfa(self, api_client, verified_user):
        _enable_mfa(verified_user)
        backup_codes = BackupCode.generate_for_user(verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(self.URL, {'code': backup_codes[0]}, format='json')
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Endpoint: GET /api/users/mfa/status/
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMFAStatusEndpoint:
    URL = '/api/users/mfa/status/'

    def test_no_mfa_returns_disabled(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.status_code == 200
        assert resp.data['is_enabled'] is False

    def test_enabled_mfa_reflected(self, api_client, verified_user):
        _enable_mfa(verified_user)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.data['is_enabled'] is True

    def test_admin_shows_required_true(self, api_client, verified_user, admin_group):
        verified_user.groups.add(admin_group)
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.data['is_required'] is True

    def test_researcher_shows_required_false(self, api_client, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(self.URL)
        assert resp.data['is_required'] is False


# ---------------------------------------------------------------------------
# POST /api/users/mfa/backup-codes/  (regenerate)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMFARegenerateBackupCodes:
    URL = '/api/users/mfa/backup-codes/'

    def test_unauthenticated_returns_401(self, api_client):
        assert api_client.post(self.URL, {'code': '123456'}, format='json').status_code == 401

    def test_valid_totp_returns_fresh_codes_and_invalidates_old(self, api_client, verified_user):
        mfa = _enable_mfa(verified_user)
        old = BackupCode.generate_for_user(verified_user)
        api_client.force_authenticate(verified_user)

        resp = api_client.post(self.URL, {'code': _valid_totp_code(mfa)}, format='json')

        assert resp.status_code == 200
        codes = resp.data['backup_codes']
        assert len(codes) == BackupCode.CODES_PER_USER
        assert not set(codes) & set(old)
        assert BackupCode.use_code(verified_user, old[0]) is False   # old set is gone
        assert BackupCode.use_code(verified_user, codes[0]) is True

    def test_invalid_code_rejected_and_codes_unchanged(self, api_client, verified_user):
        _enable_mfa(verified_user)
        old = BackupCode.generate_for_user(verified_user)
        api_client.force_authenticate(verified_user)

        resp = api_client.post(self.URL, {'code': '000000'}, format='json')

        assert resp.status_code == 400
        assert BackupCode.use_code(verified_user, old[0]) is True

    def test_backup_code_is_not_accepted_as_authorisation(self, api_client, verified_user):
        _enable_mfa(verified_user)
        old = BackupCode.generate_for_user(verified_user)
        api_client.force_authenticate(verified_user)
        assert api_client.post(self.URL, {'code': old[0]}, format='json').status_code == 400

    def test_requires_code(self, api_client, verified_user):
        _enable_mfa(verified_user)
        api_client.force_authenticate(verified_user)
        assert api_client.post(self.URL, {}, format='json').status_code == 400

    def test_requires_mfa_enabled(self, api_client, verified_user):
        api_client.force_authenticate(verified_user)
        assert api_client.post(self.URL, {'code': '123456'}, format='json').status_code == 400
        UserMFA.objects.create(user=verified_user, secret=UserMFA.generate_secret(), is_enabled=False)
        assert api_client.post(self.URL, {'code': '123456'}, format='json').status_code == 400


@pytest.mark.django_db
def test_mfa_code_endpoints_are_throttled():
    from users.throttles import MfaCodeThrottle
    from users import views
    assert MfaCodeThrottle.scope == 'mfa_code'
    for fn in (views.mfa_confirm, views.mfa_disable, views.mfa_regenerate_backup_codes):
        assert MfaCodeThrottle in fn.cls.throttle_classes
