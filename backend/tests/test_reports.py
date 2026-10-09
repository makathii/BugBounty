import pytest


@pytest.mark.django_db
def test_verified_user_can_submit_report(api_client, verified_user, report_payload, monkeypatch):
    api_client.force_authenticate(user=verified_user)
    monkeypatch.setattr("reports.views.send_mail", lambda *args, **kwargs: 1)

    response = api_client.post("/api/reports/", report_payload, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == report_payload["title"]
    assert body["severity"] == report_payload["severity"]
    assert body["status"] == "open"


@pytest.mark.django_db
def test_unverified_user_cannot_submit_report(api_client, researcher_group, report_payload):
    from django.contrib.auth.models import User

    user = User.objects.create_user(
        username="needs_verification",
        email="nv@example.com",
        password="SafePass123!",
    )
    user.groups.add(researcher_group)

    api_client.force_authenticate(user=user)
    response = api_client.post("/api/reports/", report_payload, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_regular_user_list_is_scoped_to_their_own_reports(api_client, verified_user, own_report, other_report):
    api_client.force_authenticate(user=verified_user)

    response = api_client.get("/api/reports/")

    assert response.status_code == 200
    data = response.json()
    returned_ids = {item["id"] for item in data}
    assert own_report.id in returned_ids
    assert other_report.id not in returned_ids


@pytest.mark.django_db
def test_triager_can_view_reports_beyond_their_own(api_client, triager_user, own_report, other_report):
    api_client.force_authenticate(user=triager_user)

    response = api_client.get("/api/reports/")

    assert response.status_code == 200
    data = response.json()
    returned_ids = {item["id"] for item in data}
    assert own_report.id in returned_ids
    assert other_report.id in returned_ids


@pytest.mark.django_db
def test_regular_user_cannot_change_report_status(api_client, verified_user, own_report):
    api_client.force_authenticate(user=verified_user)

    response = api_client.patch(
        f"/api/reports/{own_report.id}/change_status/",
        {"status": "triaged"},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_triager_can_change_report_status(api_client, triager_user, own_report):
    api_client.force_authenticate(user=triager_user)

    response = api_client.patch(
        f"/api/reports/{own_report.id}/change_status/",
        {"status": "triaged"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "triaged"