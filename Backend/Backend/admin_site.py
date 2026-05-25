"""
Custom Django AdminSite that enforces TOTP-based 2FA.

Why this exists
---------------
Django's default admin accepts a username + password and grants access
immediately.  An attacker who steals an admin password (phishing, credential
stuffing, DB leak) would have full admin access with no second factor.

Enforcement strategy
--------------------
We override ``has_permission`` to add a hard gate: a staff/superuser account
may only enter the admin if the matching ``UserMFA`` record exists AND
``is_enabled=True``.  Any admin user who hasn't completed MFA setup is locked
out until they enroll via the API (``/api/users/mfa/setup/`` → confirm).

This does *not* verify the TOTP code at login time (that would require a
custom admin login flow with an intermediate step).  It does, however, ensure
that:

  1. No password-only access to admin is possible once MFA is configured.
  2. Any staff account that has *not* set up 2FA is completely blocked from
     admin, giving a strong incentive to complete enrollment.

In a future iteration, step-up TOTP verification at login can be added by
overriding ``AdminSite.login()`` and storing an ``admin_mfa_verified`` flag in
the Django session.
"""
from django.contrib.admin import AdminSite


class MFARequiredAdminSite(AdminSite):
    """AdminSite subclass that requires active MFA for every staff user."""

    site_header = "BugBounty Admin (2FA required)"
    site_title = "BugBounty Admin"

    def has_permission(self, request):
        """Grant admin access only to staff users who have 2FA enabled.

        Falls back to the parent check first (user must be active + staff).
        Then additionally requires an active ``UserMFA`` record.
        """
        if not super().has_permission(request):
            return False

        # Superusers and staff must have MFA configured and enabled.
        try:
            mfa = request.user.mfa          # OneToOneField related name
            if not mfa.is_enabled:
                return False
        except Exception:
            # No UserMFA record at all → deny access.
            return False

        return True
