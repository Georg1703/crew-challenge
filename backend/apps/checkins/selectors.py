"""Check-in reads: a member's day (the ring, the cards, the crew), a challenge's month board and
one day of it (the day sheet), and the crew's feed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.db.models import Count, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.db.models.functions import Greatest

from apps.challenges import selectors as challenges
from apps.challenges.models import Challenge, Participant
from apps.challenges.periods import dates, month_of, scheduled_dates, week_of
from apps.challenges.windows import windows
from apps.core import clock
from apps.crews import selectors as crews
from apps.crews.models import Member
from apps.proofs.models import Proof
from apps.proofs.selectors import VISIBLE

from . import days
from .models import CheckIn, CheckInEntry


def records(
    *, challenge_ids: list[UUID], member_ids: list[UUID], proof_days: bool = True
) -> dict[tuple[UUID, UUID], days.Record]:
    """Check-ins per (challenge, member): days done, in progress, totals, days with posted proof
    (left out with `proof_days=False`, one query less). A pending check-in (only draft files) is
    no check-in yet."""
    result: dict[tuple[UUID, UUID], days.Record] = defaultdict(days.Record)
    rows = CheckIn.objects.filter(challenge_id__in=challenge_ids, member_id__in=member_ids).exclude(
        status=CheckIn.Status.PENDING
    )
    for row in rows:
        record = result[(row.challenge_id, row.member_id)]
        if row.status == CheckIn.Status.DONE:
            record.done.add(row.day)
        else:
            record.partial.add(row.day)
        if row.amount is not None:
            record.amounts[row.day] = row.amount
    if not proof_days:
        return dict(result)
    proofs = (
        Proof.objects.filter(
            VISIBLE,
            check_in__challenge_id__in=challenge_ids,
            check_in__member_id__in=member_ids,
        )
        .order_by()
        .values_list("check_in__challenge_id", "check_in__member_id", "check_in__day")
        .distinct()
    )
    for challenge_id, member_id, day in proofs:
        result[(challenge_id, member_id)].proof_days.add(day)
    return dict(result)


def todays_proofs(*, member: Member, day: date) -> dict[UUID, list[Proof]]:
    """The member's proofs on `day` per challenge, posted and draft, every status (uploads in
    flight too)."""
    result: dict[UUID, list[Proof]] = defaultdict(list)
    challenge_of = dict(
        CheckIn.objects.filter(member=member, day=day).values_list("pk", "challenge")
    )
    rows = Proof.objects.filter(check_in__in=list(challenge_of)).select_related(
        "original__transcode", "thumb"
    )
    for proof in rows:
        result[challenge_of[proof.subject_id]].append(proof)
    return dict(result)


@dataclass
class Card:
    """One challenge on a member's day."""

    challenge: Challenge
    state: str
    total: Decimal | None
    streak: int | None
    week: list[tuple[date, str]]
    current: days.Judged | None  # the week, month or period today is in
    settled: bool | None  # the ring segment: full, empty, or no segment today
    proofs: list[Proof]  # today's
    proof_days: list[date]  # this week's days with proof


@dataclass
class CrewDay:
    member: Member
    done: int
    needed: int
    challenges: list[tuple[UUID, str]] = field(default_factory=list)  # (id, SEGMENT state)


class Segment:
    """One challenge in a member's ring today, as the crew sees it."""

    DONE = "done"
    STARTED = "started"  # a number below the day's target
    TODO = "todo"


@dataclass
class Today:
    day: date
    deadline: datetime
    cards: list[Card] = field(default_factory=list)
    crew: list[CrewDay] = field(default_factory=list)


def _card(participant: Participant, record: days.Record, today: date, proofs: list[Proof]) -> Card:
    challenge = participant.challenge
    part = days.span(challenge, participant.left_on)
    monday, _ = week_of(today)
    week = [monday + timedelta(days=n) for n in range(7)]
    return Card(
        challenge=challenge,
        state=days.state(challenge, part, record, today, today),
        total=record.amounts.get(today),
        streak=days.streak(challenge, part, record, today),
        week=[(d, days.state(challenge, part, record, d, today)) for d in week],
        current=days.current(challenge, part, record, today),
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
        segment = (
            Segment.DONE
            if card.settled
            else Segment.STARTED
            if day in record.partial
            else Segment.TODO
        )
        row.challenges.append((participant.challenge_id, segment))
    result.crew = list(crew.values())
    return result


def challenge_windows(
    *, member: Member, challenge_id: UUID, start: date | None = None, until: date | None = None
) -> list[days.Judged] | None:
    """The windows of a challenge the member can see: theirs, with verdicts, when they take part.

    `start`: as if scheduled to begin that day (an admin choosing), without verdicts. `until`: as
    if the member left that day (the leave sheet). A proposal without `start` has no dates: none.
    """
    challenge = challenges.get_challenge(member=member, challenge_id=challenge_id)
    if challenge is None:
        return None
    today = clock.crew_today(member.crew)
    if start is not None:
        first, last = scheduled_dates(challenge.period_kind, challenge.period_length, start, today)
        challenge.period_start, challenge.start_date, challenge.end_date = start, first, last
        return [days.Judged(w, None) for w in windows(challenge, first, last)]
    if challenge.state != Challenge.State.CHOSEN:
        return []
    participant = Participant.objects.filter(
        challenge=challenge, member=member, left_on__isnull=True
    ).first()
    part = days.span(challenge, None)
    if until is not None:
        part = days.Span(part.first, min(part.last, until))
    if participant is None:  # an admin who doesn't take part: needs only
        return [days.Judged(w, None) for w in windows(challenge, part.first, part.last)]
    record = records(challenge_ids=[challenge.pk], member_ids=[member.pk]).get(
        (challenge.pk, member.pk), days.Record()
    )
    return days.judged(challenge, part, record, today)


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
    month_days = dates(*month_of(month))
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
        VISIBLE, check_in__challenge=challenge, check_in__day=day
    ).select_related("original__transcode", "thumb"):
        shown[proof.member_id].append(proof)
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
        Proof.objects.filter(VISIBLE, check_in=OuterRef("pk"))
        .order_by("-updated_at")
        .values("updated_at")[:1]
    )
    shown = Proof.objects.filter(VISIBLE).select_related("original__transcode", "thumb")
    return (
        CheckIn.objects.filter(challenge__in=challenges.visible(member=member))
        .exclude(status=CheckIn.Status.PENDING)
        .annotate(activity_at=Greatest("updated_at", Subquery(newest_proof)))
        .select_related("member", "challenge")
        .prefetch_related(Prefetch("proofs", queryset=shown, to_attr="shown_proofs"))
    )


def reactable_check_in(member: Member, check_in_id: UUID) -> CheckIn | None:
    """A check-in the member sees in the feed as a card of its own (a proof, a number or a
    milestone), so it can get reactions; plain check-ins are said together and get none."""
    check_in = feed(member=member).filter(pk=check_in_id).first()
    if check_in is None:
        return None
    if check_in.shown_proofs or check_in.challenge.measure == Challenge.Measure.QUANTITY:  # type: ignore[attr-defined]
        return check_in
    return check_in if feed_details([check_in])[check_in.pk].milestone is not None else None


MILESTONES = (3, 7, 14, 30)  # days in a row worth a card of their own


@dataclass
class FeedDetail:
    """What a feed card says around a check-in, as of its own day."""

    streak: int | None
    day_index: int  # the check-in's day within the challenge, from 1
    day_count: int
    week: list[tuple[date, str]]  # the 7 days ending on the check-in's day
    last_amount: Decimal | None  # the last "+N" of a number challenge
    target: Decimal | None  # the day's target, when the challenge sets one per day
    milestone: int | None  # the streak, when it just reached one of MILESTONES


def feed_details(check_ins: list[CheckIn]) -> dict[UUID, FeedDetail]:
    """Streaks, weeks and amounts for a page of the feed, in three queries whatever its size."""
    if not check_ins:
        return {}
    challenge_ids = list({c.challenge_id for c in check_ins})
    member_ids = list({c.member_id for c in check_ins})
    left_on = {
        (p.challenge_id, p.member_id): p.left_on
        for p in Participant.objects.filter(
            challenge_id__in=challenge_ids, member_id__in=member_ids
        ).only("challenge_id", "member_id", "left_on")
    }
    loaded = records(challenge_ids=challenge_ids, member_ids=member_ids, proof_days=False)
    last_amounts = dict(
        CheckInEntry.objects.filter(check_in__in=check_ins, amount__isnull=False)
        .order_by("check_in_id", "-number")
        .distinct("check_in_id")
        .values_list("check_in_id", "amount")
    )
    result = {}
    for check_in in check_ins:
        challenge, day = check_in.challenge, check_in.day
        assert challenge.start_date is not None
        assert challenge.end_date is not None
        key = (check_in.challenge_id, check_in.member_id)
        part = days.span(challenge, left_on.get(key))
        record = loaded.get(key, days.Record())
        streak = days.streak(challenge, part, record, day)
        week = [day - timedelta(days=n) for n in range(6, -1, -1)]
        result[check_in.pk] = FeedDetail(
            streak=streak,
            day_index=(day - challenge.start_date).days + 1,
            day_count=(challenge.end_date - challenge.start_date).days + 1,
            week=[(d, days.state(challenge, part, record, d, day)) for d in week],
            last_amount=last_amounts.get(check_in.pk),
            target=challenge.day_min,
            milestone=(
                streak
                if days.is_fixed(challenge) and day in record.done and streak in MILESTONES
                else None
            ),
        )
    return result


@dataclass
class DaySummary:
    check_ins: int
    proofs: int  # the ones the crew can see
    crew_done: bool  # everyone finished everything due that day (fixed-day challenges)


def day_summaries(*, member: Member, on: set[date]) -> dict[date, DaySummary]:
    """What the crew did on each of `on`, on challenges the member can see. Constant queries."""
    if not on:
        return {}
    seen = challenges.visible(member=member)
    check_ins = dict(
        CheckIn.objects.filter(challenge__in=seen, day__in=on)
        .exclude(status=CheckIn.Status.PENDING)
        .order_by()
        .values("day")
        .annotate(n=Count("id"))
        .values_list("day", "n")
    )
    proofs = dict(
        Proof.objects.filter(VISIBLE, check_in__challenge__in=seen, check_in__day__in=on)
        .order_by()
        .values("check_in__day")
        .annotate(n=Count("id"))
        .values_list("check_in__day", "n")
    )
    first, last = min(on), max(on)
    people = list(
        Participant.objects.filter(
            challenge__in=seen,
            challenge__state=Challenge.State.CHOSEN,
            challenge__start_date__lte=last,
            challenge__end_date__gte=first,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=first))
        .select_related("challenge")
    )
    loaded = records(
        challenge_ids=list({p.challenge_id for p in people}),
        member_ids=list({p.member_id for p in people}),
        proof_days=False,
    )
    result = {}
    for day in on:
        due = [
            p
            for p in people
            if days.is_due(p.challenge, day) and day in days.span(p.challenge, p.left_on)
        ]
        result[day] = DaySummary(
            check_ins=check_ins.get(day, 0),
            proofs=proofs.get(day, 0),
            crew_done=bool(due)
            and all(
                day in loaded.get((p.challenge_id, p.member_id), days.Record()).done for p in due
            ),
        )
    return result


@dataclass
class ChallengeMonth:
    """One challenge on a member's page: their month, days with proof, streak, today."""

    challenge: Challenge
    states: list[str]
    proof_days: list[date]
    streak: int | None
    today: str


@dataclass
class ProofDay:
    day: date
    challenge: Challenge
    proofs: list[Proof]


@dataclass
class MemberProgress:
    member: Member
    days: list[date]
    streak: int  # the best current streak among their challenges
    longest_streak: int
    month_done: int  # due days done this month, up to today (daily and weekday challenges)
    month_due: int
    challenges: list[ChallengeMonth]
    proof_days: list[ProofDay]  # latest day first


def member_progress(*, viewer: Member, member_id: UUID, month: date) -> MemberProgress | None:
    """A member's month on the challenges the viewer can see; None for another crew's member."""
    person = crews.get_member(crew=viewer.crew, member_id=member_id)
    if person is None:
        return None
    today = clock.crew_today(viewer.crew)
    first, last = month_of(month)
    month_days = dates(first, last)
    parts = list(
        Participant.objects.filter(
            member=person,
            challenge__in=challenges.visible(member=viewer),
            challenge__state=Challenge.State.CHOSEN,
            challenge__start_date__lte=last,
            challenge__end_date__gte=first,
        )
        .filter(Q(left_on__isnull=True) | Q(left_on__gte=first))
        .select_related("challenge")
        .order_by("challenge__start_date", "challenge__title", "challenge_id")
    )
    loaded = records(challenge_ids=[p.challenge_id for p in parts], member_ids=[person.pk])
    result = MemberProgress(
        member=person,
        days=month_days,
        streak=0,
        longest_streak=0,
        month_done=0,
        month_due=0,
        challenges=[],
        proof_days=[],
    )
    for participant in parts:
        challenge = participant.challenge
        part = days.span(challenge, participant.left_on)
        record = loaded.get((challenge.pk, person.pk), days.Record())
        streak = days.streak(challenge, part, record, today)
        result.streak = max(result.streak, streak or 0)
        result.longest_streak = max(
            result.longest_streak, days.longest_streak(challenge, part, record, today) or 0
        )
        due = [d for d in part.days(first, min(last, today)) if days.is_due(challenge, d)]
        open_today = today in due and today not in record.done
        result.month_due += len(due) - int(open_today)
        result.month_done += sum(1 for d in due if d in record.done)
        result.challenges.append(
            ChallengeMonth(
                challenge=challenge,
                states=[days.state(challenge, part, record, d, today) for d in month_days],
                proof_days=[d for d in month_days if d in record.proof_days],
                streak=streak,
                today=days.state(challenge, part, record, today, today),
            )
        )
    by_challenge = {p.challenge_id: p.challenge for p in parts}
    day_and_challenge = {
        pk: (day, challenge_id)
        for pk, day, challenge_id in CheckIn.objects.filter(
            member=person, challenge_id__in=list(by_challenge), day__range=(first, last)
        ).values_list("pk", "day", "challenge")
    }
    grouped: dict[tuple[date, UUID], list[Proof]] = defaultdict(list)
    for proof in (
        Proof.objects.filter(VISIBLE, check_in__in=list(day_and_challenge))
        .select_related("original__transcode", "thumb")
        .order_by("created_at")
    ):
        grouped[day_and_challenge[proof.subject_id]].append(proof)
    latest_first = sorted(grouped, key=lambda k: (-k[0].toordinal(), by_challenge[k[1]].title))
    result.proof_days = [
        ProofDay(day=day, challenge=by_challenge[challenge_id], proofs=grouped[(day, challenge_id)])
        for day, challenge_id in latest_first
    ]
    return result
