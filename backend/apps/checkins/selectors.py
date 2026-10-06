"""Check-in reads: a member's day (the ring, the cards, the crew), a challenge's month board and
one day of it (the day sheet), and the crew's feed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.db.models import OuterRef, Prefetch, QuerySet, Subquery
from django.db.models.functions import Greatest

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge, Participant
from apps.core import clock
from apps.crews.models import Member

from . import days
from .models import CheckIn, Proof

SHOWN = (Proof.Status.PROCESSING, Proof.Status.READY)  # proof the crew can see


def records(
    *, challenge_ids: list[UUID], member_ids: list[UUID]
) -> dict[tuple[UUID, UUID], days.Record]:
    """Check-ins per (challenge, member): days done, in progress, totals, days with proof."""
    result: dict[tuple[UUID, UUID], days.Record] = defaultdict(days.Record)
    rows = CheckIn.objects.filter(challenge_id__in=challenge_ids, member_id__in=member_ids)
    for row in rows:
        record = result[(row.challenge_id, row.member_id)]
        if row.status == CheckIn.Status.DONE:
            record.done.add(row.day)
        else:
            record.partial.add(row.day)
        if row.amount is not None:
            record.amounts[row.day] = row.amount
    proofs = (
        Proof.objects.filter(
            check_in__challenge_id__in=challenge_ids,
            check_in__member_id__in=member_ids,
            status__in=SHOWN,
        )
        .order_by()
        .values_list("check_in__challenge_id", "check_in__member_id", "check_in__day")
        .distinct()
    )
    for challenge_id, member_id, day in proofs:
        result[(challenge_id, member_id)].proof_days.add(day)
    return dict(result)


def todays_proofs(*, member: Member, day: date) -> dict[UUID, list[Proof]]:
    """The member's proofs on `day` per challenge, every status (uploads in flight too)."""
    result: dict[UUID, list[Proof]] = defaultdict(list)
    rows = Proof.objects.filter(check_in__member=member, check_in__day=day).select_related(
        "check_in", "original__transcode", "thumb"
    )
    for proof in rows:
        result[proof.check_in.challenge_id].append(proof)
    return dict(result)


@dataclass
class Card:
    """One challenge on a member's day."""

    challenge: Challenge
    state: str
    total: Decimal | None
    streak: int | None
    week: list[tuple[date, str]]
    progress: days.Progress | None
    settled: bool | None  # the ring segment: full, empty, or no segment today
    proofs: list[Proof]  # today's
    proof_days: list[date]  # this week's days with proof


@dataclass
class CrewDay:
    member: Member
    done: int
    needed: int


@dataclass
class Today:
    day: date
    deadline: datetime
    cards: list[Card] = field(default_factory=list)
    crew: list[CrewDay] = field(default_factory=list)


def _card(participant: Participant, record: days.Record, today: date, proofs: list[Proof]) -> Card:
    challenge = participant.challenge
    part = days.span(challenge, participant.left_on)
    monday, _ = days.week_of(today)
    week = [monday + timedelta(days=n) for n in range(7)]
    return Card(
        challenge=challenge,
        state=days.state(challenge, part, record, today, today),
        total=record.amounts.get(today),
        streak=days.streak(challenge, part, record, today),
        week=[(d, days.state(challenge, part, record, d, today)) for d in week],
        progress=days.progress(challenge, part, record, today),
        settled=days.settled_today(challenge, part, record, today),
        proofs=proofs,
        proof_days=[d for d in week if d in record.proof_days],
    )


def today(*, member: Member) -> Today:
    """The member's challenges today and the crew's progress (on challenges the member sees)."""
    day = clock.crew_today(member.crew)
    _, deadline = clock.day_bounds_utc(day, member.crew.timezone)
    everyone = challenges.participants_on(viewer=member, day=day)
    loaded = records(
        challenge_ids=list({p.challenge_id for p in everyone}),
        member_ids=list({p.member_id for p in everyone}),
    )
    mine = todays_proofs(member=member, day=day)
    result = Today(day=day, deadline=deadline)
    crew: dict[UUID, CrewDay] = {}
    for participant in everyone:
        record = loaded.get((participant.challenge_id, participant.member_id), days.Record())
        card = _card(participant, record, day, mine.get(participant.challenge_id, []))
        if participant.member_id == member.pk:
            result.cards.append(card)
        if card.settled is None:
            continue
        row = crew.setdefault(
            participant.member_id, CrewDay(member=participant.member, done=0, needed=0)
        )
        row.needed += 1
        row.done += int(card.settled)
    result.crew = list(crew.values())
    return result


def card(*, member: Member, challenge_id: UUID) -> Card | None:
    """One challenge on the member's day (after a check-in), or None if not taking part today."""
    day = clock.crew_today(member.crew)
    for participant in challenges.participants_on(viewer=member, day=day):
        if participant.challenge_id == challenge_id and participant.member_id == member.pk:
            record = records(challenge_ids=[challenge_id], member_ids=[member.pk]).get(
                (challenge_id, member.pk), days.Record()
            )
            proofs = todays_proofs(member=member, day=day).get(challenge_id, [])
            return _card(participant, record, day, proofs)
    return None


@dataclass
class BoardRow:
    member: Member
    states: list[str]
    streak: int | None
    proof_days: list[date]


@dataclass
class Board:
    days: list[date]
    rows: list[BoardRow]


Everyone = list[tuple[Participant, days.Span, days.Record]]


def _crewboard(member: Member, challenge_id: UUID) -> tuple[Challenge, date, Everyone] | None:
    """A scheduled challenge the member can see, today, and everyone in it with their record.

    The one gate for the board and the day sheet.
    """
    challenge = challenges.get_challenge(member=member, challenge_id=challenge_id)
    if challenge is None or challenge.state != Challenge.State.CHOSEN:
        return None
    people = challenges.participants(challenges=[challenge]).get(challenge.pk, [])
    loaded = records(challenge_ids=[challenge.pk], member_ids=[p.member_id for p in people])
    everyone = [
        (p, days.span(challenge, p.left_on), loaded.get((challenge.pk, p.member_id), days.Record()))
        for p in people
    ]
    return challenge, clock.crew_today(member.crew), everyone


def board(*, member: Member, challenge_id: UUID, month: date) -> Board | None:
    """Every participant's month for a challenge the member can see, one state per day."""
    found = _crewboard(member, challenge_id)
    if found is None:
        return None
    challenge, today, everyone = found
    first = month.replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)
    month_days = [first + timedelta(days=n) for n in range((next_month - first).days)]
    rows = []
    for participant, part, record in everyone:
        rows.append(
            BoardRow(
                member=participant.member,
                states=[days.state(challenge, part, record, d, today) for d in month_days],
                streak=days.streak(challenge, part, record, today),
                proof_days=[d for d in month_days if d in record.proof_days],
            )
        )
    return Board(days=month_days, rows=rows)


@dataclass
class DaySheetRow:
    member: Member
    state: str
    total: Decimal | None
    proofs: list[Proof]  # the ones the crew can see


def day_sheet(*, member: Member, challenge_id: UUID, day: date) -> list[DaySheetRow] | None:
    """Everyone's state, total and proofs on one day of a challenge the member can see."""
    found = _crewboard(member, challenge_id)
    if found is None:
        return None
    challenge, today, everyone = found
    shown: dict[UUID, list[Proof]] = defaultdict(list)
    for proof in Proof.objects.filter(
        check_in__challenge=challenge, check_in__day=day, status__in=SHOWN
    ).select_related("check_in", "original__transcode", "thumb"):
        shown[proof.check_in.member_id].append(proof)
    return [
        DaySheetRow(
            member=participant.member,
            state=days.state(challenge, part, record, day, today),
            total=record.amounts.get(day),
            proofs=shown.get(participant.member_id, []),
        )
        for participant, part, record in everyone
    ]


def feed(*, member: Member) -> QuerySet[CheckIn]:
    """The crew's check-ins on challenges the member can see, with the proofs the crew can see.

    Derived, nothing stored: `activity_at` is the later of the check-in's last change and its
    newest shown proof. Order and page it with `-activity_at` (see api FeedPagination).
    """
    newest_proof = (
        Proof.objects.filter(check_in=OuterRef("pk"), status__in=SHOWN)
        .order_by("-updated_at")
        .values("updated_at")[:1]
    )
    shown = Proof.objects.filter(status__in=SHOWN).select_related("original__transcode", "thumb")
    return (
        CheckIn.objects.filter(challenge__in=challenges.visible(member=member))
        .annotate(activity_at=Greatest("updated_at", Subquery(newest_proof)))
        .select_related("member", "challenge")
        .prefetch_related(Prefetch("proofs", queryset=shown, to_attr="shown_proofs"))
    )
