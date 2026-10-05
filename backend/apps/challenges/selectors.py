"""Challenge reads. Views and other apps read challenge data through these functions.

A member only ever gets the challenges they can see: the ones they are invited to, or every one
in the crew for an admin (`visible`).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from django.db.models import Q, QuerySet

from apps.core import clock
from apps.crews.models import Member

from .models import Challenge, Invitee, Participation, Vote

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
    """The crew's challenges this member can see: invited to, or all of them for an admin."""
    rows = Challenge.objects.for_crew(member.crew)
    if member.is_admin:
        return rows
    return rows.filter(invitees__member=member)


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


def invitees(*, challenges: list[Challenge]) -> dict[UUID, list[Member]]:
    """Who is invited to each challenge, in the order they joined the crew."""
    result: dict[UUID, list[Member]] = defaultdict(list)
    rows = (
        Invitee.objects.filter(challenge__in=challenges)
        .select_related("member")
        .order_by("member__created_at", "member_id")
    )
    for row in rows:
        result[row.challenge_id].append(row.member)
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


def participants(*, challenge: Challenge) -> list[Participation]:
    """Who takes part (including people who left early, with `ended_on`), in join order."""
    return list(
        Participation.objects.filter(challenge=challenge)
        .select_related("member")
        .order_by("joined_on", "member__created_at")
    )


def participations_on(*, viewer: Member, day: date) -> list[Participation]:
    """Who takes part in what on `day`, in the viewer's crew, for challenges the viewer can see.

    Includes people who left that very day (`ended_on == day`); in join order, then by title.
    """
    return list(
        Participation.objects.filter(
            challenge__in=visible(member=viewer),
            challenge__state=Challenge.State.CHOSEN,
            challenge__start_date__lte=day,
            challenge__end_date__gte=day,
            joined_on__lte=day,
        )
        .filter(Q(ended_on__isnull=True) | Q(ended_on__gte=day))
        .select_related("challenge", "member")
        .order_by("member__created_at", "member_id", "challenge__title", "challenge_id")
    )
