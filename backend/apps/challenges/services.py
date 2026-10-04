"""Challenge rules: proposing, editing, voting, the admin's choice, taking part.

Every write goes through here. Functions are keyword-only and raise DomainError subclasses.
A round is locked (`select_for_update`) in every write that depends on its state, so a vote can
never land on an edited proposal or a closed round.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
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
from .models import ICONS, Challenge, Participation, PeriodKind, Round, Vote

TITLE_MAX = 60
RULES_MAX = 500
UNIT_MAX = 20
TIMES_MAX = {
    Challenge.Frequency.TIMES_PER_WEEK: 7,
    Challenge.Frequency.TIMES_PER_PERIOD: 31,
}


class RoundClosed(Conflict):
    code = "round_closed"
    message = "This round is closed: a challenge has already been chosen."


class RoundNotFound(NotFound):
    code = "round_not_found"
    message = "This round does not exist."


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
    message = "This period is over. Choose a challenge for the next one."


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


# --- rounds ------------------------------------------------------------------------------------


@transaction.atomic
def open_round(*, crew: Crew) -> Round:
    """The round people propose and vote in now.

    This month's round while nobody has chosen yet (an admin can still choose late), otherwise
    the first month after it whose round is still open. Created on first use.
    """
    today = clock.crew_today(crew)
    start, end = periods.month_of(today)
    current = (
        Round.objects.for_crew(crew)
        .filter(period_kind=PeriodKind.MONTH, period_start=start)
        .first()
    )
    if current is not None and current.state == Round.State.OPEN:
        return current
    while True:
        start, end = periods.next_month_of(start)
        round_, _ = Round.objects.get_or_create(
            crew=crew,
            period_kind=PeriodKind.MONTH,
            period_start=start,
            defaults={"period_end": end},
        )
        if round_.state == Round.State.OPEN:
            return round_


def _lock_round(round_id: UUID, crew: Crew) -> Round:
    round_ = Round.objects.select_for_update().for_crew(crew).filter(pk=round_id).first()
    if round_ is None:
        raise RoundNotFound()
    return round_


def _require_open(round_: Round) -> None:
    if round_.state != Round.State.OPEN:
        raise RoundClosed()


# --- proposals ---------------------------------------------------------------------------------


@transaction.atomic
def propose_challenge(*, by: Member, shape: dict[str, Any]) -> Challenge:
    """Any member proposes a challenge for the open round."""
    cleaned = clean_shape(shape)
    round_ = _lock_round(open_round(crew=by.crew).pk, by.crew)
    _require_open(round_)
    challenge = Challenge(crew=by.crew, round=round_, created_by=by)
    _apply(challenge, cleaned)
    challenge.save()
    return challenge


@transaction.atomic
def edit_proposal(*, by: Member, challenge_id: UUID, shape: dict[str, Any]) -> Challenge:
    """The creator changes their proposal while the round is open. Its votes are reset."""
    cleaned = clean_shape(shape)
    challenge = _get_challenge(by.crew, challenge_id)
    _lock_round(challenge.round_id, by.crew)
    challenge.refresh_from_db()
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
    """The creator (or an admin) removes a proposal while the round is open. Soft delete."""
    challenge = _get_challenge(by.crew, challenge_id)
    _lock_round(challenge.round_id, by.crew)
    challenge.refresh_from_db()
    if challenge.created_by_id != by.pk and not by.is_admin:
        raise NotYourProposal()
    _require_proposed(challenge)
    Vote.objects.filter(challenge=challenge).delete()
    challenge.delete()


@transaction.atomic
def repropose(*, by: Member, challenge_id: UUID) -> Challenge:
    """Copy a challenge that was not chosen into the open round, proposed by `by`."""
    source = _get_challenge(by.crew, challenge_id)
    if source.state != Challenge.State.NOT_CHOSEN:
        raise Conflict(message="Only a challenge that was not chosen can be proposed again.")
    round_ = _lock_round(open_round(crew=by.crew).pk, by.crew)
    _require_open(round_)
    copy = Challenge(crew=by.crew, round=round_, created_by=by)
    for field in Shape.__dataclass_fields__:
        setattr(copy, field, getattr(source, field))
    copy.save()
    return copy


def _get_challenge(crew: Crew, challenge_id: UUID) -> Challenge:
    challenge = Challenge.objects.for_crew(crew).filter(pk=challenge_id).first()
    if challenge is None:
        raise ChallengeNotFound()
    return challenge


def _require_proposed(challenge: Challenge) -> None:
    if challenge.state != Challenge.State.PROPOSED or challenge.round.state != Round.State.OPEN:
        raise RoundClosed()


# --- votes -------------------------------------------------------------------------------------


@transaction.atomic
def cast_vote(*, by: Member, challenge_id: UUID) -> Vote:
    """Vote for a proposal in its round. Replaces your earlier vote in that round."""
    challenge = _get_challenge(by.crew, challenge_id)
    round_ = _lock_round(challenge.round_id, by.crew)
    _require_open(round_)
    if not Challenge.objects.filter(pk=challenge.pk, state=Challenge.State.PROPOSED).exists():
        raise ChallengeNotFound()
    vote, _ = Vote.objects.update_or_create(
        round=round_, member=by, defaults={"challenge": challenge, "crew": by.crew}
    )
    return vote


@transaction.atomic
def clear_vote(*, by: Member, round_id: UUID) -> None:
    round_ = _lock_round(round_id, by.crew)
    _require_open(round_)
    Vote.objects.filter(round=round_, member=by).delete()


# --- the admin's choice ------------------------------------------------------------------------


@transaction.atomic
def choose_challenge(*, by: Member, challenge_id: UUID) -> Round:
    """An admin chooses the round's challenge, or changes the choice before it starts.

    Chosen before the period: it runs the whole period. Chosen late (the period has begun): it
    starts tomorrow. The whole crew takes part. Choosing the same challenge again changes nothing.
    """
    require_admin(by)
    challenge = _get_challenge(by.crew, challenge_id)
    round_ = _lock_round(challenge.round_id, by.crew)
    challenge.refresh_from_db()
    today = clock.crew_today(by.crew)

    if round_.chosen_id == challenge.pk:
        return round_
    previous = round_.chosen
    if previous is not None and previous.start_date and today >= previous.start_date:
        raise ChallengeStarted()
    if challenge.state == Challenge.State.PROPOSED and round_.state == Round.State.CLOSED:
        raise RoundClosed()

    start = round_.period_start if today < round_.period_start else today + timedelta(days=1)
    if start > round_.period_end:
        raise PeriodOver()

    proposals = Challenge.objects.filter(round=round_).exclude(pk=challenge.pk)
    proposals.update(state=Challenge.State.NOT_CHOSEN, start_date=None, end_date=None)
    if previous is not None:
        Participation.objects.filter(challenge=previous).delete()

    challenge.state = Challenge.State.CHOSEN
    challenge.start_date = start
    challenge.end_date = round_.period_end
    challenge.save(update_fields=["state", "start_date", "end_date", "updated_at"])
    Participation.objects.bulk_create(
        Participation(crew=by.crew, challenge=challenge, member=member, joined_on=start)
        for member in crews.list_members(crew=by.crew)
    )

    round_.state = Round.State.CLOSED
    round_.chosen = challenge
    round_.chosen_by = by
    round_.chosen_at = clock.now()
    round_.save(update_fields=["state", "chosen", "chosen_by", "chosen_at", "updated_at"])
    return round_


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
