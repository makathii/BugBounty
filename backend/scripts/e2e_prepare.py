"""
Prepare the database for the browser end-to-end tests and print what they need as JSON.

    E2E_RESET=1 python manage.py shell < scripts/e2e_prepare.py

It RESETS demo state (all comments, store purchases, wallet transactions and equipped items),
so it refuses to run unless E2E_RESET=1 is set. Run it only against a throwaway e2e database.
The demo data must already exist (``scripts/seed_demo.py``).

Output: the last line of stdout is a JSON object with an access/refresh token pair per demo
user and the ids of a few reports, which frontend/e2e/global-setup.js reads.
"""
import json
import os

if os.environ.get("E2E_RESET") != "1":
    raise SystemExit("Refusing to reset data: set E2E_RESET=1 (and only on a throwaway database).")

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from reports.models import ActivityLog, BugReport, Comment
from store.models import EquippedItem, UserItem
from store import services as store_services
from wallet.models import WalletTransaction

# Start from a known state, regardless of earlier runs.
Comment.objects.all().delete()
ActivityLog.objects.filter(action="comment").delete()
EquippedItem.objects.all().delete()
for owned in UserItem.objects.all():
    store_services.refund(owned)
WalletTransaction.objects.all().delete()

# An accepted-but-not-yet-accepted report for the triage flow: re-open one that is triaged.
triaged = BugReport.objects.filter(status="triaged", reporter__username="parsa").order_by("id").first()
if triaged is None:
    # an earlier run accepted it; put it back to triaged (this also revokes its points)
    triaged = BugReport.objects.filter(reporter__username="parsa", title__startswith="API key leaked").first()
    triaged.status = "triaged"
    triaged.bonus_points = 0
    triaged.save()

tokens = {}
for username in ("parsa", "nova", "triager", "admin"):
    refresh = RefreshToken.for_user(User.objects.get(username=username))
    tokens[username] = {"access": str(refresh.access_token), "refresh": str(refresh)}

print(json.dumps({
    "tokens": tokens,
    "reports": {
        "own": BugReport.objects.filter(reporter__username="parsa").order_by("id").first().id,
        "triaged": triaged.id,
    },
}))
