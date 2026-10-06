"""Settings for pytest. Fast, deterministic, and never talks to real AWS.

Tests need Postgres and use TEST_DATABASE_URL (defaults to a database on localhost, which is what
`make dev` exposes and CI provides). They do not need Redis: Celery runs tasks eagerly.
"""

from .base import *  # noqa: F403
from .base import env

SECRET_KEY = "test-only-secret-key"
DEBUG = False

DATABASES = {
    "default": env.db(
        "TEST_DATABASE_URL",
        default="postgres://crew:crew-local-password@localhost:5432/crew_challenges",
    )
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

OBJECT_STORAGE_BACKEND = "memory"
TRANSCODER_BACKEND = "memory"
MEDIA_BUCKET = "cc-test-media"
MEDIA_CDN_DOMAIN = ""
AWS_PROFILE = None

LOGGING = {"version": 1, "disable_existing_loggers": False}
