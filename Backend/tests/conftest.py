import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient
from users.models import Profile
from reports.models import BugReport
from programs.models import Program, Company
from unittest.mock import MagicMock


# Disable throttling for all tests by mocking the throttle classes
@pytest.fixture(autouse=True)
def disable_throttling(monkeypatch):
    """Disable REST framework throttling for all tests"""
    # Import throttle classes and replace them with no-op versions
    from rest_framework import throttling
    from users import throttles

    # Create a no-op throttle that always allows requests
    class NoOpThrottle:
        def allow_request(self, request, view):
            return True

    # Replace all throttle classes
    monkeypatch.setattr(throttles, 'LoginThrottle', NoOpThrottle)
    monkeypatch.setattr(throttles, 'RegisterThrottle', NoOpThrottle)
    monkeypatch.setattr(throttles, 'SubmissionThrottle', NoOpThrottle)
    monkeypatch.setattr(throttles, 'BurstRateThrottle', NoOpThrottle)
    monkeypatch.setattr(throttles, 'PasswordResetThrottle', NoOpThrottle)
    monkeypatch.setattr(throttles, 'PasswordResetConfirmThrottle', NoOpThrottle)


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