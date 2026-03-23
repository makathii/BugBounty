import pytest
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient
from users.models import Profile
from reports.models import BugReport
from programs.models import Program


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
    )
    user.groups.add(triager_group)
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