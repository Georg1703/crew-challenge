"""Challenge reads. Views and other apps read challenge data through these functions.

A member only ever gets the challenges they can see: the ones they take part in (and have not
left), or every one in the crew for an admin (`visible`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.core import clock
from apps.crews.models import Member

from .models import Challenge, Participant, Punishment, Vote

PHASES = ("upcoming", "active", "finished")


def phase(challenge: Challenge, today: date) -> str | None:
    """`upcoming`, `active` or `finished` for a chosen challenge; None for proposals."""
    if challenge.state != Challenge.State.CHOSEN or not challenge.start_date:
        return None
    assert challenge.end_date is not None
    if today < challenge.start_date:
        return "upcoming"
    if today > challenge.end_date:
        return "finished"
    return "active"


@dataclass
class Tally:
    """Votes for one proposal: how many and who."""

    count: int = 0
    voters: list[Member] = field(default_factory=list)


@dataclass
class Pool:
    """The crew's proposals (newest first) with their votes, and how full the pool is."""

    proposals: list[Challenge]
    tallies: dict[UUID, Tally]
    size: int
    limit: int


def tallies(*, challenges: list[Challenge]) -> dict[UUID, Tally]:
    """Votes for each of the given challenges, voters in the order they voted."""
    result: dict[UUID, Tally] = defaultdict(Tally)
    votes = (
        Vote.objects.filter(challenge__in=challenges)
        .select_related("member")
        .order_by("created_at", "id")
    )
    for vote in votes:
        tally = result[vote.challenge_id]
        tally.count += 1
        tally.voters.append(vote.member)
    return dict(result)


def visible(*, member: Member) -> QuerySet[Challenge]:
    """The crew's challenges this member can see: taking part (not left), or all for an admin."""
    rows = Challenge.objects.for_crew(member.crew)
    if member.is_admin:
        return rows
    return rows.filter(participants__member=member, participants__left_on__isnull=True)


def pool(*, member: Member) -> Pool:
    """The proposals the member can see; `size` counts the whole crew's pool (the limit does)."""
    proposals = list(
        visible(member=member)
        .filter(state=Challenge.State.PROPOSED)
        .select_related("created_by")
        .order_by("-created_at", "-id")
    )
    size = Challenge.objects.for_crew(member.crew).filter(state=Challenge.State.PROPOSED).count()
    return Pool(
        proposals=proposals,
        tallies=tallies(challenges=proposals),
        size=size,
        limit=member.crew.max_proposals,
    )


def participants(*, challenges: list[Challenge]) -> dict[UUID, list[Participant]]:
    """Who takes part in each challenge (people who left too), in the order they joined the crew."""
    result: dict[UUID, list[Participant]] = defaultdict(list)
    rows = (
        Participant.objects.filter(challenge__in=challenges)
        .select_related("member")
        .order_by("member__created_at", "member_id")
    )
    for row in rows:
        result[row.challenge_id].append(row)
    return dict(result)


def punishments(*, challenges: list[Challenge]) -> dict[UUID, list[Punishment]]:
    """Each challenge's punishments, by position, in one query."""
    result: dict[UUID, list[Punishment]] = defaultdict(list)
    for row in Punishment.objects.filter(challenge__in=challenges).order_by("position"):
        result[row.challenge_id].append(row)
    return dict(result)


def get_challenge(*, member: Member, challenge_id: UUID) -> Challenge | None:
    return (
        visible(member=member)
        .select_related("created_by", "chosen_by")
        .filter(pk=challenge_id)
        .first()
    )


def list_chosen(*, member: Member, phases: tuple[str, ...] = PHASES) -> list[Challenge]:
    """Scheduled challenges the member can see, in the given phases, by start date, then title."""
    today = clock.crew_today(member.crew)
    chosen = (
        visible(member=member)
        .filter(state=Challenge.State.CHOSEN)
        .select_related("created_by", "chosen_by")
        .order_by("start_date", "title", "created_at")
    )
    return [c for c in chosen if phase(c, today) in phases]


def participants_on(*, viewer: Member, day: date) -> list[Participant]:
    """Who takes part in what on `day`, in the viewer's crew, for challenges the viewer can see.

    Includes people who left that very day (`left_on == day`); in join order, then by title.
    """
    return list(
        Participant.objects.filter(
            challenge__in=visible(member=viewer),
            challenge__state=Challenge.State.CHOSEN,
            challenge__start_date__lte=day,
            challenge__end_date__gte=day,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=day))
        .select_related("challenge", "member")
        .order_by("member__created_at", "member_id", "challenge__title", "challenge_id")
    )
