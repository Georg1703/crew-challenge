"""Challenge reads. Views and other apps read challenge data through these functions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from apps.core import clock
from apps.crews.models import Crew, Member

from .models import Challenge, Participation, Round, Vote

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
class RoundView:
    round: Round
    proposals: list[Challenge]
    tallies: dict[UUID, Tally]
    my_vote: UUID | None


def round_view(*, round_: Round, member: Member) -> RoundView:
    """A round with its proposals (oldest first), the votes for each, and the member's vote."""
    proposals = list(
        Challenge.objects.filter(round=round_)
        .select_related("created_by")
        .order_by("created_at", "id")
    )
    tallies: dict[UUID, Tally] = defaultdict(Tally)
    my_vote = None
    votes = Vote.objects.filter(round=round_).select_related("member").order_by("created_at")
    for vote in votes:
        tally = tallies[vote.challenge_id]
        tally.count += 1
        tally.voters.append(vote.member)
        if vote.member_id == member.pk:
            my_vote = vote.challenge_id
    return RoundView(round=round_, proposals=proposals, tallies=dict(tallies), my_vote=my_vote)


def get_round(*, crew: Crew, round_id: UUID) -> Round | None:
    return Round.objects.for_crew(crew).select_related("chosen_by").filter(pk=round_id).first()


def list_closed_rounds(*, crew: Crew) -> list[Round]:
    """Rounds where a challenge was chosen, newest period first."""
    return list(
        Round.objects.for_crew(crew)
        .filter(state=Round.State.CLOSED)
        .select_related("chosen", "chosen_by")
        .order_by("-period_start")
    )


def get_challenge(*, crew: Crew, challenge_id: UUID) -> Challenge | None:
    return (
        Challenge.objects.for_crew(crew)
        .select_related("created_by", "round")
        .filter(pk=challenge_id)
        .first()
    )


def list_chosen(*, crew: Crew, phases: tuple[str, ...] = PHASES) -> list[Challenge]:
    """Chosen challenges in the given phases, by start date (newest first for finished)."""
    today = clock.crew_today(crew)
    chosen = (
        Challenge.objects.for_crew(crew)
        .filter(state=Challenge.State.CHOSEN)
        .select_related("created_by", "round")
        .order_by("start_date", "created_at")
    )
    return [c for c in chosen if phase(c, today) in phases]


def participants(*, challenge: Challenge) -> list[Participation]:
    """Who takes part (including people who left early, with `ended_on`), in join order."""
    return list(
        Participation.objects.filter(challenge=challenge)
        .select_related("member")
        .order_by("joined_on", "member__created_at")
    )
