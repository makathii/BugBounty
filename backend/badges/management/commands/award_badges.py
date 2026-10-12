from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from badges.services import evaluate
from leaderboard.models import ScoreEvent


class Command(BaseCommand):
    help = "Award any badges researchers already qualify for (backfill after adding badges)."

    def handle(self, *args, **options):
        users = get_user_model().objects.filter(
            pk__in=ScoreEvent.objects.values("researcher_id")
        )
        awarded = sum(len(evaluate(user)) for user in users)
        self.stdout.write(self.style.SUCCESS(
            f"Checked {users.count()} researcher(s); awarded {awarded} badge(s)."
        ))
