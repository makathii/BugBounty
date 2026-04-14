import pytest
from django.contrib.auth.models import User
from programs.models import Company


@pytest.mark.django_db
def test_register_creates_user_and_assigns_default_group(api_client, user_payload):
    response = api_client.post("/api/users/register/", user_payload, format="json")

    assert response.status_code == 201
    assert User.objects.filter(username=user_payload["username"]).exists()

    created_user = User.objects.get(username=user_payload["username"])
    assert created_user.groups.filter(name="Researcher").exists()

    body = response.json()
    assert "user" in body
    assert body["user"]["username"] == user_payload["username"]
    assert "password" not in str(body).lower()


@pytest.mark.django_db
def test_register_company_assigns_program_owner_group(api_client):
    company_payload = {
        "username": "testcompany",
        "email": "company@example.com",
        "password": "SafePass123!",
        "password2": "SafePass123!",
        "first_name": "Test",
        "last_name": "Company",
        "role": "company",
    }
    response = api_client.post("/api/users/register/", company_payload, format="json")

    assert response.status_code == 201
    created_user = User.objects.get(username="testcompany")
    assert created_user.groups.filter(name="ProgramOwner").exists()
    assert not created_user.groups.filter(name="Researcher").exists()


@pytest.mark.django_db
def test_company_user_redirected_to_complete_profile(api_client, company_user):
    """Test that company user without profile is redirected to complete profile"""
    # Check user exists
    assert User.objects.filter(username="testcompany").exists()

    # Login the company user
    api_client.force_authenticate(user=company_user)

    # Try to access dashboard
    response = api_client.get("/api/programs/dashboard/")

    # Should be redirected or shown incomplete profile message
    assert response.status_code in [200, 302]

    # Check if profile_completion_required is in response
    if response.status_code == 200:
        assert "profile_completion_required" in response.data or "incomplete_profile" in response.data


@pytest.mark.django_db
def test_company_profile_completion_flow(api_client):
    """Test full company profile completion flow"""
    # Register company user
    company_payload = {
        "username": "testcompany2",
        "email": "company2@example.com",
        "password": "SafePass123!",
        "password2": "SafePass123!",
        "first_name": "Test",
        "last_name": "Company2",
        "role": "company",
    }

    response = api_client.post("/api/users/register/", company_payload, format="json")
    assert response.status_code == 201

    user = User.objects.get(username="testcompany2")
    api_client.force_authenticate(user=user)

    # Complete company profile
    profile_data = {
        "company_name": "Test Company LLC",
        "website": "https://testcompany.example.com",
        "description": "A test company for security testing",
        "contact_email": "security@testcompany.example.com",
        "industry": "Technology",
        "country": "United States"
    }

    response = api_client.post("/api/programs/companies/", profile_data, format="json")
    assert response.status_code == 201

    # Verify profile was created
    assert Company.objects.filter(user=user).exists()
    company = Company.objects.get(user=user)
    assert company.company_name == "Test Company LLC"
    assert company.website == "https://testcompany.example.com"
    assert not company.is_verified  # Company should not be verified yet
    assert not company.can_create_program  # Cannot create program until verified


@pytest.mark.django_db
def test_register_rejects_invalid_payload(api_client, user_payload):
    bad_payload = {**user_payload, "password2": "different-pass"}

    response = api_client.post("/api/users/register/", bad_payload, format="json")

    assert response.status_code == 400
    assert User.objects.filter(username=bad_payload["username"]).count() == 0


@pytest.mark.django_db
def test_login_returns_jwt_tokens_for_valid_credentials(api_client, verified_user):
    response = api_client.post(
        "/api/token/",
        {"username": verified_user.username, "password": "SafePass123!"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert "access" in body and body["access"]
    assert "refresh" in body and body["refresh"]


@pytest.mark.django_db
def test_login_rejects_invalid_credentials(api_client, verified_user):
    response = api_client.post(
        "/api/token/",
        {"username": verified_user.username, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == 401