import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient
from users.models import Profile
from reports.models import BugReport
from programs.models import Program, Company
from unittest.mock import MagicMock, patch


# Disable throttling for all tests.
#
# Patch ``allow_request`` on the real throttle classes rather than swapping the
# names in ``users.throttles``: views bind ``throttle_classes`` when
# ``users.views`` is first imported, so a name swap only works if that import
# happens inside a patched test. Depending on test order/selection the real
# classes were captured instead and the 3/min login limit leaked into the
# account-lockout tests (HTTP 429 instead of the lockout response).
# Patching the methods works regardless of when the views were imported.
@pytest.fixture(autouse=True)
def disable_throttling(monkeypatch):
    """Disable REST framework throttling for all tests"""
    from users import throttles

    for name in (
        'LoginThrottle', 'RegisterThrottle', 'SubmissionThrottle',
        'BurstRateThrottle', 'PasswordResetThrottle',
        'PasswordResetEmailThrottle', 'PasswordResetConfirmThrottle',
        'TokenRefreshThrottle', 'MfaCodeThrottle', 'MfaEnrollThrottle',
    ):
        monkeypatch.setattr(getattr(throttles, name), 'allow_request',
                            lambda self, request, view: True)


# Bypass reCAPTCHA for all tests — the real key is set in .env but tests
# don't supply captcha tokens, so verify_recaptcha must be a no-op.
@pytest.fixture(autouse=True)
def disable_recaptcha(monkeypatch):
    """Make verify_recaptcha a no-op so registration tests don't need a captcha token"""
    monkeypatch.setattr('reports.captcha.verify_recaptcha', lambda *args, **kwargs: None)
    monkeypatch.setattr('users.views.accounts.verify_recaptcha', lambda *args, **kwargs: None)


# Clear the Django cache before each test so throttle counters don't leak
# between tests. (NoOpThrottle patches the module attribute but DRF views hold
# direct class references, so the real throttle still runs against the cache.)
@pytest.fixture(autouse=True)
def clear_cache():
    """Reset Django cache before every test to prevent throttle state bleed"""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_payload():
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SafePass123!",
        "password2": "SafePass123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def researcher_group(db):
    return Group.objects.get_or_create(name="Researcher")[0]


@pytest.fixture
def triager_group(db):
    return Group.objects.get_or_create(name="Triager")[0]


@pytest.fixture
def admin_group(db):
    return Group.objects.get_or_create(name="Admin")[0]


@pytest.fixture
def verified_user(db, researcher_group):
    user = User.objects.create_user(
        username="verified_user",
        email="verified@example.com",
        password="SafePass123!",
        is_active=True,
    )
    user.groups.add(researcher_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    user.refresh_from_db()
    return user


@pytest.fixture
def second_verified_user(db, researcher_group):
    user = User.objects.create_user(
        username="another_user",
        email="another@example.com",
        password="SafePass123!",
        is_active=True,
    )
    user.groups.add(researcher_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    user.refresh_from_db()
    return user


@pytest.fixture
def triager_user(db, triager_group):
    user = User.objects.create_user(
        username="triager_user",
        email="triager@example.com",
        password="SafePass123!",
        is_active=True,
    )
    user.groups.add(triager_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    user.refresh_from_db()
    return user


@pytest.fixture
def company_user(db):
    """Create a verified company user without complete profile"""
    from django.contrib.auth.models import Group
    user = User.objects.create_user(
        username="testcompany",
        email="testcompany@example.com",
        password="SafePass123!",
        is_active=True,
    )
    # Assign ProgramOwner group
    program_owner_group, _ = Group.objects.get_or_create(name="ProgramOwner")
    user.groups.add(program_owner_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    user.refresh_from_db()
    return user


@pytest.fixture
def program(db):
    """Create a test program for bug reports"""
    company = User.objects.create_user(
        username="test_company",
        email="company@example.com",
        password="CompanyPass123!",
    )
    return Program.objects.create(
        name="Test Bug Bounty Program",
        company=company,
        description="A test program for bug bounty submissions",
        status="active",
    )


@pytest.fixture
def report_payload(program):
    return {
        "title": "Stored XSS in profile preview",
        "description": "A sufficiently long description that explains the bug, impact, reproduction steps, and expected behavior.",
        "severity": "medium",
        "program": program.id,
    }


@pytest.fixture
def own_report(db, verified_user, program):
    return BugReport.objects.create(
        title="Reporter owned issue",
        description="A long enough description to represent a realistic report owned by the main test user.",
        severity="low",
        reporter=verified_user,
        program=program,
    )


@pytest.fixture
def other_report(db, second_verified_user, program):
    return BugReport.objects.create(
        title="Someone else's issue",
        description="A long enough description to represent a realistic report owned by another user.",
        severity="high",
        reporter=second_verified_user,
        program=program,
    )


@pytest.fixture
def admin_user(db, admin_group):
    """A fully verified user in the Admin group."""
    user = User.objects.create_user(
        username="admin_user",
        email="admin@example.com",
        password="SafePass123!",
        is_active=True,
    )
    user.groups.add(admin_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    user.refresh_from_db()
    return user


@pytest.fixture
def program_owner_group(db):
    return Group.objects.get_or_create(name="ProgramOwner")[0]


@pytest.fixture
def company_user_with_profile(db, program_owner_group):
    """A ProgramOwner user with a completed, verified Company profile."""
    user = User.objects.create_user(
        username="owner_with_profile",
        email="owner@example.com",
        password="SafePass123!",
        is_active=True,
    )
    user.groups.add(program_owner_group)
    Profile.objects.filter(user=user).update(email_verified=True)
    Company.objects.create(
        user=user,
        company_name="Acme Security Inc.",
        website="https://acme.example.com",
        description="Test company for unit tests",
        contact_email="security@acme.example.com",
        is_verified=True,
    )
    user.refresh_from_db()
    return user


@pytest.fixture
def active_program(db, company_user_with_profile):
    """An active program owned by company_user_with_profile."""
    return Program.objects.create(
        name="Active Bounty Program",
        company=company_user_with_profile,
        description="An active program used in tests",
        status="active",
        scope_type="public",
    )


@pytest.fixture
def triaged_report(db, verified_user, program):
    """A report in 'triaged' status — ready for accept/reject."""
    return BugReport.objects.create(
        title="Triaged SSRF report",
        description="Server-side request forgery found in the image proxy endpoint.",
        severity="high",
        reporter=verified_user,
        program=program,
        status="triaged",
    )