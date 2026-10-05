"""Challenge reads. Views and other apps read challenge data through these functions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from apps.core import clock
from apps.crews.models import Crew, Member

from .models import Challenge, Participation, Vote

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


def pool(*, crew: Crew) -> Pool:
    proposals = list(
        Challenge.objects.for_crew(crew)
        .filter(state=Challenge.State.PROPOSED)
        .select_related("created_by")
        .order_by("-created_at", "-id")
    )
    return Pool(
        proposals=proposals,
        tallies=tallies(challenges=proposals),
        size=len(proposals),
        limit=crew.max_proposals,
    )


def get_challenge(*, crew: Crew, challenge_id: UUID) -> Challenge | None:
    return (
        Challenge.objects.for_crew(crew)
        .select_related("created_by", "chosen_by")
        .filter(pk=challenge_id)
        .first()
    )


def list_chosen(*, crew: Crew, phases: tuple[str, ...] = PHASES) -> list[Challenge]:
    """Scheduled challenges in the given phases, by start date, then title."""
    today = clock.crew_today(crew)
    chosen = (
        Challenge.objects.for_crew(crew)
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
