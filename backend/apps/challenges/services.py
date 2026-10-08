"""Challenge rules: the proposal pool, who takes part, votes, the admin's schedule, leaving.

Only a challenge's participants (who have not left) and the crew's admins can see it; to anyone
else it does not exist (`ChallengeNotFound`), like another crew's challenge.

Every write goes through here. Functions are keyword-only and raise DomainError subclasses.
A challenge row is locked (`select_for_update`) in every write that depends on its state, so a
vote never lands on a challenge being edited or scheduled. Proposing locks the crew row, so two
people cannot take the pool's last place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, NamedTuple
from uuid import UUID

from django.db import transaction

from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from apps.crews import selectors as crews
from apps.crews.models import Crew, Member
from apps.crews.services import require_admin

from . import periods
from .models import ICONS, Challenge, Participant, PeriodKind, Punishment, Vote

TITLE_MAX = 60
RULES_MAX = 500
UNIT_MAX = 20
AMOUNT_MAX = Decimal(10**8)
MONTHS_AHEAD = 12
PUNISHMENTS_MAX = 8  # and at least 2, or none: one would be no draw
PUNISHMENT_MAX = 80  # characters
# How long a challenge can run, in each unit of its length.
LENGTH_MAX = {PeriodKind.MONTH: 12, PeriodKind.WEEK: 52, PeriodKind.DAY: 365}
# The most days a unit can have (a period count can ask for at most one check-in a day).
UNIT_DAYS = {PeriodKind.MONTH: 31, PeriodKind.WEEK: 7, PeriodKind.DAY: 1}


class PoolFull(Conflict):
    code = "pool_full"
    message = "The list of proposals is full. Withdraw one or wait until one is chosen."


class NotAProposal(Conflict):
    code = "not_a_proposal"
    message = "This challenge has already been chosen, so it cannot be changed or voted on."


class ChallengeNotFound(NotFound):
    code = "challenge_not_found"
    message = "This challenge does not exist."


class NotYourProposal(PermissionDenied):
    code = "not_your_proposal"
    message = "Only the person who proposed this challenge can change it."


class ChallengeStarted(Conflict):
    code = "challenge_started"
    message = "This challenge has already started."


class ChallengeFinished(Conflict):
    code = "challenge_finished"
    message = "This challenge has already finished."


class PeriodOver(Conflict):
    code = "period_over"
    message = "This period is over. Choose a later one."


class PeriodTooFar(ValidationFailed):
    code = "period_too_far"
    message = f"Choose a period at most {MONTHS_AHEAD} months ahead."


class TooFewDays(Conflict):
    code = "too_few_days"
    message = "The challenge asks for more times than the days in this period."


class NotAParticipant(PermissionDenied):
    code = "not_a_participant"
    message = "Only the people taking part can do this."


class NotChosenYet(Conflict):
    code = "not_chosen_yet"
    message = "Only a chosen challenge has participants."


# --- the shape of a challenge ------------------------------------------------------------------


class PunishmentShape(NamedTuple):
    text: str
    proof_required: bool


@dataclass(frozen=True)
class Shape:
    """Everything the creator decides. Validated by `clean_shape`."""

    title: str
    rules: str = ""
    icon: str = "star"
    measure: str = Challenge.Measure.CHECK
    unit: str = ""
    window: str = Challenge.Window.DAY
    on_days: int = 0
    need_kind: str = Challenge.NeedKind.COUNT
    need_value: Decimal = Decimal(1)
    day_min: Decimal | None = None
    period_kind: str = PeriodKind.MONTH
    period_length: int = 1
    proof_required: bool = False
    punishments: tuple[PunishmentShape, ...] = ()


def clean_shape(raw: dict[str, Any]) -> Shape:
    """Normalize and check a challenge's shape; raise ValidationFailed with every bad field."""
    errors: dict[str, list[str]] = {}

    def bad(field: str, message: str) -> None:
        errors.setdefault(field, []).append(message)

    title = " ".join(str(raw.get("title", "")).split())
    if not 1 <= len(title) <= TITLE_MAX:
        bad("title", f"Use 1-{TITLE_MAX} characters.")
    rules = str(raw.get("rules", "") or "").strip()
    if len(rules) > RULES_MAX:
        bad("rules", f"Use at most {RULES_MAX} characters.")
    icon = raw.get("icon") or "star"
    if icon not in ICONS:
        bad("icon", "Choose one of the icons.")

    measure = raw.get("measure", Challenge.Measure.CHECK)
    if measure not in Challenge.Measure.values:
        bad("measure", "Choose what people record.")
    unit = " ".join(str(raw.get("unit", "") or "").split())
    if measure == Challenge.Measure.QUANTITY and not 1 <= len(unit) <= UNIT_MAX:
        bad("unit", f"Name the unit in 1-{UNIT_MAX} characters, for example km or pages.")
    if measure != Challenge.Measure.QUANTITY:
        unit = ""

    period_kind = raw.get("period_kind", PeriodKind.MONTH)
    period_length = raw.get("period_length", 1)
    longest = 0  # the most days the period can have
    if period_kind not in PeriodKind.values:
        bad("period_kind", "Choose months, weeks or days.")
    elif not isinstance(period_length, int) or not 1 <= period_length <= LENGTH_MAX[period_kind]:
        bad("period_length", f"Choose 1-{LENGTH_MAX[period_kind]}.")
    else:
        longest = UNIT_DAYS[period_kind] * period_length

    window = raw.get("window", Challenge.Window.DAY)
    if window not in Challenge.Window.values:
        bad("window", "Choose how often.")
    elif window == Challenge.Window.WEEK and 0 < longest < 7:
        bad("window", "A weekly challenge needs a period of at least 7 days.")
    elif window == Challenge.Window.MONTH and period_kind != PeriodKind.MONTH:
        bad("window", "A monthly challenge needs a period counted in months.")
    on_days = 0
    days = raw.get("on_days") or []
    if days and window != Challenge.Window.DAY:
        bad("on_days", "Chosen days are only for a challenge judged each day.")
    elif any(not isinstance(d, int) or not 0 <= d <= 6 for d in days):
        bad("on_days", "Choose days from Monday (0) to Sunday (6).")
    else:
        on_days = sum(1 << d for d in set(days))

    numbers = measure == Challenge.Measure.QUANTITY
    need_kind = raw.get("need_kind", Challenge.NeedKind.COUNT)
    need_value = _positive(raw.get("need_value", 1))
    if need_kind not in Challenge.NeedKind.values:
        bad("need_kind", "Choose a number of check-ins or a total.")
    elif need_kind == Challenge.NeedKind.AMOUNT:
        if not numbers:
            bad("need_kind", "Only a challenge that records a number can have a total.")
        elif window == Challenge.Window.DAY:
            bad("need_kind", "For each day, set the least amount a check-in needs instead.")
        if need_value is None:
            bad("need_value", "Give a number above zero.")
    elif window in Challenge.Window.values:
        # A month asks for at most 28, so February can meet it too.
        limit = {Challenge.Window.DAY: 1, Challenge.Window.WEEK: 7, Challenge.Window.MONTH: 28}.get(
            window, longest or 1
        )
        if need_value is None or need_value != need_value.to_integral_value() or need_value > limit:
            bad("need_value", f"Choose 1-{limit}." if limit > 1 else "Each day asks for 1.")

    day_min = None
    if raw.get("day_min") is not None:
        day_min = _positive(raw.get("day_min"))
        if not numbers or need_kind != Challenge.NeedKind.COUNT:
            bad("day_min", "Only a challenge that counts number check-ins can set a minimum.")
        elif day_min is None:
            bad("day_min", "Give a number above zero.")

    proof_required = bool(raw.get("proof_required"))

    punishments = tuple(
        PunishmentShape(str(p.get("text", "")).strip(), bool(p.get("proof_required")))
        for p in raw.get("punishments") or []
    )
    if len(punishments) == 1 or len(punishments) > PUNISHMENTS_MAX:
        bad("punishments", "Add 2 to 8 punishments, or none.")
    if any(not p.text or len(p.text) > PUNISHMENT_MAX for p in punishments):
        bad("punishments", "Write each punishment in 1 to 80 characters.")
    if len({p.text.casefold() for p in punishments}) < len(punishments):
        bad("punishments", "Each punishment must be different.")

    if errors:
        raise ValidationFailed(fields=errors)
    return Shape(
        title=title,
        rules=rules,
        icon=icon,
        measure=measure,
        unit=unit,
        window=window,
        on_days=on_days,
        need_kind=need_kind,
        need_value=need_value or Decimal(1),
        day_min=day_min,
        period_kind=period_kind,
        period_length=period_length,
        proof_required=proof_required,
        punishments=punishments,
    )


def _positive(value: Any) -> Decimal | None:
    """A number above zero (and below AMOUNT_MAX), or None."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and 0 < number < AMOUNT_MAX else None


def _apply(challenge: Challenge, shape: Shape) -> None:
    """Set the challenge's fields; its punishments are rows of their own (`_set_punishments`)."""
    for field, value in shape.__dict__.items():
        if field != "punishments":
            setattr(challenge, field, value)


def _punishments_of(challenge: Challenge) -> tuple[PunishmentShape, ...]:
    return tuple(
        PunishmentShape(p.text, p.proof_required)
        for p in Punishment.objects.filter(challenge=challenge).order_by("position")
    )


def _set_punishments(challenge: Challenge, punishments: tuple[PunishmentShape, ...]) -> None:
    """Replace them as a whole: only a proposal changes, and no spin can point at them yet."""
    Punishment.objects.filter(challenge=challenge).delete()
    Punishment.objects.bulk_create(
        Punishment(
            crew_id=challenge.crew_id,
            challenge=challenge,
            position=position,
            text=p.text,
            proof_required=p.proof_required,
        )
        for position, p in enumerate(punishments, start=1)
    )


# --- the pool ----------------------------------------------------------------------------------


def _takes_part(challenge: Challenge, member: Member) -> bool:
    """`member` is one of the challenge's participants and has not left it."""
    return Participant.objects.filter(
        challenge=challenge, member=member, left_on__isnull=True
    ).exists()


def _lock(by: Member, challenge_id: UUID) -> Challenge:
    """The challenge, locked, if `by` can see it (a participant or an admin)."""
    rows = Challenge.objects.for_crew(by.crew).select_for_update()
    challenge = rows.filter(pk=challenge_id).first()
    if challenge is None or not (by.is_admin or _takes_part(challenge, by)):
        raise ChallengeNotFound()
    return challenge


def _require_proposed(challenge: Challenge) -> None:
    if challenge.state != Challenge.State.PROPOSED:
        raise NotAProposal()


def _crew_member_ids(crew: Crew, member_ids: list[UUID] | None) -> set[UUID]:
    """The given ids, checked to be members of the crew; None means the whole crew."""
    everyone = {m.pk for m in crews.list_members(crew=crew)}
    if member_ids is None:
        return everyone
    chosen = set(member_ids)
    if not chosen <= everyone:
        raise ValidationFailed(fields={"participant_ids": ["Choose people from your crew."]})
    return chosen


def _set_participants(challenge: Challenge, by: Member, member_ids: set[UUID]) -> None:
    """Make `member_ids` (plus the creator) the participants; removed people lose their vote."""
    if challenge.created_by_id:
        member_ids = member_ids | {challenge.created_by_id}
    rows = Participant.objects.filter(challenge=challenge)
    current = set(rows.values_list("member_id", flat=True))
    removed = current - member_ids
    rows.filter(member_id__in=removed).delete()
    Vote.objects.filter(challenge=challenge, member_id__in=removed).delete()
    Participant.objects.bulk_create(
        Participant(crew=by.crew, challenge=challenge, member_id=member_id)
        for member_id in member_ids - current
    )


@transaction.atomic
def propose_challenge(
    *, by: Member, shape: dict[str, Any], participant_ids: list[UUID] | None = None
) -> Challenge:
    """Any member adds a proposal to the crew's pool, while the pool has room.

    `participant_ids` are who takes part (None: the whole crew); the creator is always one of them.
    """
    cleaned = clean_shape(shape)
    crew = Crew.objects.select_for_update().get(pk=by.crew_id)
    chosen = _crew_member_ids(crew, participant_ids)
    in_pool = Challenge.objects.for_crew(crew).filter(state=Challenge.State.PROPOSED).count()
    if in_pool >= crew.max_proposals:
        raise PoolFull()
    challenge = Challenge(crew=crew, created_by=by)
    _apply(challenge, cleaned)
    challenge.save()
    _set_punishments(challenge, cleaned.punishments)
    _set_participants(challenge, by, chosen)
    return challenge


@transaction.atomic
def edit_proposal(
    *,
    by: Member,
    challenge_id: UUID,
    shape: dict[str, Any],
    participant_ids: list[UUID] | None = None,
) -> Challenge:
    """The creator changes their proposal while it is in the pool.

    Changing the challenge itself resets every vote; changing only who takes part keeps the votes
    of the people who stay. `participant_ids=None` keeps the participants as they are.
    """
    cleaned = clean_shape(shape)
    challenge = _lock(by, challenge_id)
    if challenge.created_by_id != by.pk:
        raise NotYourProposal()
    _require_proposed(challenge)
    fields = {k: v for k, v in cleaned.__dict__.items() if k != "punishments"}
    if (
        any(getattr(challenge, field) != value for field, value in fields.items())
        or _punishments_of(challenge) != cleaned.punishments
    ):
        _apply(challenge, cleaned)
        challenge.revision += 1
        challenge.save()
        _set_punishments(challenge, cleaned.punishments)
        Vote.objects.filter(challenge=challenge).delete()
    if participant_ids is not None:
        _set_participants(challenge, by, _crew_member_ids(by.crew, participant_ids))
    return challenge


@transaction.atomic
def set_participants(*, by: Member, challenge_id: UUID, participant_ids: list[UUID]) -> Challenge:
    """The creator changes who takes part while the challenge is a proposal."""
    challenge = _lock(by, challenge_id)
    if challenge.created_by_id != by.pk:
        raise NotYourProposal()
    _require_proposed(challenge)
    _set_participants(challenge, by, _crew_member_ids(by.crew, participant_ids))
    return challenge


@transaction.atomic
def withdraw_proposal(*, by: Member, challenge_id: UUID) -> None:
    """The creator (or an admin) takes a proposal out of the pool. Soft delete."""
    challenge = _lock(by, challenge_id)
    if challenge.created_by_id != by.pk and not by.is_admin:
        raise NotYourProposal()
    _require_proposed(challenge)
    Vote.objects.filter(challenge=challenge).delete()
    challenge.delete()


# --- votes -------------------------------------------------------------------------------------


@transaction.atomic
def cast_vote(*, by: Member, challenge_id: UUID) -> Vote:
    """Vote for a proposal. A member can vote for any number of proposals, once each.

    Only participants vote; an admin who is not one sees the proposal but has no vote.
    """
    challenge = _lock(by, challenge_id)
    _require_proposed(challenge)
    if not _takes_part(challenge, by):
        raise NotAParticipant()
    vote, _ = Vote.objects.get_or_create(challenge=challenge, member=by, defaults={"crew": by.crew})
    return vote


@transaction.atomic
def clear_vote(*, by: Member, challenge_id: UUID) -> None:
    """Take your vote back. Nothing happens if you had not voted."""
    challenge = _lock(by, challenge_id)
    _require_proposed(challenge)
    Vote.objects.filter(challenge=challenge, member=by).delete()


# --- the admin's schedule ----------------------------------------------------------------------


@transaction.atomic
def schedule_challenge(*, by: Member, challenge_id: UUID, period_start: date) -> Challenge:
    """An admin takes a proposal out of the pool and picks when it starts.

    How long it runs was proposed with it: months start on the 1st, weeks on a Monday, a number of
    days on any day from tomorrow. Also moves a scheduled challenge that has not started (its
    length stays). Chosen while its month or week is under way: it starts tomorrow, and its windows
    ask for less. The participants stay as they are (people who opted out stay out when it moves).
    Scheduling for the same start changes nothing.
    """
    require_admin(by)
    challenge = _lock(by, challenge_id)
    kind = challenge.period_kind
    if kind == PeriodKind.MONTH and period_start.day != 1:
        raise ValidationFailed(fields={"period_start": ["A month starts on its first day."]})
    if kind == PeriodKind.WEEK and period_start.weekday() != 0:
        raise ValidationFailed(fields={"period_start": ["A week starts on a Monday."]})
    today = clock.crew_today(by.crew)
    first = period_start
    start, last = periods.scheduled_dates(kind, challenge.period_length, first, today)

    if challenge.state == Challenge.State.CHOSEN:
        assert challenge.start_date is not None
        if challenge.period_start == first:
            return challenge
        if today >= challenge.start_date:
            raise ChallengeStarted()

    if kind == PeriodKind.DAY and first <= today:
        raise ValidationFailed(fields={"period_start": ["Start tomorrow or later."]})
    if start > last:
        raise PeriodOver()
    if first > periods.add_months(periods.month_of(today)[0], MONTHS_AHEAD):
        raise PeriodTooFar(fields={"period_start": [PeriodTooFar.message]})
    counted_over_the_period = (
        challenge.window == Challenge.Window.PERIOD
        and challenge.need_kind == Challenge.NeedKind.COUNT
    )
    if counted_over_the_period and challenge.need_value > (last - first).days + 1:
        raise TooFewDays()  # a late start asks for less (windows.py), a short month can't

    challenge.state = Challenge.State.CHOSEN
    challenge.period_start = first
    challenge.start_date = start
    challenge.end_date = last
    challenge.chosen_by = by
    challenge.chosen_at = clock.now()
    challenge.save()
    return challenge


@transaction.atomic
def unschedule_challenge(*, by: Member, challenge_id: UUID) -> Challenge:
    """An admin puts a scheduled challenge back in the pool before it starts.

    Allowed when the pool is full: the proposal was there before. Its old votes count again.
    """
    require_admin(by)
    challenge = _lock(by, challenge_id)
    if challenge.state != Challenge.State.CHOSEN:
        return challenge
    assert challenge.start_date is not None
    if clock.crew_today(by.crew) >= challenge.start_date:
        raise ChallengeStarted()
    challenge.state = Challenge.State.PROPOSED
    challenge.period_start = challenge.start_date = challenge.end_date = None
    challenge.chosen_by = None
    challenge.chosen_at = None
    challenge.save()
    return challenge


# --- taking part -------------------------------------------------------------------------------


@transaction.atomic
def stop_taking_part(*, by: Member, challenge_id: UUID) -> None:
    """Opt out before the start (the row goes) or leave a running challenge (today is the last
    day counted). Either way the member stops seeing it; the board keeps a leaver's days.
    """
    rows = Challenge.objects.for_crew(by.crew).select_for_update()
    found = rows.filter(pk=challenge_id).first()
    if found is None or not _takes_part(found, by):
        raise ChallengeNotFound()
    if found.state != Challenge.State.CHOSEN:
        raise NotChosenYet()
    assert found.start_date is not None
    assert found.end_date is not None
    today = clock.crew_today(by.crew)
    if today > found.end_date:
        raise ChallengeFinished()
    row = Participant.objects.get(challenge=found, member=by)
    if today < found.start_date:
        row.delete()
        Vote.objects.filter(challenge=found, member=by).delete()
    else:
        row.left_on = today
        row.save(update_fields=["left_on", "updated_at"])
