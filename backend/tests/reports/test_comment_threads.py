"""Threaded comments: nesting, internal notes, edit/delete, activity log and email."""
import pytest
from django.core import mail

from reports.models import ActivityLog, Comment


def url(report, suffix=""):
    return f"/api/reports/{report.id}/comments/{suffix}"


def post(client, report, text="hello there", **extra):
    return client.post(url(report), {"text": text, **extra}, format="json")


@pytest.mark.django_db
class TestThread:
    def test_empty_thread(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.get(url(own_report))
        assert resp.status_code == 200
        assert resp.data == []

    def test_replies_nest_under_parent(self, api_client, verified_user, triager_user, own_report):
        api_client.force_authenticate(user=verified_user)
        root = post(api_client, own_report, "root").data
        api_client.force_authenticate(user=triager_user)
        reply = post(api_client, own_report, "reply", parent=root["id"])
        assert reply.status_code == 201
        assert reply.data["parent"] == root["id"]
        post(api_client, own_report, "second root")

        tree = api_client.get(url(own_report)).data
        assert [n["text"] for n in tree] == ["root", "second root"]
        assert [r["text"] for r in tree[0]["replies"]] == ["reply"]
        assert tree[1]["replies"] == []

    def test_thread_is_one_query_regardless_of_size(
        self, api_client, verified_user, own_report, django_assert_max_num_queries
    ):
        parent = None
        for i in range(8):
            parent = Comment.objects.create(
                report=own_report, author=verified_user, text=f"c{i}", parent=parent
            )
        api_client.force_authenticate(user=verified_user)
        with django_assert_max_num_queries(8):
            assert api_client.get(url(own_report)).status_code == 200

    def test_parent_must_belong_to_same_report(
        self, api_client, verified_user, own_report, second_verified_user, other_report
    ):
        foreign = Comment.objects.create(report=other_report, author=second_verified_user, text="x")
        api_client.force_authenticate(user=verified_user)
        resp = post(api_client, own_report, parent=foreign.id)
        assert resp.status_code == 400
        assert Comment.objects.filter(report=own_report).count() == 0

    def test_garbage_parent_is_rejected(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        assert post(api_client, own_report, parent="abc").status_code == 400
        assert post(api_client, own_report, parent=999999).status_code == 400

    def test_depth_is_capped(self, api_client, verified_user, own_report):
        parent = None
        for i in range(6):  # depths 0..5
            parent = Comment.objects.create(
                report=own_report, author=verified_user, text=f"c{i}", parent=parent
            )
        api_client.force_authenticate(user=verified_user)
        assert post(api_client, own_report, parent=parent.id).status_code == 400

    def test_empty_and_markup_only_text_rejected(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        assert post(api_client, own_report, "   ").status_code == 400
        assert post(api_client, own_report, "<b></b>").status_code == 400

    def test_researcher_cannot_read_or_post_on_others_report(
        self, api_client, verified_user, other_report
    ):
        api_client.force_authenticate(user=verified_user)
        assert api_client.get(url(other_report)).status_code in (403, 404)
        assert post(api_client, other_report).status_code in (403, 404)

    def test_unauthenticated(self, api_client, own_report):
        assert api_client.get(url(own_report)).status_code == 401

    def test_legacy_comment_endpoint_still_works(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        resp = api_client.post(
            f"/api/reports/{own_report.id}/comment/", {"text": "legacy"}, format="json"
        )
        assert resp.status_code == 201
        assert resp.data["parent"] is None


@pytest.mark.django_db
class TestInternalNotes:
    def test_researcher_cannot_post_internal(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        assert post(api_client, own_report, is_internal=True).status_code == 403
        assert Comment.objects.count() == 0

    def test_triager_internal_hidden_from_researcher(
        self, api_client, verified_user, triager_user, own_report
    ):
        api_client.force_authenticate(user=triager_user)
        note = post(api_client, own_report, "secret triage note", is_internal=True)
        assert note.status_code == 201 and note.data["is_internal"] is True
        post(api_client, own_report, "public")

        assert [n["text"] for n in api_client.get(url(own_report)).data] == [
            "secret triage note", "public"
        ]
        api_client.force_authenticate(user=verified_user)
        assert [n["text"] for n in api_client.get(url(own_report)).data] == ["public"]
        flat = api_client.get("/api/comments/").data
        assert "secret triage note" not in [c["text"] for c in flat]

    def test_researcher_cannot_reply_to_or_touch_internal(
        self, api_client, verified_user, triager_user, own_report
    ):
        note = Comment.objects.create(
            report=own_report, author=triager_user, text="hidden", is_internal=True
        )
        api_client.force_authenticate(user=verified_user)
        assert post(api_client, own_report, parent=note.id).status_code == 400
        assert api_client.delete(url(own_report, f"{note.id}/")).status_code == 404

    def test_reply_to_internal_stays_internal(self, api_client, triager_user, own_report):
        note = Comment.objects.create(
            report=own_report, author=triager_user, text="hidden", is_internal=True
        )
        api_client.force_authenticate(user=triager_user)
        resp = post(api_client, own_report, "follow-up", parent=note.id, is_internal=False)
        assert resp.data["is_internal"] is True

    def test_internal_note_never_emails_the_researcher(
        self, api_client, verified_user, triager_user, own_report
    ):
        verified_user.email = "researcher@example.com"
        verified_user.save()
        api_client.force_authenticate(user=triager_user)
        post(api_client, own_report, "staff only", is_internal=True)
        assert all("researcher@example.com" not in m.to for m in mail.outbox)

    def test_activity_log_hides_internal_entries_from_researcher(
        self, api_client, verified_user, triager_user, own_report
    ):
        api_client.force_authenticate(user=triager_user)
        post(api_client, own_report, "staff only", is_internal=True)
        post(api_client, own_report, "public")
        staff_logs = api_client.get(f"/api/reports/{own_report.id}/activity_logs/").data
        assert len([l for l in staff_logs if l["action"] == "comment"]) == 2
        api_client.force_authenticate(user=verified_user)
        res_logs = api_client.get(f"/api/reports/{own_report.id}/activity_logs/").data
        assert len([l for l in res_logs if l["action"] == "comment"]) == 1


@pytest.mark.django_db
class TestEditDelete:
    def test_author_can_edit_and_it_is_marked(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        c = post(api_client, own_report, "typo").data
        resp = api_client.patch(url(own_report, f"{c['id']}/"), {"text": "fixed"}, format="json")
        assert resp.status_code == 200
        assert resp.data["text"] == "fixed" and resp.data["edited_at"]

    def test_edit_is_sanitised(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        c = post(api_client, own_report, "ok").data
        resp = api_client.patch(
            url(own_report, f"{c['id']}/"), {"text": "<script>x</script>fine"}, format="json"
        )
        assert "<script>" not in resp.data["text"]

    def test_only_author_can_edit_even_staff(
        self, api_client, verified_user, triager_user, own_report
    ):
        c = Comment.objects.create(report=own_report, author=verified_user, text="mine")
        api_client.force_authenticate(user=triager_user)
        resp = api_client.patch(url(own_report, f"{c.id}/"), {"text": "hijack"}, format="json")
        assert resp.status_code == 403
        c.refresh_from_db()
        assert c.text == "mine"

    def test_delete_keeps_replies_and_blanks_text(
        self, api_client, verified_user, triager_user, own_report
    ):
        api_client.force_authenticate(user=verified_user)
        root = post(api_client, own_report, "to delete").data
        api_client.force_authenticate(user=triager_user)
        post(api_client, own_report, "child", parent=root["id"])
        api_client.force_authenticate(user=verified_user)
        assert api_client.delete(url(own_report, f"{root['id']}/")).status_code == 204

        tree = api_client.get(url(own_report)).data
        assert tree[0]["is_deleted"] is True and tree[0]["text"] == ""
        assert tree[0]["can_edit"] is False and tree[0]["can_delete"] is False
        assert [r["text"] for r in tree[0]["replies"]] == ["child"]
        assert Comment.objects.filter(pk=root["id"]).exists()  # soft delete

    def test_staff_can_delete_any_public_comment_but_researcher_cannot_delete_others(
        self, api_client, verified_user, triager_user, own_report
    ):
        theirs = Comment.objects.create(report=own_report, author=triager_user, text="staff")
        api_client.force_authenticate(user=verified_user)
        assert api_client.delete(url(own_report, f"{theirs.id}/")).status_code == 403
        mine = Comment.objects.create(report=own_report, author=verified_user, text="mine")
        api_client.force_authenticate(user=triager_user)
        assert api_client.delete(url(own_report, f"{mine.id}/")).status_code == 204

    def test_cannot_edit_or_delete_twice(self, api_client, verified_user, own_report):
        c = Comment.objects.create(report=own_report, author=verified_user, text="x")
        api_client.force_authenticate(user=verified_user)
        assert api_client.delete(url(own_report, f"{c.id}/")).status_code == 204
        assert api_client.delete(url(own_report, f"{c.id}/")).status_code == 404
        assert api_client.patch(
            url(own_report, f"{c.id}/"), {"text": "y"}, format="json"
        ).status_code == 404

    def test_comment_from_another_report_is_not_addressable(
        self, api_client, verified_user, own_report, second_verified_user, other_report
    ):
        foreign = Comment.objects.create(report=other_report, author=second_verified_user, text="x")
        api_client.force_authenticate(user=verified_user)
        assert api_client.delete(url(own_report, f"{foreign.id}/")).status_code == 404

    def test_permission_flags(self, api_client, verified_user, triager_user, own_report):
        Comment.objects.create(report=own_report, author=verified_user, text="mine")
        Comment.objects.create(report=own_report, author=triager_user, text="theirs")
        api_client.force_authenticate(user=verified_user)
        mine, theirs = api_client.get(url(own_report)).data
        assert (mine["can_edit"], mine["can_delete"]) == (True, True)
        assert (theirs["can_edit"], theirs["can_delete"]) == (False, False)
        api_client.force_authenticate(user=triager_user)
        mine, theirs = api_client.get(url(own_report)).data
        assert (mine["can_edit"], mine["can_delete"]) == (False, True)
        assert (theirs["can_edit"], theirs["can_delete"]) == (True, True)


@pytest.mark.django_db
class TestActivityAndNotifications:
    def test_comment_is_logged(self, api_client, verified_user, own_report):
        api_client.force_authenticate(user=verified_user)
        c = post(api_client, own_report).data
        log = ActivityLog.objects.get(report=own_report, action="comment")
        assert log.details["comment_id"] == c["id"]
        assert log.details["is_internal"] is False

    def test_researcher_comment_emails_assignee_not_self(
        self, api_client, verified_user, triager_user, own_report
    ):
        verified_user.email = "r@example.com"
        verified_user.save()
        triager_user.email = "t@example.com"
        triager_user.save()
        own_report.assigned_to = triager_user
        own_report.save()
        api_client.force_authenticate(user=verified_user)
        post(api_client, own_report, "please look")
        recipients = [addr for m in mail.outbox for addr in m.to]
        assert recipients == ["t@example.com"]

    def test_staff_reply_emails_reporter_and_parent_author_once(
        self, api_client, verified_user, triager_user, own_report
    ):
        verified_user.email = "r@example.com"
        verified_user.save()
        root = Comment.objects.create(report=own_report, author=verified_user, text="root")
        api_client.force_authenticate(user=triager_user)
        post(api_client, own_report, "answer", parent=root.id)
        assert [m.to for m in mail.outbox] == [["r@example.com"]]
        assert "answer" in mail.outbox[0].body
        assert f"/reports/{own_report.id}" in mail.outbox[0].body

    def test_mail_failure_does_not_break_posting(
        self, api_client, verified_user, triager_user, own_report, monkeypatch
    ):
        def boom(*a, **k):
            raise RuntimeError("smtp down")

        monkeypatch.setattr("reports.tasks.send_mail", boom)
        verified_user.email = "r@example.com"
        verified_user.save()
        api_client.force_authenticate(user=triager_user)
        assert post(api_client, own_report).status_code == 201
