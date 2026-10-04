"""Local development settings (make dev)."""

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, REST_FRAMEWORK, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    # Looser limits than production so `make e2e` (many logins from one IP) and manual testing
    # do not lock you out. The production limits are tested in the unit tests.
    "DEFAULT_THROTTLE_RATES": {"login": "60/min", "join": "60/min", "invite_preview": "120/min"},
}

# `make tunnel` serves the app on a temporary https://<random>.trycloudflare.com address.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, ".trycloudflare.com"]
CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, "https://*.trycloudflare.com"]
