import operator
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import reduce
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.crews import targets
from apps.crews.models import Member

from .models import Comment

WRITERS = 3  # the last writers a target's summary names


@dataclass(frozen=True)
class Summary:
    """A target's comments, for its card: how many, and who wrote last (latest first)."""

    count: int = 0
    member_ids: list[UUID] = field(default_factory=list)


def visible(member: Member) -> QuerySet[Comment]:
    """Comments I can see: on targets that take comments and that I can see now (the `comment`
    target)."""
    on = [
        Q(
            target_type=ContentType.objects.get_for_model(target.model),
            target_id__in=target.visible(member).values("pk"),
        )
        for target in targets.all_targets()
        if target.comments
    ]
    nothing = Q(pk__in=[])
    return Comment.objects.for_crew(member.crew).filter(reduce(operator.or_, on, nothing))


def thread(*, member: Member, target: str, target_id: UUID) -> list[Comment]:
    """A target's comments, oldest first, so a reply's parent comes before it (the client puts
    them in a tree). TargetNotFound if I may not see it or it takes no comments."""
    found = targets.find(target, member, target_id, comments=True)
    return list(
        Comment.objects.filter(
            target_type=ContentType.objects.get_for_model(found), target_id=found.pk
        ).order_by("created_at", "pk")
    )


def summaries(*, member: Member, target: str, ids: Iterable[UUID]) -> dict[UUID, Summary]:
    """Comment counts and last writers of many targets of one kind in one query (a journal
    page). Unknown ids: empty."""
    wanted = list(ids)
    found = targets.get(target)
    if found is None or not wanted:
        return {pk: Summary() for pk in wanted}
    # ponytail: reads every comment row of the page's targets; count in SQL if threads get long.
    rows = (
        Comment.objects.for_crew(member.crew)
        .filter(target_type=ContentType.objects.get_for_model(found.model), target_id__in=wanted)
        .order_by("-created_at", "-pk")
        .values_list("target_id", "member_id")
    )
    counts: Counter[UUID] = Counter()
    writers: dict[UUID, list[UUID]] = {pk: [] for pk in wanted}
    for target_id, member_id in rows:
        counts[target_id] += 1
        last = writers[target_id]
        if member_id not in last and len(last) < WRITERS:
            last.append(member_id)
    return {pk: Summary(count=counts[pk], member_ids=writers[pk]) for pk in wanted}


def others_commented(*, member: Member, on: QuerySet[Any]) -> bool:
    """Whether someone other than `member` has a comment on any of `on` (deleting them would
    delete words that are not theirs)."""
    return (
        Comment.objects.filter(
            target_type=ContentType.objects.get_for_model(on.model),
            target_id__in=on.values("pk"),
        )
        .exclude(member=member)
        .exists()
    )
