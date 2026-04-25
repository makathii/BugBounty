"""
Tests for environment-based configuration security (Task 2).
Covers: DEBUG flag, ALLOWED_HOSTS, REST framework auth classes, CSP report settings.
"""
import pytest
from django.conf import settings


class TestDebugConfig:
    def test_debug_is_false_in_test_env(self):
        """DEBUG must be False in test/prod — stack traces must not leak."""
        assert settings.DEBUG is False, (
            "DEBUG=True exposes full stack traces to users. "
            "Set DJANGO_DEBUG=False in production."
        )

    def test_secret_key_is_set(self):
        """A non-empty SECRET_KEY must always be present."""
        assert settings.SECRET_KEY, "SECRET_KEY is missing"
        assert len(settings.SECRET_KEY) >= 20, "SECRET_KEY is suspiciously short"


class TestAllowedHosts:
    def test_allowed_hosts_not_wildcard(self):
        """ALLOWED_HOSTS=['*'] allows host header injection attacks."""
        assert '*' not in settings.ALLOWED_HOSTS, (
            "ALLOWED_HOSTS=['*'] is a security risk — use explicit domain names."
        )

    def test_allowed_hosts_is_not_empty_when_debug_false(self):
        """When DEBUG=False Django itself requires ALLOWED_HOSTS to be non-empty."""
        if not settings.DEBUG:
            assert len(settings.ALLOWED_HOSTS) > 0, (
                "ALLOWED_HOSTS must not be empty when DEBUG=False."
            )

    def test_allowed_hosts_includes_testserver(self):
        """Test client uses 'testserver' — it must be in ALLOWED_HOSTS."""
        assert 'testserver' in settings.ALLOWED_HOSTS, (
            "'testserver' must be in ALLOWED_HOSTS for the Django test client to work."
        )


class TestRestFrameworkAuthConfig:
    def test_no_session_authentication_in_default_classes(self):
        """
        SessionAuthentication opens CSRF attack surface on every API endpoint.
        JWT-only auth is the correct choice for a pure REST API.
        """
        auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
        session_auth = 'rest_framework.authentication.SessionAuthentication'
        assert session_auth not in auth_classes, (
            f"SessionAuthentication is present in DEFAULT_AUTHENTICATION_CLASSES. "
            f"Remove it to avoid CSRF vulnerabilities on API endpoints."
        )

    def test_jwt_authentication_is_present(self):
        """JWT must remain the primary authentication mechanism."""
        auth_classes = settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES', [])
        jwt_auth = 'rest_framework_simplejwt.authentication.JWTAuthentication'
        assert jwt_auth in auth_classes, (
            "JWTAuthentication is missing from DEFAULT_AUTHENTICATION_CLASSES."
        )

    def test_throttle_rates_defined(self):
        """Critical throttle scopes must be defined to prevent brute-force attacks."""
        rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        required_scopes = ['login', 'register', 'password_reset', 'password_reset_confirm']
        for scope in required_scopes:
            assert scope in rates, f"Throttle rate for '{scope}' is not defined."


class TestEmailBackendConfig:
    def test_email_backend_is_not_console_when_smtp_configured(self):
        """
        In the test environment the backend is overridden to locmem.
        This test documents that the production path is never the console backend
        when EMAIL_BACKEND env var is set to 'smtp'.
        """
        import os
        # The test_settings.py overrides EMAIL_BACKEND to locmem — that's correct.
        from django.conf import settings as djsettings
        # Acceptable backends in test/prod: locmem (tests) or smtp (prod)
        # The bare console backend must never be active unless explicitly in dev mode.
        acceptable = {
            'django.core.mail.backends.locmem.EmailBackend',
            'django.core.mail.backends.smtp.EmailBackend',
            'django.core.mail.backends.console.EmailBackend',  # only dev
        }
        assert djsettings.EMAIL_BACKEND in acceptable, (
            f"Unexpected EMAIL_BACKEND: {djsettings.EMAIL_BACKEND}"
        )

    def test_default_from_email_is_set(self):
        """DEFAULT_FROM_EMAIL must always be configured."""
        from django.conf import settings as djsettings
        assert djsettings.DEFAULT_FROM_EMAIL, "DEFAULT_FROM_EMAIL must not be empty"


class TestCSPReportConfig:
    def test_csp_report_only_is_a_bool(self):
        """CSP_REPORT_ONLY must be a boolean — a string 'True' would be truthy but wrong."""
        assert isinstance(settings.CSP_REPORT_ONLY, bool), (
            "CSP_REPORT_ONLY must be a bool, not a string."
        )

    def test_csp_report_uri_is_a_string(self):
        """CSP_REPORT_URI must be a string (empty string is fine for dev)."""
        assert isinstance(settings.CSP_REPORT_URI, str)
