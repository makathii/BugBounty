"""Check badges whenever a researcher's points ledger changes."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from leaderboard.models import ScoreEvent

from .services import evaluate


@receiver(post_save, sender=ScoreEvent, dispatch_uid="badges_on_score_event")
def award_badges_on_score_change(sender, instance, **kwargs):
    evaluate(instance.researcher)
