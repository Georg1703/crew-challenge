"""Web Push through pywebpush (VAPID signing, payload encryption). Thin: no unit tests, checked
by hand on a phone; see the coverage omit list in pyproject.toml."""

from __future__ import annotations

import json
from typing import Any

from pywebpush import WebPushException, webpush

from .base import PushError, PushSender, SubscriptionGone

GONE = {404, 410}
TTL = 24 * 60 * 60  # the push service keeps it a day for a phone that is off


class WebPushSender(PushSender):
    def __init__(self, *, private_key: str, subject: str) -> None:
        self._private_key = private_key
        self._subject = subject

    def send(self, *, endpoint: str, p256dh: str, auth: str, payload: dict[str, Any]) -> None:
        try:
            webpush(
                subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
                data=json.dumps(payload),
                vapid_private_key=self._private_key,
                vapid_claims={"sub": self._subject},
                ttl=TTL,
                timeout=10,
            )
        except WebPushException as exc:
            if exc.status_code in GONE:
                raise SubscriptionGone(endpoint) from exc
            raise PushError(str(exc)) from exc
