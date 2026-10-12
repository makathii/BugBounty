from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "List accounts that share an email address (case-insensitive). New registrations can no "
        "longer do this, but older data may; resolve these before relying on email lookups "
        "(password reset, resend verification)."
    )

    def handle(self, *args, **options):
        groups = defaultdict(list)
        for user in get_user_model().objects.exclude(email="").order_by("date_joined"):
            groups[user.email.lower()].append(user)
        shared = {email: users for email, users in groups.items() if len(users) > 1}
        if not shared:
            self.stdout.write(self.style.SUCCESS("No two accounts share an email address."))
            return
        for email, users in sorted(shared.items()):
            self.stdout.write(f"{email}:")
            for user in users:
                state = "active" if user.is_active else "inactive"
                self.stdout.write(f"  - {user.username} (id {user.pk}, {state}, joined {user.date_joined:%Y-%m-%d})")
        self.stdout.write(self.style.WARNING(f"{len(shared)} email address(es) are shared by more than one account."))
