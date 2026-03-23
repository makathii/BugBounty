import pytest
from django.contrib.auth.models import User


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