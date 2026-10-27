from collections.abc import Iterable
from datetime import timedelta
from functools import partial
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.accounts.models import User
from apps.core import clock
from apps.crews import targets
from apps.crews.models import Member

from . import tasks, texts
from .models import SNIPPET, Notification, PushSubscription

KEEP = timedelta(days=90)  # news older than this is dropped (prune)
# The frontend route that shows a registered target, by its key (a push carries the URL); a
# target without one is shown at its key.
PAGES = {"entry": "crew/cards"}


def notify(
    *,
    kind: str,
    actor: Member,
    source: Any,
    target: Any,
    recipients: Iterable[UUID | None],
    facts: dict[str, Any],
) -> list[Notification]:
    """Tell `recipients` (member ids; the actor and None are dropped) that `actor` did `kind` on
    `target` (a registered target), by `source` (the row that caused it: the reaction, the
    comment). One row per person per source; a person already told stays as they were. Each new
    row goes out by push once this transaction commits."""
    page_key, page_id = targets.page_of(target)
    page_type = ContentType.objects.get_for_model(targets.get(page_key).model)  # type: ignore[union-attr]
    text = facts.get("text")
    if isinstance(text, str):
        facts = {**facts, "text": text[:SNIPPET]}
    rows: list[Notification] = []
    with transaction.atomic():
        for member_id in {m for m in recipients if m is not None and m != actor.pk}:
            row, created = Notification.objects.get_or_create(
                recipient_id=member_id,
                source_type=ContentType.objects.get_for_model(source),
                source_id=source.pk,
                defaults={
                    "crew_id": actor.crew_id,
                    "actor": actor,
                    "kind": kind,
                    "target_type": page_type,
                    "target_id": page_id,
                    "facts": {**facts, "on": targets.of(target).key},
                },
            )
            if created:
                rows.append(row)
                transaction.on_commit(partial(tasks.push.delay, str(row.pk)))
    return rows


def retract(*, source: Any) -> None:
    """The source is gone (soft deleted): the news about it goes too."""
    Notification.objects.filter(
        source_type=ContentType.objects.get_for_model(source), source_id=source.pk
    ).delete()


def mark_read(*, member: Member, target: Any | None = None) -> None:
    """The member has seen their news: all of it (the list opened), or what is shown on one
    registered target's page (the card opened)."""
    rows = Notification.objects.filter(recipient=member, read_at__isnull=True)
    if target is not None:
        page_key, page_id = targets.page_of(target)
        rows = rows.filter(
            target_type=ContentType.objects.get_for_model(targets.get(page_key).model),  # type: ignore[union-attr]
            target_id=page_id,
        )
    rows.update(read_at=clock.now())


def prune() -> int:
    """Drop news older than KEEP. Safe to run twice."""
    deleted, _ = Notification.objects.filter(created_at__lt=clock.now() - KEEP).delete()
    return deleted


def subscribe(
    *, user: User, endpoint: str, p256dh: str, auth: str, user_agent: str = ""
) -> PushSubscription:
    """This browser gets the user's news by push (keys refreshed when it asks again; a browser
    that changed hands goes to its new user)."""
    row, _ = PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={"user": user, "p256dh": p256dh, "auth": auth, "user_agent": user_agent[:200]},
    )
    return row


def unsubscribe(*, user: User, endpoint: str) -> None:
    """This browser stops getting push; unknown or another user's: nothing happens."""
    PushSubscription.objects.filter(user=user, endpoint=endpoint).delete()


def send_push(*, notification_id: UUID) -> int:
    """Push one notification to every device of its recipient, in their language. A device the
    push service no longer knows is dropped. Returns how many were sent. Nothing when push is
    off or the row is gone (read is fine: the phone may still want it)."""
    from integrations.push import SubscriptionGone, get_push_sender

    sender = get_push_sender()
    row = (
        Notification.objects.select_related("actor", "recipient__user", "crew")
        .filter(pk=notification_id)
        .first()
    )
    if sender is None or row is None:
        return 0
    page_key = targets.key_for(row.target_type)
    payload = {
        "title": row.crew.name,
        "body": texts.line(
            language=row.recipient.user.preferred_language,
            kind=row.kind,
            actor=row.actor.display_name,
            facts=row.facts,
        ),
        "url": f"/{PAGES.get(page_key, page_key)}/{row.target_id}?crew={row.crew_id}",
        "tag": f"{page_key}:{row.target_id}",
    }
    sent = 0
    for device in PushSubscription.objects.filter(user=row.recipient.user):
        try:
            sender.send(
                endpoint=device.endpoint, p256dh=device.p256dh, auth=device.auth, payload=payload
            )
        except SubscriptionGone:
            device.delete()
        else:
            sent += 1
    return sent
