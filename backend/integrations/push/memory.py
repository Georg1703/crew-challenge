"""Push sender kept in memory, for tests: records what was sent; endpoints marked gone fail."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import PushSender, SubscriptionGone


@dataclass
class InMemoryPushSender(PushSender):
    sent: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (endpoint, payload)
    gone: set[str] = field(default_factory=set)

    def send(self, *, endpoint: str, p256dh: str, auth: str, payload: dict[str, Any]) -> None:
        if endpoint in self.gone:
            raise SubscriptionGone(endpoint)
        self.sent.append((endpoint, payload))
