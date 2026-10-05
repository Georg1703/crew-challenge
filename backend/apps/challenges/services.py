"""Challenge rules: the proposal pool, votes, the admin's schedule, taking part.

Every write goes through here. Functions are keyword-only and raise DomainError subclasses.
A challenge row is locked (`select_for_update`) in every write that depends on its state, so a
vote never lands on a challenge being edited or scheduled. Proposing locks the crew row, so two
people cannot take the pool's last place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from django.db import transaction

from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from apps.crews import selectors as crews
from apps.crews.models import Crew, Member
from apps.crews.services import require_admin

from . import periods
from .models import ICONS, Challenge, Participation, PeriodKind, Vote

TITLE_MAX = 60
RULES_MAX = 500
UNIT_MAX = 20
TIMES_MAX = {
    Challenge.Frequency.TIMES_PER_WEEK: 7,
    Challenge.Frequency.TIMES_PER_PERIOD: 31,
}


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
    message = "Choose a period at most 12 months ahead."


class PeriodKindNotAvailable(ValidationFailed):
    code = "period_kind_not_available"
    message = "Only months can be chosen for now."


class TooFewDays(Conflict):
    code = "too_few_days"
    message = "The challenge asks for more times than the days it would run."


class NotChosenYet(Conflict):
    code = "not_chosen_yet"
    message = "Only a chosen challenge has participants."


# --- the shape of a challenge ------------------------------------------------------------------


@dataclass(frozen=True)
class Shape:
    """Everything the creator decides. Validated by `clean_shape`."""

    title: str
    rules: str = ""
    icon: str = "star"
    measure: str = Challenge.Measure.CHECK
    unit: str = ""
    frequency: str = Challenge.Frequency.DAILY
    weekdays: int = 0
    times: int | None = None
    target_scope: str = Challenge.TargetScope.NONE
    target_value: Decimal | None = None
    proof_kind: str = Challenge.ProofKind.NONE
    proof_required: bool = False


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

    frequency = raw.get("frequency", Challenge.Frequency.DAILY)
    if frequency not in Challenge.Frequency.values:
        bad("frequency", "Choose how often.")
    weekdays = 0
    if frequency == Challenge.Frequency.WEEKDAYS:
        days = raw.get("weekdays") or []
        if not days or any(not isinstance(d, int) or not 0 <= d <= 6 for d in days):
            bad("weekdays", "Choose at least one day.")
        else:
            weekdays = sum(1 << d for d in set(days))
    times = None
    if frequency in TIMES_MAX:
        times = raw.get("times")
        limit = TIMES_MAX[frequency]
        if not isinstance(times, int) or not 1 <= times <= limit:
            bad("times", f"Choose 1-{limit}.")

    target_scope = raw.get("target_scope") or Challenge.TargetScope.NONE
    target_value = None
    if target_scope not in Challenge.TargetScope.values:
        bad("target_scope", "Choose what the target counts.")
    elif target_scope != Challenge.TargetScope.NONE:
        if measure != Challenge.Measure.QUANTITY:
            bad("target_scope", "Only a challenge that records a number can have a target.")
        try:
            target_value = Decimal(str(raw.get("target_value")))
            if not target_value.is_finite() or target_value <= 0 or target_value >= 10**8:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            bad("target_value", "Give a number above zero.")

    proof_kind = raw.get("proof_kind") or Challenge.ProofKind.NONE
    if proof_kind not in Challenge.ProofKind.values:
        bad("proof_kind", "Choose the kind of proof.")
    proof_required = bool(raw.get("proof_required")) and proof_kind != Challenge.ProofKind.NONE

    if errors:
        raise ValidationFailed(fields=errors)
    return Shape(
        title=title,
        rules=rules,
        icon=icon,
        measure=measure,
        unit=unit,
        frequency=frequency,
        weekdays=weekdays,
        times=times,
        target_scope=target_scope,
        target_value=target_value,
        proof_kind=proof_kind,
        proof_required=proof_required,
    )


def _apply(challenge: Challenge, shape: Shape) -> None:
    for field, value in shape.__dict__.items():
        setattr(challenge, field, value)


# --- the pool ----------------------------------------------------------------------------------


def _lock(crew: Crew, challenge_id: UUID) -> Challenge:
    rows = Challenge.objects.for_crew(crew).select_for_update()
    challenge = rows.filter(pk=challenge_id).first()
    if challenge is None:
        raise ChallengeNotFound()
    return challenge


def _require_proposed(challenge: Challenge) -> None:
    if challenge.state != Challenge.State.PROPOSED:
        raise NotAProposal()


@transaction.atomic
def propose_challenge(*, by: Member, shape: dict[str, Any]) -> Challenge:
    """Any member adds a proposal to the crew's pool, while the pool has room."""
    cleaned = clean_shape(shape)
    crew = Crew.objects.select_for_update().get(pk=by.crew_id)
    in_pool = Challenge.objects.for_crew(crew).filter(state=Challenge.State.PROPOSED).count()
    if in_pool >= crew.max_proposals:
        raise PoolFull()
    challenge = Challenge(crew=crew, created_by=by)
    _apply(challenge, cleaned)
    challenge.save()
    return challenge


@transaction.atomic
def edit_proposal(*, by: Member, challenge_id: UUID, shape: dict[str, Any]) -> Challenge:
    """The creator changes their proposal while it is in the pool. Its votes are reset."""
    cleaned = clean_shape(shape)
    challenge = _lock(by.crew, challenge_id)
    if challenge.created_by_id != by.pk:
        raise NotYourProposal()
    _require_proposed(challenge)
    _apply(challenge, cleaned)
    challenge.revision += 1
    challenge.save()
    Vote.objects.filter(challenge=challenge).delete()
    return challenge


@transaction.atomic
def withdraw_proposal(*, by: Member, challenge_id: UUID) -> None:
    """The creator (or an admin) takes a proposal out of the pool. Soft delete."""
    challenge = _lock(by.crew, challenge_id)
    if challenge.created_by_id != by.pk and not by.is_admin:
        raise NotYourProposal()
    _require_proposed(challenge)
    Vote.objects.filter(challenge=challenge).delete()
    challenge.delete()


def _get_challenge(crew: Crew, challenge_id: UUID) -> Challenge:
    challenge = Challenge.objects.for_crew(crew).filter(pk=challenge_id).first()
    if challenge is None:
        raise ChallengeNotFound()
    return challenge


# --- votes -------------------------------------------------------------------------------------


@transaction.atomic
def cast_vote(*, by: Member, challenge_id: UUID) -> Vote:
    """Vote for a proposal. A member can vote for any number of proposals, once each."""
    challenge = _lock(by.crew, challenge_id)
    _require_proposed(challenge)
    vote, _ = Vote.objects.get_or_create(challenge=challenge, member=by, defaults={"crew": by.crew})
    return vote


@transaction.atomic
def clear_vote(*, by: Member, challenge_id: UUID) -> None:
    """Take your vote back. Nothing happens if you had not voted."""
    challenge = _lock(by.crew, challenge_id)
    _require_proposed(challenge)
    Vote.objects.filter(challenge=challenge, member=by).delete()


# --- the admin's schedule ----------------------------------------------------------------------

MONTHS_AHEAD = 12


def _days_needed(challenge: Challenge) -> int:
    if challenge.frequency == Challenge.Frequency.TIMES_PER_PERIOD and challenge.times:
        return challenge.times
    return 1


@transaction.atomic
def schedule_challenge(
    *, by: Member, challenge_id: UUID, period_kind: str, period_start: date
) -> Challenge:
    """An admin takes a proposal out of the pool and schedules it for a period.

    Also moves a scheduled challenge that has not started. Chosen before the period: it runs the
    whole period. Chosen late (the period has begun): it starts tomorrow. The whole crew takes
    part (when moved, everyone takes part again). Scheduling for the same period changes nothing.
    """
    require_admin(by)
    if period_kind != PeriodKind.MONTH:
        raise PeriodKindNotAvailable(fields={"period_kind": [PeriodKindNotAvailable.message]})
    if period_start.day != 1:
        raise ValidationFailed(fields={"period_start": ["A month starts on its first day."]})
    challenge = _lock(by.crew, challenge_id)
    today = clock.crew_today(by.crew)
    first, last = periods.month_of(period_start)

    if challenge.state == Challenge.State.CHOSEN:
        assert challenge.start_date is not None
        if challenge.period_kind == period_kind and challenge.period_start == first:
            return challenge
        if today >= challenge.start_date:
            raise ChallengeStarted()

    start = first if today < first else today + timedelta(days=1)
    if start > last:
        raise PeriodOver()
    if first > periods.add_months(periods.month_of(today)[0], MONTHS_AHEAD):
        raise PeriodTooFar(fields={"period_start": [PeriodTooFar.message]})
    if (last - start).days + 1 < _days_needed(challenge):
        raise TooFewDays()

    challenge.state = Challenge.State.CHOSEN
    challenge.period_kind = period_kind
    challenge.period_start = first
    challenge.start_date = start
    challenge.end_date = last
    challenge.chosen_by = by
    challenge.chosen_at = clock.now()
    challenge.save()
    Participation.objects.filter(challenge=challenge).delete()
    Participation.objects.bulk_create(
        Participation(crew=by.crew, challenge=challenge, member=member, joined_on=start)
        for member in crews.list_members(crew=by.crew)
    )
    return challenge


@transaction.atomic
def unschedule_challenge(*, by: Member, challenge_id: UUID) -> Challenge:
    """An admin puts a scheduled challenge back in the pool before it starts.

    Allowed when the pool is full: the proposal was there before. Its old votes count again.
    """
    require_admin(by)
    challenge = _lock(by.crew, challenge_id)
    if challenge.state != Challenge.State.CHOSEN:
        return challenge
    assert challenge.start_date is not None
    if clock.crew_today(by.crew) >= challenge.start_date:
        raise ChallengeStarted()
    Participation.objects.filter(challenge=challenge).delete()
    challenge.state = Challenge.State.PROPOSED
    challenge.period_kind = ""
    challenge.period_start = challenge.start_date = challenge.end_date = None
    challenge.chosen_by = None
    challenge.chosen_at = None
    challenge.save()
    return challenge


# --- taking part -------------------------------------------------------------------------------


def _get_chosen(crew: Crew, challenge_id: UUID) -> Challenge:
    challenge = _get_challenge(crew, challenge_id)
    if challenge.state != Challenge.State.CHOSEN:
        raise NotChosenYet()
    return challenge


@transaction.atomic
def take_part(*, by: Member, challenge_id: UUID) -> Participation:
    """Opt back in before the challenge starts."""
    challenge = _get_chosen(by.crew, challenge_id)
    assert challenge.start_date is not None
    if clock.crew_today(by.crew) >= challenge.start_date:
        raise ChallengeStarted()
    participation, _ = Participation.objects.get_or_create(
        challenge=challenge,
        member=by,
        defaults={"crew": by.crew, "joined_on": challenge.start_date},
    )
    return participation


@transaction.atomic
def stop_taking_part(*, by: Member, challenge_id: UUID) -> None:
    """Opt out before the start, or leave a running challenge (today is the last day counted)."""
    challenge = _get_chosen(by.crew, challenge_id)
    assert challenge.start_date is not None
    assert challenge.end_date is not None
    today = clock.crew_today(by.crew)
    if today > challenge.end_date:
        raise ChallengeFinished()
    participation = Participation.objects.filter(challenge=challenge, member=by).first()
    if participation is None:
        return
    if today < challenge.start_date:
        participation.delete()
    elif participation.ended_on is None:
        participation.ended_on = today
        participation.save(update_fields=["ended_on", "updated_at"])


def add_to_running_challenges(*, member: Member) -> list[Participation]:
    """Someone who joins the crew takes part in its upcoming and running challenges."""
    today = clock.crew_today(member.crew)
    added = []
    challenges = Challenge.objects.for_crew(member.crew).filter(
        state=Challenge.State.CHOSEN, end_date__gte=today
    )
    for challenge in challenges:
        assert challenge.start_date is not None
        participation, created = Participation.objects.get_or_create(
            challenge=challenge,
            member=member,
            defaults={"crew": member.crew, "joined_on": max(challenge.start_date, today)},
        )
        if created:
            added.append(participation)
    return added
