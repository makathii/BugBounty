from django.core.management.base import BaseCommand

from leaderboard.services import recompute_all


class Command(BaseCommand):
    help = (
        "Rebuild the leaderboard ScoreEvent ledger from scratch by re-deriving "
        "it from every BugReport. Use after changing the points config or to "
        "backfill the ledger for reports created before the app was installed."
    )

    def handle(self, *args, **options):
        self.stdout.write("Recomputing leaderboard ledger...")
        count = recompute_all()
        self.stdout.write(self.style.SUCCESS(
            f"Done. {count} score event(s) rebuilt."
        ))
