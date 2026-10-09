from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import SecurityAuditLog


class Command(BaseCommand):
    help = (
        "Delete SecurityAuditLog rows older than the retention window "
        "(AUDIT_LOG_RETENTION_DAYS, default 365). Deletes in small batches so "
        "it never holds long locks. Intended to run from cron."
    )

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None,
                            help="Override AUDIT_LOG_RETENTION_DAYS.")
        parser.add_argument("--batch-size", type=int, default=5000)
        parser.add_argument("--dry-run", action="store_true",
                            help="Report how many rows would be deleted.")

    def handle(self, *args, **opts):
        days = opts["days"] if opts["days"] is not None else settings.AUDIT_LOG_RETENTION_DAYS
        if days <= 0:
            self.stdout.write("Retention disabled (days <= 0); nothing to do.")
            return
        cutoff = timezone.now() - timedelta(days=days)
        old = SecurityAuditLog.objects.filter(timestamp__lt=cutoff)

        if opts["dry_run"]:
            self.stdout.write(f"{old.count()} row(s) older than {days} days would be deleted.")
            return

        total = 0
        while True:
            pks = list(old.order_by().values_list("pk", flat=True)[: opts["batch_size"]])
            if not pks:
                break
            deleted, _ = SecurityAuditLog.objects.filter(pk__in=pks).delete()
            total += deleted
        self.stdout.write(self.style.SUCCESS(f"Deleted {total} audit log row(s) older than {days} days."))
