"""
Tests for Django admin 2FA enforcement (Issue 21).

Verifies that the MFARequiredAdminSite blocks admin access for any staff user
who has not enabled TOTP-based MFA, and allows access when MFA is active.
"""
import pytest
from django.contrib.auth.models import User
from users.models import UserMFA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_staff(username="admin_user", password="S3cur3P@ss!"):
    """Create an active superuser without any MFA record."""
    return User.objects.create_superuser(
        username=username, email=f"{username}@example.com", password=password
    )


def _enable_mfa(user):
    """Give the user an active MFA record (secret doesn't matter for this gate)."""
    import pyotp
    mfa, _ = UserMFA.objects.get_or_create(
        user=user,
        defaults={"secret": pyotp.random_base32()},
    )
    mfa.is_enabled = True
    mfa.save()
    return mfa


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdminMFAGate:

    def test_admin_denies_staff_without_mfa(self, client):
        """A staff user with no MFA record must NOT reach the admin index."""
        user = _make_staff(username="no_mfa_admin")
        client.force_login(user)

        resp = client.get("/admin/", follow=True)
        # Django redirects to the login page when has_permission() is False
        # for an already-authenticated user.  The final URL should be the
        # admin login page (not the admin index), OR the response is a 302.
        final_url = resp.redirect_chain[-1][0] if resp.redirect_chain else ""
        assert "/admin/login/" in final_url or resp.status_code in (302, 403), (
            "Admin must redirect/deny users without MFA configured."
        )

    def test_admin_denies_staff_with_mfa_disabled(self, client):
        """A staff user whose MFA record exists but is_enabled=False is blocked."""
        user = _make_staff(username="disabled_mfa_admin")
        import pyotp
        UserMFA.objects.create(user=user, secret=pyotp.random_base32(), is_enabled=False)
        client.force_login(user)

        resp = client.get("/admin/", follow=True)
        final_url = resp.redirect_chain[-1][0] if resp.redirect_chain else ""
        assert "/admin/login/" in final_url or resp.status_code in (302, 403), (
            "Admin must block users with MFA disabled (is_enabled=False)."
        )

    def test_admin_allows_staff_with_mfa_enabled(self, client):
        """A staff user with is_enabled=True MFA reaches the admin index."""
        user = _make_staff(username="mfa_admin")
        _enable_mfa(user)
        client.force_login(user)

        resp = client.get("/admin/")
        # Should reach the admin index (200) or possibly redirect to admin
        # index — not the login page.
        assert resp.status_code == 200, (
            f"Admin should grant access to users with active MFA. Got {resp.status_code}."
        )

    def test_admin_site_class_is_mfa_required(self):
        """The global admin.site must be the MFA-gated subclass."""
        from django.contrib import admin
        from config.admin_site import MFARequiredAdminSite
        assert isinstance(admin.site, MFARequiredAdminSite), (
            "admin.site must be an instance of MFARequiredAdminSite."
        )
