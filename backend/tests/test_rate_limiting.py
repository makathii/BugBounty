"""
Tests for rate limiting configuration.
"""
import pytest
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

# NOTE: Do NOT import from users.views at module level here.
# users.views is first imported on the first HTTP request inside a test, at
# which point the conftest disable_throttling fixture has already replaced the
# throttle class references.  A module-level import would load users.views
# *before* any fixture runs, caching the real throttle classes and causing the
# actual throttle counters to fire across the full test suite.
from users.throttles import (
    LoginThrottle,
    RegisterThrottle,
    PasswordResetThrottle,
    PasswordResetEmailThrottle,
    PasswordResetConfirmThrottle,
    BurstRateThrottle,
)


@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting is properly configured"""

    def test_login_throttle_scope(self):
        """Test login throttle has correct scope"""
        throttle = LoginThrottle()
        assert throttle.scope == 'login'
        # Rate is env-configurable (LOGIN_THROTTLE_RATE); verify it is set and non-empty
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login']

    def test_register_throttle_scope(self):
        """Test register throttle has correct scope"""
        throttle = RegisterThrottle()
        assert throttle.scope == 'register'
        # Rate is env-configurable (REGISTER_THROTTLE_RATE); verify it is set and non-empty
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['register']

    def test_password_reset_throttle_exists(self):
        """Test password reset throttle is configured and IP-based."""
        throttle = PasswordResetThrottle()
        assert throttle.scope == 'password_reset'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset'] == '2/hour'
        # Must be AnonRateThrottle (IP-keyed) so anonymous callers are limited.
        assert isinstance(throttle, AnonRateThrottle), (
            "PasswordResetThrottle must extend AnonRateThrottle for IP-based throttling."
        )

    def test_password_reset_email_throttle_exists(self):
        """Per-target-email throttle prevents inbox flooding via rotating IPs."""
        throttle = PasswordResetEmailThrottle()
        assert throttle.scope == 'password_reset_email'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset_email'] == '3/hour'
        assert isinstance(throttle, AnonRateThrottle)

    def test_password_reset_email_throttle_cache_key_uses_email(self):
        """Cache key for the email throttle must be keyed on the target email, not IP."""
        from django.test import RequestFactory
        from unittest.mock import MagicMock

        factory = RequestFactory()
        request = factory.post('/api/users/password-reset/', data={'email': 'victim@example.com'},
                               content_type='application/json')
        # Simulate DRF parsed data
        request.data = {'email': 'victim@example.com'}
        request.META['REMOTE_ADDR'] = '1.2.3.4'

        throttle = PasswordResetEmailThrottle()
        key = throttle.get_cache_key(request, MagicMock())
        assert 'victim@example.com' in key, (
            "Email throttle cache key must include the target email address."
        )

    def test_password_reset_email_throttle_normalises_email_case(self):
        """Email throttle must not be bypassable by changing letter case."""
        from django.test import RequestFactory
        from unittest.mock import MagicMock

        factory = RequestFactory()
        throttle = PasswordResetEmailThrottle()

        req_lower = factory.post('/')
        req_lower.data = {'email': 'victim@example.com'}
        req_lower.META['REMOTE_ADDR'] = '1.2.3.4'

        req_upper = factory.post('/')
        req_upper.data = {'email': 'VICTIM@EXAMPLE.COM'}
        req_upper.META['REMOTE_ADDR'] = '9.9.9.9'

        key_lower = throttle.get_cache_key(req_lower, MagicMock())
        key_upper = throttle.get_cache_key(req_upper, MagicMock())
        assert key_lower == key_upper, (
            "Case variants of the same email must map to the same throttle bucket."
        )

    def test_password_reset_confirm_throttle_exists(self):
        """Test password reset confirm throttle is configured and IP-based."""
        throttle = PasswordResetConfirmThrottle()
        assert throttle.scope == 'password_reset_confirm'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset_confirm'] == '5/hour'
        assert isinstance(throttle, AnonRateThrottle), (
            "PasswordResetConfirmThrottle must extend AnonRateThrottle for IP-based throttling."
        )

    def test_password_reset_view_has_both_throttles(self):
        """The password reset request view must declare both IP and email throttles.

        We check the source file rather than introspecting the live class to
        avoid importing users.views at module level (which would cache it before
        conftest monkeypatching and break throttle-disabling across the suite).
        """
        import os, re
        views_path = os.path.join(
            os.path.dirname(__file__), '..', 'users', 'views', 'password_reset.py'
        )
        source = open(views_path).read()
        # Find the PasswordResetRequestView class definition and check that
        # both throttle classes are listed in its throttle_classes attribute.
        assert 'PasswordResetThrottle' in source, (
            "PasswordResetThrottle must appear in users/views/."
        )
        assert 'PasswordResetEmailThrottle' in source, (
            "PasswordResetEmailThrottle must appear in users/views/."
        )
        # Verify they're in the throttle_classes list, not just imported.
        throttle_classes_match = re.search(
            r'throttle_classes\s*=\s*\[([^\]]+)\]', source
        )
        assert throttle_classes_match, "throttle_classes list not found in views.py"
        throttle_list_src = throttle_classes_match.group(0)
        # Find the one belonging to PasswordResetRequestView (first occurrence
        # after the class definition).
        reset_view_src = source[source.index('class PasswordResetRequestView'):]
        first_throttle_list = re.search(r'throttle_classes\s*=\s*\[([^\]]+)\]', reset_view_src)
        assert first_throttle_list, "PasswordResetRequestView has no throttle_classes"
        tc_content = first_throttle_list.group(1)
        assert 'PasswordResetThrottle' in tc_content
        assert 'PasswordResetEmailThrottle' in tc_content

    def test_burst_throttle_scope(self):
        """Test burst throttle is properly configured"""
        throttle = BurstRateThrottle()
        assert throttle.scope == 'burst'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['burst'] == '100/minute'

    def test_submission_throttle_rate(self):
        """Test submission throttle has been tightened"""
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['submission'] == '50/hour'

    def test_anon_throttle_rate(self):
        """Test anonymous throttle has been tightened"""
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['anon'] == '20/min'

    def test_user_throttle_rate(self):
        """Test user throttle has been tightened"""
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user'] == '60/min'

    def test_throttle_classes_configured(self):
        """Test throttle classes are in REST_FRAMEWORK settings.

        Checks the *production* settings module rather than the live
        `settings.REST_FRAMEWORK` because the test settings module
        intentionally empties DEFAULT_THROTTLE_CLASSES to disable throttling
        in tests.
        """
        from config import settings as prod_settings
        throttle_classes = prod_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        assert "rest_framework.throttling.AnonRateThrottle" in throttle_classes
        assert "rest_framework.throttling.UserRateThrottle" in throttle_classes
