"""
Which programs a report may be filed under.

Found by the full-program browser test: the submit page lost the chosen program, so reports were
saved with NO program; and the API never checked that a program was given, open for submissions,
or accessible to the reporter.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from programs.models import Program
from reports.models import BugReport


@pytest.fixture
def make_program(program):
    def make(**fields):
        defaults = dict(company=program.company, name=f"P{Program.objects.count()}", description="x",
                        scope_type="public", status="active")
        return Program.objects.create(**{**defaults, **fields})
    return make


@pytest.fixture
def submit(api_client, report_payload, verified_user):
    def go(program_id="__keep__", user=verified_user, **changes):
        payload = {**report_payload, **changes}
        if program_id != "__keep__":
            payload["program"] = program_id
        if payload.get("program") is None:
            payload.pop("program", None)
        api_client.force_authenticate(user=user)
        return api_client.post("/api/reports/", payload, format="json")
    return go


@pytest.mark.django_db
class TestCreate:
    def test_a_report_for_an_open_public_program_is_created_under_it(self, submit, program):
        resp = submit()
        assert resp.status_code == 201, resp.data
        assert BugReport.objects.get(pk=resp.data["id"]).program_id == program.id

    def test_a_program_is_required(self, submit):
        resp = submit(program_id=None)
        assert resp.status_code == 400 and "program" in resp.data
        assert not BugReport.objects.exists()

    def test_an_unknown_program_is_refused(self, submit):
        assert submit(program_id=999999).status_code == 400

    @pytest.mark.parametrize("status", ["draft", "paused", "closed"])
    def test_programs_that_are_not_active_do_not_take_reports(self, submit, make_program, status):
        resp = submit(program_id=make_program(status=status).id)
        assert resp.status_code == 400 and "program" in resp.data
        assert not BugReport.objects.exists()

    def test_programs_past_their_end_date_do_not_take_reports(self, submit, make_program):
        ended = make_program(end_date=timezone.now().date() - timedelta(days=1))
        assert submit(program_id=ended.id).status_code == 400

    def test_a_program_ending_today_still_takes_reports(self, submit, make_program):
        today = make_program(end_date=timezone.now().date())
        assert submit(program_id=today.id).status_code == 201

    def test_private_programs_need_access(self, submit, make_program):
        private = make_program(scope_type="private")
        resp = submit(program_id=private.id)
        assert resp.status_code == 400 and "program" in resp.data
        assert not BugReport.objects.exists()

    def test_vdp_programs_are_open_to_all(self, submit, make_program):
        assert submit(program_id=make_program(scope_type="vdp").id).status_code == 201


@pytest.mark.django_db
class TestEditing:
    def test_a_report_cannot_be_moved_to_another_program(self, api_client, own_report, make_program, verified_user):
        other = make_program()
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(f"/api/reports/{own_report.id}/", {"program": other.id}, format="json")
        assert resp.status_code == 400 and "program" in resp.data
        own_report.refresh_from_db()
        assert own_report.program_id != other.id

    def test_other_fields_can_still_be_edited_without_resending_the_program(
        self, api_client, own_report, verified_user
    ):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(f"/api/reports/{own_report.id}/", {"title": "A better, longer title"}, format="json")
        assert resp.status_code == 200

    def test_resending_the_same_program_is_fine(self, api_client, own_report, verified_user):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.patch(
            f"/api/reports/{own_report.id}/", {"program": own_report.program_id}, format="json"
        )
        assert resp.status_code == 200
