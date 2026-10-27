"""Pick the PushSender from settings.

PUSH_BACKEND = "webpush" (wherever VAPID keys are set), "memory" in tests, "off" (the default
without keys): no push at all.
"""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import PushSender
from .memory import InMemoryPushSender
from .webpush import WebPushSender


@lru_cache(maxsize=1)
def get_push_sender() -> PushSender | None:
    backend = settings.PUSH_BACKEND
    if backend == "off":
        return None
    if backend == "memory":
        return InMemoryPushSender()
    if backend == "webpush":
        if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY):
            raise ImproperlyConfigured("Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY to push.")
        return WebPushSender(private_key=settings.VAPID_PRIVATE_KEY, subject=settings.VAPID_SUBJECT)
    raise ImproperlyConfigured(f"Unknown PUSH_BACKEND: {backend!r}")
