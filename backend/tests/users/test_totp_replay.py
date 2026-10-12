"""A one-time code must be usable once (RFC 6238 section 5.2). Found by the full-program browser test."""
import threading
import time

import pyotp
import pytest
from django.db import connection

from users.models import UserMFA


@pytest.fixture
def mfa(verified_user):
    return UserMFA.objects.create(user=verified_user, secret=pyotp.random_base32(), is_enabled=True)


def code_at(mfa, offset_seconds=0):
    return pyotp.TOTP(mfa.secret).at(time.time() + offset_seconds)


@pytest.mark.django_db
class TestVerifyCode:
    def test_a_fresh_code_is_accepted_once_then_refused(self, mfa):
        code = code_at(mfa)
        assert mfa.verify_code(code) is True
        assert mfa.verify_code(code) is False  # the replay

    def test_the_replay_is_refused_even_through_a_fresh_object(self, mfa):
        code = code_at(mfa)
        assert mfa.verify_code(code) is True
        again = UserMFA.objects.get(pk=mfa.pk)  # e.g. the next request
        assert again.verify_code(code) is False

    def test_a_later_code_still_works(self, mfa):
        assert mfa.verify_code(code_at(mfa)) is True
        assert mfa.verify_code(code_at(mfa, +30)) is True

    def test_an_older_code_is_refused_after_a_newer_one_was_used(self, mfa):
        assert mfa.verify_code(code_at(mfa, +30)) is True
        assert mfa.verify_code(code_at(mfa, -30)) is False  # still "valid" by the clock, but older
        assert mfa.verify_code(code_at(mfa)) is False

    def test_clock_drift_of_one_step_is_still_tolerated(self, mfa):
        assert mfa.verify_code(code_at(mfa, -30)) is True

    @pytest.mark.parametrize("bad", ["", "000000", "12345", "abcdef", None, "1234567"])
    def test_wrong_codes_are_refused_and_do_not_burn_a_step(self, mfa, bad):
        assert mfa.verify_code(bad) is False
        assert UserMFA.objects.get(pk=mfa.pk).last_used_step is None
        assert mfa.verify_code(code_at(mfa)) is True  # the real code is unaffected

    def test_whitespace_around_a_valid_code_is_ignored(self, mfa):
        assert mfa.verify_code(f" {code_at(mfa)} ") is True

    def test_records_when_it_was_used(self, mfa):
        mfa.verify_code(code_at(mfa))
        mfa.refresh_from_db()
        assert mfa.last_used_at is not None and mfa.last_used_step is not None


@pytest.mark.django_db
class TestReplayOverTheLoginApi:
    def login(self, api_client, user, code):
        return api_client.post(
            "/api/token/", {"username": user.username, "password": "SafePass123!", "totp_code": code}, format="json"
        )

    def test_the_same_code_cannot_log_in_twice(self, api_client, verified_user, mfa):
        verified_user.set_password("SafePass123!")
        verified_user.save()
        code = code_at(mfa)
        assert self.login(api_client, verified_user, code).status_code == 200
        assert self.login(api_client, verified_user, code).status_code in (400, 401)


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(connection.vendor == "sqlite", reason="needs real concurrent transactions (PostgreSQL)")
def test_two_simultaneous_attempts_with_one_code_cannot_both_succeed(mfa):
    code = code_at(mfa)
    results = []

    def attempt():
        try:
            results.append(UserMFA.objects.get(pk=mfa.pk).verify_code(code))
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1
