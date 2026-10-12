import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError

from core.checks import email_is_ready_for_production


def ids(settings_obj):
    return {w.id for w in email_is_ready_for_production(None)}


def test_console_email_is_flagged_for_production(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    settings.FRONTEND_URL = "https://app.example.org"
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.org"
    assert ids(settings) == {"bugbounty.W001"}


def test_localhost_smtp_and_placeholder_sender_are_flagged(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "localhost"
    settings.EMAIL_HOST_USER = ""
    settings.DEFAULT_FROM_EMAIL = "no-reply@bugbounty.local"
    settings.FRONTEND_URL = "http://localhost:3000"
    assert ids(settings) == {"bugbounty.W002", "bugbounty.W003", "bugbounty.W004", "bugbounty.W005"}


def test_a_proper_setup_has_no_warnings(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "smtp.sendgrid.net"
    settings.EMAIL_HOST_USER = "apikey"
    settings.DEFAULT_FROM_EMAIL = "no-reply@bugbounty.at"
    settings.FRONTEND_URL = "https://app.bugbounty.at"
    assert ids(settings) == set()


def test_send_test_email_command(settings, capsys):
    call_command("send_test_email", "me@example.org")
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["me@example.org"]


def test_send_test_email_reports_smtp_trouble(settings, monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr("users.management.commands.send_test_email.send_mail", boom)
    with pytest.raises(CommandError, match="connection refused"):
        call_command("send_test_email", "me@example.org")
