"""What the app needs from Web Push, independent of the library: send one payload to one browser
subscription, and say when the browser is gone for good (unsubscribed, app removed)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PushError(Exception):
    """The push service failed or refused the request; the subscription may still be good."""


class SubscriptionGone(PushError):
    """The push service no longer knows this subscription: drop it."""


class PushSender(ABC):
    @abstractmethod
    def send(self, *, endpoint: str, p256dh: str, auth: str, payload: dict[str, Any]) -> None:
        """Send `payload` (JSON) to one subscription; SubscriptionGone when it is dead."""
