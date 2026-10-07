from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID

from django.contrib.contenttypes.models import ContentType

from apps.crews.models import Member

from . import targets
from .models import Reaction


@dataclass(frozen=True)
class Group:
    """One emoji on one target and who used it, in the order they did."""

    emoji: str
    member_ids: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class Summary:
    """A target's reactions: groups in the order each emoji was first used, and the viewer's."""

    groups: list[Group] = field(default_factory=list)
    mine: str | None = None


def summaries(*, member: Member, target: str, ids: Iterable[UUID]) -> dict[UUID, Summary]:
    """Reactions of many targets of one kind in one query (a feed page). Unknown ids: empty."""
    wanted = list(ids)
    found = targets.get(target)
    if found is None or not wanted:
        return {pk: Summary() for pk in wanted}
    rows = (
        Reaction.objects.for_crew(member.crew)
        .filter(target_type=ContentType.objects.get_for_model(found.model), target_id__in=wanted)
        .order_by("created_at", "pk")
        .values_list("target_id", "member_id", "emoji")
    )
    groups: dict[UUID, dict[str, Group]] = {pk: {} for pk in wanted}
    mine: dict[UUID, str] = {}
    for target_id, member_id, emoji in rows:
        groups[target_id].setdefault(emoji, Group(emoji)).member_ids.append(member_id)
        if member_id == member.pk:
            mine[target_id] = emoji
    return {pk: Summary(groups=list(groups[pk].values()), mine=mine.get(pk)) for pk in wanted}


def summary(*, member: Member, target: str, target_id: UUID) -> Summary:
    return summaries(member=member, target=target, ids=[target_id])[target_id]
