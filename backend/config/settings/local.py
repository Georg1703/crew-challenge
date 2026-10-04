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
}

# `make tunnel` serves the app on a temporary https://<random>.trycloudflare.com address.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, ".trycloudflare.com"]
CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, "https://*.trycloudflare.com"]
