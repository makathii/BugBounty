"""
Tests for security headers configuration.
"""
import pytest
from django.conf import settings


@pytest.mark.django_db
class TestSecurityHeaders:
    """Test that security headers are properly configured"""

    def test_x_frame_options_header(self, api_client, verified_user):
        """Test X-Frame-Options header is set to DENY"""
        api_client.force_authenticate(user=verified_user)
        response = api_client.get('/api/users/profile/')

        # Check header is present
        assert response.headers.get('X-Frame-Options') == 'DENY'

    def test_x_content_type_options_header(self, api_client, verified_user):
        """Test X-Content-Type-Options header is set to nosniff"""
        api_client.force_authenticate(user=verified_user)
        response = api_client.get('/api/users/profile/')

        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_xss_protection_header(self, api_client, verified_user):
        """Test X-XSS-Protection setting is configured"""
        # Note: Modern browsers deprecate X-XSS-Protection, but we still configure it
        assert settings.SECURE_BROWSER_XSS_FILTER is True

    def test_csp_header_present(self, api_client, verified_user):
        """Test Content-Security-Policy header is present"""
        api_client.force_authenticate(user=verified_user)
        response = api_client.get('/api/users/profile/')

        # CSP header should be present
        csp_header = response.headers.get('Content-Security-Policy')
        assert csp_header is not None

        # Check default-src is set to 'self'
        assert "default-src 'self'" in csp_header

    def test_security_settings_configured(self):
        """Test that security settings are properly configured in settings"""
        # X-Frame-Options
        assert settings.X_FRAME_OPTIONS == 'DENY'

        # Content Type Nosniff
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

        # Browser XSS Filter
        assert settings.SECURE_BROWSER_XSS_FILTER is True

        # CSP is configured
        assert hasattr(settings, 'CSP_DEFAULT_SRC')
        assert "'self'" in settings.CSP_DEFAULT_SRC

    def test_no_server_header_leakage(self, api_client, verified_user):
        """Test that server version info is not leaked in headers"""
        api_client.force_authenticate(user=verified_user)
        response = api_client.get('/api/users/profile/')

        # Server header should not reveal version
        server_header = response.headers.get('Server', '')
        assert 'django' not in server_header.lower() or server_header == ''


@pytest.mark.django_db
class TestCSRFProtection:
    """Test CSRF protection is enabled"""

    def test_csrf_cookie_settings(self):
        """Test CSRF cookie is configured securely"""
        # CSRF middleware is in place
        assert 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE
