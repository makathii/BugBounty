"""
Tests for security.txt (RFC 9116) and CSP report-only mode (Task 8).
"""
import pytest
from django.conf import settings


# ---------------------------------------------------------------------------
# security.txt endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSecurityTxt:
    URL = '/.well-known/security.txt'

    def test_security_txt_returns_200(self, client):
        resp = client.get(self.URL)
        assert resp.status_code == 200

    def test_security_txt_content_type(self, client):
        resp = client.get(self.URL)
        assert 'text/plain' in resp['Content-Type']

    def test_security_txt_has_contact(self, client):
        resp = client.get(self.URL)
        assert 'Contact:' in resp.content.decode()

    def test_security_txt_has_expires(self, client):
        """RFC 9116 requires an Expires field."""
        resp = client.get(self.URL)
        assert 'Expires:' in resp.content.decode()

    def test_security_txt_has_policy(self, client):
        resp = client.get(self.URL)
        assert 'Policy:' in resp.content.decode()

    def test_security_txt_not_expired(self, client):
        """The Expires date in security.txt must be in the future."""
        from datetime import datetime, timezone
        resp = client.get(self.URL)
        content = resp.content.decode()
        for line in content.splitlines():
            if line.startswith('Expires:'):
                expires_str = line.split('Expires:', 1)[1].strip()
                try:
                    expires_dt = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    assert expires_dt > datetime.now(tz=timezone.utc), (
                        f"security.txt has expired ({expires_str}). Update the Expires field."
                    )
                except ValueError:
                    pytest.fail(f"Could not parse Expires date: {expires_str}")
                break


# ---------------------------------------------------------------------------
# CSP report-only configuration
# ---------------------------------------------------------------------------

class TestCSPReportOnlyConfig:
    """django-csp 4.x uses CONTENT_SECURITY_POLICY dict instead of flat CSP_* keys."""

    def test_csp_report_only_is_bool(self):
        # Report-only mode is now toggled by populating CONTENT_SECURITY_POLICY_REPORT_ONLY.
        # When CSP_REPORT_ONLY env var is True, the main policy dict becomes empty and the
        # report-only dict is populated. Either way, both settings are dicts (or empty dicts).
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', None)
        csp_ro = getattr(settings, 'CONTENT_SECURITY_POLICY_REPORT_ONLY', None)
        assert isinstance(csp, (dict, type(None)))
        assert isinstance(csp_ro, (dict, type(None)))

    def test_csp_report_uri_is_string(self):
        # report-uri now lives inside the DIRECTIVES dict, not as a top-level setting.
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', {}) or {}
        directives = csp.get('DIRECTIVES', {})
        report_uri = directives.get('report-uri', None)
        # Must be None (unset) or a list of strings
        assert report_uri is None or isinstance(report_uri, list)

    def test_csp_default_src_is_set(self):
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', {}) or {}
        directives = csp.get('DIRECTIVES', {})
        assert 'default-src' in directives, "default-src directive must be configured."
        assert directives['default-src'], "default-src must not be empty."

    def test_csp_frame_ancestors_blocks_framing(self):
        """Clickjacking protection — frames must be denied."""
        csp = getattr(settings, 'CONTENT_SECURITY_POLICY', {}) or {}
        directives = csp.get('DIRECTIVES', {})
        frame_ancestors = directives.get('frame-ancestors', [])
        assert frame_ancestors, "frame-ancestors directive must be configured."
        assert "'none'" in frame_ancestors, (
            "frame-ancestors should include \"'none'\" to prevent clickjacking."
        )
