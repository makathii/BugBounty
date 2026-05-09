"""
Tests for rate limiting configuration.
"""
import pytest
from django.conf import settings
from rest_framework.throttling import UserRateThrottle

from users.throttles import (
    LoginThrottle,
    RegisterThrottle,
    PasswordResetThrottle,
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
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] == '3/min'

    def test_register_throttle_scope(self):
        """Test register throttle has correct scope"""
        throttle = RegisterThrottle()
        assert throttle.scope == 'register'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['register'] == '2/min'

    def test_password_reset_throttle_exists(self):
        """Test password reset throttle is configured"""
        throttle = PasswordResetThrottle()
        assert throttle.scope == 'password_reset'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset'] == '2/hour'

    def test_password_reset_confirm_throttle_exists(self):
        """Test password reset confirm throttle is configured"""
        throttle = PasswordResetConfirmThrottle()
        assert throttle.scope == 'password_reset_confirm'
        assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset_confirm'] == '5/hour'

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
        from Backend import settings as prod_settings
        throttle_classes = prod_settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        assert "rest_framework.throttling.AnonRateThrottle" in throttle_classes
        assert "rest_framework.throttling.UserRateThrottle" in throttle_classes
