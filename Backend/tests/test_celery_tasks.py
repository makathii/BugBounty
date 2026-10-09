"""Celery integration: dispatch semantics and task bodies."""
from unittest import mock

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail

from audit.models import SecurityAuditLog
from core import tasks as core_tasks
from programs.models import Program
from reports.models import BugReport
from reports.tasks import refresh_program_stats, send_report_submission_notification


def test_registered_and_autodiscovered():
    from Backend.celery import app
    app.loader.import_default_modules()
    for name in ("reports.tasks.refresh_program_stats",
                 "reports.tasks.send_report_submission_notification",
                 "audit.tasks.purge_audit_logs"):
        assert name in app.tasks


def test_test_environment_runs_tasks_inline(settings):
    # No broker configured in tests -> eager, so no worker/Redis is needed.
    assert settings.CELERY_TASK_ALWAYS_EAGER is True


@pytest.mark.django_db
class TestEnqueueAfterCommit:
    def test_eager_runs_immediately(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        task = mock.Mock()
        core_tasks.enqueue_after_commit(task, 1, a=2)
        task.apply.assert_called_once_with(args=(1,), kwargs={"a": 2}, throw=True)

    def test_broker_mode_publishes_only_after_commit(self, settings, django_capture_on_commit_callbacks):
        settings.CELERY_TASK_ALWAYS_EAGER = False
        task = mock.Mock()
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            core_tasks.enqueue_after_commit(task, 7)
            task.apply_async.assert_not_called()      # nothing before commit
        assert len(callbacks) == 1
        callbacks[0]()
        task.apply_async.assert_called_once_with(args=(7,), kwargs={})

    def test_broker_outage_does_not_raise(self, settings, django_capture_on_commit_callbacks):
        settings.CELERY_TASK_ALWAYS_EAGER = False
        task = mock.Mock(name="t")
        task.apply_async.side_effect = ConnectionError("redis down")
        with django_capture_on_commit_callbacks(execute=True):
            core_tasks.enqueue_after_commit(task, 1)   # must not raise


@pytest.mark.django_db
class TestTaskBodies:
    def test_refresh_program_stats(self, verified_user, program):
        BugReport.objects.create(title="A report title", description="d", reporter=verified_user,
                                 program=program, bounty_amount=50)
        Program.objects.filter(pk=program.pk).update(total_reports=0, total_bounties=0)
        refresh_program_stats.apply(args=(program.pk,), throw=True)
        program.refresh_from_db()
        assert program.total_reports == 1 and float(program.total_bounties) == 50

    def test_refresh_is_idempotent(self, program):
        refresh_program_stats.apply(args=(program.pk,), throw=True)
        refresh_program_stats.apply(args=(program.pk,), throw=True)

    def test_submission_email_goes_to_admins_only(self, verified_user, program):
        admin = User.objects.create_user("adm", "adm@example.com", "x")
        admin.groups.add(Group.objects.get_or_create(name="Admin")[0])
        blank = User.objects.create_user("adm2", "", "x")
        blank.groups.add(Group.objects.get(name="Admin"))
        report = BugReport.objects.create(title="Stored XSS everywhere", description="d" * 10,
                                          reporter=verified_user, program=program)
        mail.outbox.clear()
        send_report_submission_notification.apply(args=(report.pk,), throw=True)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["adm@example.com"]
        assert "Stored XSS everywhere" in mail.outbox[0].subject

    def test_submission_email_skips_deleted_report(self):
        send_report_submission_notification.apply(args=(999999,), throw=True)
        assert mail.outbox == []

    def test_purge_task_runs_command(self, settings):
        from audit.tasks import purge_audit_logs
        settings.AUDIT_LOG_RETENTION_DAYS = 30
        old = SecurityAuditLog.objects.create(action=SecurityAuditLog.ACTION_ADMIN_ACCESS)
        from datetime import timedelta
        from django.utils import timezone
        SecurityAuditLog.objects.filter(pk=old.pk).update(timestamp=timezone.now() - timedelta(days=40))
        purge_audit_logs.apply(throw=True)
        assert SecurityAuditLog.objects.count() == 0


def test_beat_schedule_points_at_real_task():
    from django.conf import settings
    from Backend.celery import app
    app.loader.import_default_modules()
    for entry in settings.CELERY_BEAT_SCHEDULE.values():
        assert entry["task"] in app.tasks
