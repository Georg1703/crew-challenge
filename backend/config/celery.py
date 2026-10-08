"""Celery application. Tasks live in each app's tasks.py and are discovered automatically."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("crew_challenges")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Synced into django-celery-beat's tables when beat starts. Intervals need no time zone; jobs
# that follow crew-local days loop over crews and use apps.core.clock.
app.conf.beat_schedule = {
    "expire-proofs": {"task": "apps.proofs.tasks.expire_proofs", "schedule": 15 * 60},
    "finish-videos": {"task": "apps.proofs.tasks.finish_videos", "schedule": 20},
    "open-spins": {"task": "apps.doom.tasks.open_spins", "schedule": 15 * 60},
}
