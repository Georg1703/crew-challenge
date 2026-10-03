"""Production settings (the Lightsail server, behind Caddy)."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, SECRET_KEY, env

DEBUG = False

if SECRET_KEY == "insecure-local-only" or len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a long random value in production.")

# Caddy is the one proxy in front of Django: trust one X-Forwarded-For hop for client IPs.
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": env.int("TRUSTED_PROXY_COUNT", default=1)}

# Caddy terminates HTTPS and forwards the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Caddy already redirects http -> https
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Deliberate choices, silenced so `manage.py check --deploy` stays clean:
# W008: Caddy redirects http -> https before requests reach Django.
# W005, W021: HSTS for subdomains and preload depend on the final domain; decide when it exists.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]
