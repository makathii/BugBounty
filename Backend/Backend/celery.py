import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Backend.settings")

app = Celery("bugbounty")
# All Celery settings live in Django settings under the CELERY_ prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
