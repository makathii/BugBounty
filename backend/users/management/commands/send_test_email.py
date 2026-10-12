from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send one test email with the current EMAIL_* settings, to check the mail setup (docs/EMAIL.md)."

    def add_arguments(self, parser):
        parser.add_argument("to", help="Address that should receive the test email")

    def handle(self, *args, to, **options):
        host = getattr(settings, "EMAIL_HOST", "-")
        self.stdout.write(
            f"Backend {settings.EMAIL_BACKEND}, host {host}, from {settings.DEFAULT_FROM_EMAIL}"
        )
        try:
            sent = send_mail(
                "BugBounty test email",
                "If you can read this, outgoing email works.\n",
                settings.DEFAULT_FROM_EMAIL,
                [to],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f"Sending failed: {exc}")
        if not sent:
            raise CommandError("The mail backend accepted no message.")
        self.stdout.write(self.style.SUCCESS(f"Test email handed to the mail server for {to}."))
