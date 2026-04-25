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
    def test_csp_report_only_is_bool(self):
        assert isinstance(settings.CSP_REPORT_ONLY, bool), (
            "CSP_REPORT_ONLY must be a Python bool (not the string 'True')."
        )

    def test_csp_report_uri_is_string(self):
        assert isinstance(settings.CSP_REPORT_URI, str), (
            "CSP_REPORT_URI must be a string (empty string is fine for dev)."
        )

    def test_csp_default_src_is_set(self):
        assert hasattr(settings, 'CSP_DEFAULT_SRC'), "CSP_DEFAULT_SRC must be configured."
        assert settings.CSP_DEFAULT_SRC, "CSP_DEFAULT_SRC must not be empty."

    def test_csp_frame_ancestors_blocks_framing(self):
        """Clickjacking protection — frames must be denied."""
        assert hasattr(settings, 'CSP_FRAME_ANCESTORS')
        assert "'none'" in settings.CSP_FRAME_ANCESTORS, (
            "CSP_FRAME_ANCESTORS should include \"'none'\" to prevent clickjacking."
        )
