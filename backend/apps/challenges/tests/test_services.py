from datetime import date
from decimal import Decimal

import pytest
import time_machine
from django.db import IntegrityError, transaction

from apps.challenges import periods, selectors, services
from apps.challenges.models import Challenge, Participant, Punishment, Vote
from apps.challenges.windows import windows
from apps.core.errors import PermissionDenied, ValidationFailed
from apps.crews import services as crews
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

PUSHUPS = {
    "title": "50 push-ups a day",
    "icon": "dumbbell",
    "measure": "quantity",
    "unit": "push-ups",
    "day_min": 50,
    "proof_required": True,
}
NO_SUGAR = {
    "title": "No sugar on weekdays",
    "measure": "abstain",
    "on_days": [0, 1, 2, 3, 4],
}

OCT = time_machine.travel("2026-10-10 12:00Z", tick=False)
LATER = time_machine.travel("2026-10-10 12:05Z", tick=False)


@pytest.fixture
def crew():
    """An admin (Ana) and two members (Bogdan, Cristina), on 10 October 2026."""
    with OCT:
        admin = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=admin.crew, display_name="Cristina")
        yield admin, bogdan, cristina


# --- the shape -------------------------------------------------------------------------------


def test_shapes_are_normalized():
    shape = services.clean_shape(
        {**PUSHUPS, "title": "  50   push-ups ", "unit": " push-ups ", "rules": " ok "}
    )
    assert shape.title == "50 push-ups"
    assert shape.unit == "push-ups"
    assert shape.rules == "ok"
    assert (shape.window, shape.need_kind, shape.need_value, shape.day_min) == (
        "day",
        "count",
        1,
        Decimal("50"),
    )
    weekdays = services.clean_shape(NO_SUGAR)
    assert weekdays.on_days == 0b11111
    assert weekdays.unit == ""
    km = services.clean_shape(
        {"title": "Run", "measure": "quantity", "unit": "km", "window": "week"}
        | {"need_kind": "amount", "need_value": "50.5"}
    )
    assert (km.window, km.need_kind, km.need_value) == ("week", "amount", Decimal("50.5"))
    assert services.clean_shape({"title": "Read", "proof_required": True}).proof_required is True
    old_kind = services.clean_shape({"title": "Read", "proof_kind": "video"})  # no longer read
    assert old_kind.proof_required is False


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"title": "   "}, "title"),
        ({"icon": "rocket"}, "icon"),
        ({"unit": ""}, "unit"),
        ({"measure": "check"}, "day_min"),  # a minimum needs numbers
        ({"day_min": 0}, "day_min"),
        ({"day_min": "abc"}, "day_min"),
        ({"on_days": [7]}, "on_days"),
        ({"window": "week", "on_days": [0]}, "on_days"),  # chosen days only for day windows
        ({"need_value": 2}, "need_value"),  # a day asks for one check-in
        ({"window": "week", "need_value": 8}, "need_value"),
        ({"window": "week", "need_value": "2.5"}, "need_value"),
        ({"window": "period", "need_value": 32}, "need_value"),
        ({"window": "week", "need_kind": "amount", "need_value": 0, "day_min": None}, "need_value"),
        ({"need_kind": "amount", "need_value": 20, "day_min": None}, "need_kind"),  # per day
        (
            {"measure": "check", "window": "week", "need_kind": "amount", "day_min": None},
            "need_kind",
        ),
        ({"window": "week", "need_kind": "amount", "need_value": 20}, "day_min"),  # totals: no min
        ({"need_kind": "weight"}, "need_kind"),
        ({"measure": "dance"}, "measure"),
        ({"window": "hourly"}, "window"),
        ({"period_kind": "year"}, "period_kind"),
        ({"period_length": 13}, "period_length"),  # at most 12 months
        ({"period_kind": "week", "period_length": 53}, "period_length"),
        ({"period_kind": "day", "period_length": 0}, "period_length"),
        ({"period_kind": "day", "period_length": 5, "window": "week", "need_value": 2}, "window"),
        (
            {"period_kind": "day", "period_length": 10, "window": "period", "need_value": 11},
            "need_value",
        ),
        ({"window": "month", "need_value": 3, "period_kind": "week", "period_length": 4}, "window"),
        ({"window": "month", "need_value": 29, "period_length": 3}, "need_value"),  # Feb has 28
        ({"rules": "x" * 501}, "rules"),
    ],
)
def test_bad_shapes_name_the_field(change, field):
    with pytest.raises(ValidationFailed) as error:
        services.clean_shape({**PUSHUPS, **change})
    assert field in error.value.fields


# --- the pool ----------------------------------------------------------------------------------


def november(by):
    return {"by": by, "period_start": date(2026, 11, 1)}


def test_any_member_proposes_into_the_pool(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert proposal.created_by == bogdan
    assert proposal.state == "proposed"
    assert (proposal.period_kind, proposal.period_length) == ("month", 1)
    assert (proposal.period_start, proposal.start_date) == (None, None)
    assert (proposal.measure, proposal.unit, proposal.day_min) == (
        "quantity",
        "push-ups",
        Decimal("50"),
    )


def test_the_pool_is_newest_first_with_its_size_and_limit(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with LATER:
        second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    pool = selectors.pool(member=admin)
    assert pool.proposals == [second, first]
    assert (pool.size, pool.limit) == (2, 50)


def test_a_full_pool_refuses_new_proposals_until_a_place_frees_up(crew):
    admin, bogdan, cristina = crew
    admin.crew.max_proposals = 2
    admin.crew.save()
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    with pytest.raises(services.PoolFull):
        services.propose_challenge(by=bogdan, shape=PUSHUPS)

    services.withdraw_proposal(by=bogdan, challenge_id=first.pk)  # soft-deleted ones don't count
    third = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(
        challenge_id=second.pk, **november(admin)
    )  # scheduled ones don't count
    services.propose_challenge(by=cristina, shape=NO_SUGAR)

    # Putting one back is allowed even when the pool is full: it was there before.
    services.unschedule_challenge(by=admin, challenge_id=second.pk)
    assert selectors.pool(member=admin).size == 3
    with pytest.raises(services.PoolFull):
        services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert third.state == "proposed"


def test_lowering_the_limit_keeps_every_proposal(crew):
    admin, bogdan, _ = crew
    services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.propose_challenge(by=bogdan, shape=NO_SUGAR)
    admin.crew.max_proposals = 1
    admin.crew.save()
    assert selectors.pool(member=admin).size == 2
    with pytest.raises(services.PoolFull):
        services.propose_challenge(by=bogdan, shape=PUSHUPS)


def test_editing_resets_the_votes_and_only_the_creator_may(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    other = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    services.cast_vote(by=bogdan, challenge_id=other.pk)

    with pytest.raises(services.NotYourProposal):
        services.edit_proposal(by=admin, challenge_id=proposal.pk, shape=PUSHUPS)
    edited = services.edit_proposal(
        by=bogdan, challenge_id=proposal.pk, shape={**PUSHUPS, "day_min": 60}
    )
    assert edited.revision == 2
    assert edited.day_min == Decimal("60")
    assert not Vote.objects.filter(challenge=proposal).exists()
    assert Vote.objects.filter(challenge=other).count() == 1  # other proposals keep theirs


def punishment(text, proof=False):
    return {"text": text, "proof_required": proof}


TWO = [punishment(" 20 burpees ", proof=True), punishment("Cold shower")]


@pytest.mark.parametrize(("count", "ok"), [(0, True), (1, False), (2, True), (8, True), (9, False)])
def test_a_challenge_has_no_punishments_or_two_to_eight(count, ok):
    shape = {**PUSHUPS, "punishments": [punishment(f"Plank {n}") for n in range(count)]}
    if ok:
        assert len(services.clean_shape(shape).punishments) == count
    else:
        with pytest.raises(ValidationFailed) as error:
            services.clean_shape(shape)
        assert "punishments" in error.value.fields


@pytest.mark.parametrize(
    "punishments",
    [
        [punishment(""), punishment("Plank")],
        [punishment("x" * 81), punishment("Plank")],
        [punishment("Plank"), punishment(" plank ")],  # the same, ignoring case and spaces
    ],
)
def test_each_punishment_is_written_and_different(punishments):
    with pytest.raises(ValidationFailed) as error:
        services.clean_shape({**PUSHUPS, "punishments": punishments})
    assert "punishments" in error.value.fields


def test_punishments_are_kept_in_order_and_replaced_by_an_edit(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape={**PUSHUPS, "punishments": TWO})
    rows = list(Punishment.objects.filter(challenge=proposal))
    assert [(p.position, p.text, p.proof_required) for p in rows] == [
        (1, "20 burpees", True),
        (2, "Cold shower", False),
    ]
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    same = services.edit_proposal(
        by=bogdan, challenge_id=proposal.pk, shape={**PUSHUPS, "punishments": TWO}
    )
    assert same.revision == 1  # nothing changed: the votes stay
    assert Vote.objects.filter(challenge=proposal).count() == 1

    edited = services.edit_proposal(
        by=bogdan,
        challenge_id=proposal.pk,
        shape={**PUSHUPS, "punishments": [*TWO, punishment("Sing on video", proof=True)]},
    )
    assert edited.revision == 2
    assert not Vote.objects.filter(challenge=proposal).exists()
    assert Punishment.objects.filter(challenge=proposal).count() == 3
    services.edit_proposal(by=bogdan, challenge_id=proposal.pk, shape=PUSHUPS)
    assert not Punishment.objects.filter(challenge=proposal).exists()  # none is fine too


def test_the_database_keeps_positions_one_to_eight_and_unique(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape={**PUSHUPS, "punishments": TWO})
    for position in (9, 2):  # out of range, then taken
        with transaction.atomic(), pytest.raises(IntegrityError):
            Punishment.objects.create(
                crew=bogdan.crew, challenge=proposal, position=position, text="Plank"
            )


def test_withdrawing_is_a_soft_delete_by_the_creator_or_an_admin(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.cast_vote(by=cristina, challenge_id=proposal.pk)
    with pytest.raises(services.NotYourProposal):
        services.withdraw_proposal(by=cristina, challenge_id=proposal.pk)
    services.withdraw_proposal(by=bogdan, challenge_id=proposal.pk)
    assert not Challenge.objects.filter(pk=proposal.pk).exists()
    assert Challenge.all_objects.get(pk=proposal.pk).deleted_at is not None
    assert not Vote.objects.exists()
    assert selectors.pool(member=admin).proposals == []

    by_admin = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.withdraw_proposal(by=admin, challenge_id=by_admin.pk)
    with pytest.raises(services.ChallengeNotFound):
        services.withdraw_proposal(by=admin, challenge_id=by_admin.pk)


def test_a_scheduled_challenge_cannot_be_edited_withdrawn_or_voted_on(crew):
    admin, bogdan, _ = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    for action in (
        lambda: services.edit_proposal(by=bogdan, challenge_id=chosen.pk, shape=PUSHUPS),
        lambda: services.withdraw_proposal(by=bogdan, challenge_id=chosen.pk),
        lambda: services.cast_vote(by=bogdan, challenge_id=chosen.pk),
        lambda: services.clear_vote(by=bogdan, challenge_id=chosen.pk),
    ):
        with pytest.raises(services.NotAProposal):
            action()
    assert Punishment.objects.filter(challenge=chosen).count() == 0  # as proposed: none


def test_other_crews_cannot_see_or_touch_a_proposal(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    stranger = AdminFactory.create()
    for action in (
        lambda: services.cast_vote(by=stranger, challenge_id=proposal.pk),
        lambda: services.clear_vote(by=stranger, challenge_id=proposal.pk),
        lambda: services.edit_proposal(by=stranger, challenge_id=proposal.pk, shape=PUSHUPS),
        lambda: services.withdraw_proposal(by=stranger, challenge_id=proposal.pk),
        lambda: services.schedule_challenge(challenge_id=proposal.pk, **november(stranger)),
        lambda: services.unschedule_challenge(by=stranger, challenge_id=proposal.pk),
    ):
        with pytest.raises(services.ChallengeNotFound):
            action()
    assert selectors.get_challenge(member=stranger, challenge_id=proposal.pk) is None
    assert selectors.pool(member=stranger).proposals == []


# --- votes -------------------------------------------------------------------------------------


def test_members_vote_for_as_many_proposals_as_they_like_once_each(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.cast_vote(by=bogdan, challenge_id=first.pk)  # your own proposal is fine
    with LATER:
        services.cast_vote(by=cristina, challenge_id=first.pk)
        services.cast_vote(by=cristina, challenge_id=second.pk)
        services.cast_vote(by=cristina, challenge_id=second.pk)  # twice counts once

    tallies = selectors.tallies(challenges=[first, second])
    assert [m.display_name for m in tallies[first.pk].voters] == ["Bogdan", "Cristina"]
    assert tallies[second.pk].count == 1

    services.clear_vote(by=cristina, challenge_id=first.pk)
    services.clear_vote(by=cristina, challenge_id=first.pk)  # nothing to clear is fine
    assert selectors.tallies(challenges=[first])[first.pk].count == 1
    assert selectors.tallies(challenges=[]) == {}


def test_votes_for_withdrawn_proposals_are_refused(crew):
    _, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.withdraw_proposal(by=bogdan, challenge_id=proposal.pk)
    with pytest.raises(services.ChallengeNotFound):
        services.cast_vote(by=cristina, challenge_id=proposal.pk)


# --- scheduling ------------------------------------------------------------------------------


def test_only_admins_schedule(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(PermissionDenied):
        services.schedule_challenge(challenge_id=proposal.pk, **november(bogdan))
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    with pytest.raises(PermissionDenied):
        services.unschedule_challenge(by=bogdan, challenge_id=proposal.pk)


def test_scheduling_before_the_month_runs_the_whole_month_for_the_whole_crew(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    other = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.cast_vote(by=bogdan, challenge_id=chosen.pk)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))

    chosen.refresh_from_db()
    other.refresh_from_db()
    assert (chosen.state, chosen.period_kind, chosen.chosen_by) == ("chosen", "month", admin)
    assert chosen.chosen_at is not None
    assert (chosen.period_start, chosen.start_date, chosen.end_date) == (
        date(2026, 11, 1),
        date(2026, 11, 1),
        date(2026, 11, 30),
    )
    assert other.state == "proposed"  # the rest stay in the pool
    assert selectors.tallies(challenges=[chosen])[chosen.pk].count == 1  # votes stay as history
    assert names(chosen) == [
        "Ana",
        "Bogdan",
        "Cristina",
    ]
    assert selectors.phase(chosen, date(2026, 10, 31)) == "upcoming"
    assert selectors.phase(chosen, date(2026, 11, 1)) == "active"
    assert selectors.phase(chosen, date(2026, 12, 1)) == "finished"
    assert selectors.phase(other, date(2026, 11, 1)) is None


def test_several_challenges_can_run_in_the_same_month(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.schedule_challenge(challenge_id=first.pk, **november(admin))
    services.schedule_challenge(challenge_id=second.pk, **november(admin))
    upcoming = selectors.list_chosen(member=admin, phases=("upcoming",))
    assert upcoming == [first, second]  # same start: by title
    assert Participant.objects.count() == 6


def test_scheduling_the_same_period_twice_changes_nothing(crew):
    admin, bogdan, _ = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    services.stop_taking_part(by=bogdan, challenge_id=chosen.pk)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    assert Participant.objects.filter(challenge=chosen).count() == 2  # the opt-out stays


def test_moving_before_the_start_keeps_opt_outs_and_is_locked_after(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    services.stop_taking_part(by=cristina, challenge_id=chosen.pk)

    services.schedule_challenge(by=admin, challenge_id=chosen.pk, period_start=date(2027, 1, 1))
    chosen.refresh_from_db()
    assert (chosen.start_date, chosen.end_date) == (date(2027, 1, 1), date(2027, 1, 31))
    assert Participant.objects.filter(challenge=chosen).count() == 2  # Cristina stays out

    with time_machine.travel("2027-01-01 08:00Z", tick=False):
        with pytest.raises(services.ChallengeStarted):
            services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
        with pytest.raises(services.ChallengeStarted):
            services.unschedule_challenge(by=admin, challenge_id=chosen.pk)


def test_putting_back_in_the_pool_reopens_votes_and_keeps_participants(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.cast_vote(by=cristina, challenge_id=chosen.pk)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))

    back = services.unschedule_challenge(by=admin, challenge_id=chosen.pk)
    assert (back.state, back.period_start, back.start_date) == ("proposed", None, None)
    assert (back.period_kind, back.period_length) == ("month", 1)  # how long stays with it
    assert (back.end_date, back.chosen_by, back.chosen_at) == (None, None, None)
    assert Participant.objects.filter(challenge=chosen).count() == 3
    assert selectors.tallies(challenges=[chosen])[chosen.pk].count == 1
    services.cast_vote(by=admin, challenge_id=chosen.pk)  # voting is open again
    assert services.unschedule_challenge(by=admin, challenge_id=chosen.pk) == back  # no-op


def test_scheduling_late_starts_tomorrow_and_ends_with_the_month(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with time_machine.travel("2026-11-10 12:00Z", tick=False):
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    proposal.refresh_from_db()
    assert proposal.period_start == date(2026, 11, 1)
    assert (proposal.start_date, proposal.end_date) == (date(2026, 11, 11), date(2026, 11, 30))


def test_scheduling_on_the_last_day_or_for_a_past_month_is_too_late(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with time_machine.travel("2026-11-30 12:00Z", tick=False), pytest.raises(services.PeriodOver):
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    with pytest.raises(services.PeriodOver):
        services.schedule_challenge(
            by=admin, challenge_id=proposal.pk, period_start=date(2026, 9, 1)
        )


def test_the_last_day_follows_the_crew_time_zone(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    # 30 Oct 22:30 UTC is 31 October in Chisinau (UTC+2 after the DST switch on 25 October):
    # the last day of October, so October is over.
    with time_machine.travel("2026-10-30 22:30Z", tick=False):
        with pytest.raises(services.PeriodOver):
            services.schedule_challenge(
                by=admin,
                challenge_id=proposal.pk,
                period_start=date(2026, 10, 1),
            )
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    proposal.refresh_from_db()
    assert proposal.start_date == date(2026, 11, 1)


@pytest.mark.parametrize(
    ("period_start", "error"),
    [
        (date(2026, 11, 2), ValidationFailed),  # a month starts on the 1st
        (date(2027, 11, 1), services.PeriodTooFar),
    ],
)
def test_bad_periods_are_refused(crew, period_start, error):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(error):
        services.schedule_challenge(by=admin, challenge_id=proposal.pk, period_start=period_start)


def test_twelve_months_ahead_is_the_limit(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(by=admin, challenge_id=proposal.pk, period_start=date(2027, 10, 1))


def test_a_period_shorter_than_the_count_is_refused_and_a_late_start_asks_for_less(crew):
    admin, bogdan, _ = crew
    swim = services.propose_challenge(
        by=bogdan, shape={"title": "Swim", "window": "period", "need_value": 30}
    )
    with pytest.raises(services.TooFewDays):  # February 2027 has 28 days
        services.schedule_challenge(by=admin, challenge_id=swim.pk, period_start=date(2027, 2, 1))
    with time_machine.travel("2026-11-25 12:00Z", tick=False):  # 26-30 Nov: 5 of 30 days
        chosen = services.schedule_challenge(challenge_id=swim.pk, **november(admin))
    assert chosen.start_date is not None
    assert chosen.end_date is not None
    assert windows(chosen, chosen.start_date, chosen.end_date)[0].need == 5  # 30 x 5/30


# --- taking part ---------------------------------------------------------------------------


@pytest.fixture
def chosen(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    proposal.refresh_from_db()
    return proposal


def test_opting_out_before_the_start_removes_the_challenge_for_good(crew, chosen):
    _, _, cristina = crew
    services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
    assert not Participant.objects.filter(challenge=chosen, member=cristina).exists()
    assert selectors.get_challenge(member=cristina, challenge_id=chosen.pk) is None
    with pytest.raises(services.ChallengeNotFound):
        services.stop_taking_part(by=cristina, challenge_id=chosen.pk)


def test_leaving_a_running_challenge_hides_it_and_keeps_the_days_so_far(crew, chosen):
    _, bogdan, cristina = crew
    with time_machine.travel("2026-11-12 12:00Z", tick=False):
        services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
        assert selectors.get_challenge(member=cristina, challenge_id=chosen.pk) is None
        with pytest.raises(services.ChallengeNotFound):
            services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
    row = Participant.objects.get(challenge=chosen, member=cristina)
    assert row.left_on == date(2026, 11, 12)
    people = selectors.participants(challenges=[chosen])[chosen.pk]
    assert cristina in [p.member for p in people]  # the others still see her days
    with (
        time_machine.travel("2026-12-02 12:00Z", tick=False),
        pytest.raises(services.ChallengeFinished),
    ):
        services.stop_taking_part(by=bogdan, challenge_id=chosen.pk)


def test_proposals_have_no_participants(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(services.NotChosenYet):
        services.stop_taking_part(by=bogdan, challenge_id=proposal.pk)


def test_new_members_are_not_added_to_running_challenges(crew, chosen):
    admin, *_ = crew
    with time_machine.travel("2026-11-15 12:00Z", tick=False):
        invite = crews.create_invite(by=admin)
        newcomer = crews.accept_invite(
            code=invite.code, username="newbie", password="garden-flame-2026", display_name="Eva"
        )
    assert not Participant.objects.filter(challenge=chosen, member=newcomer).exists()
    assert selectors.get_challenge(member=newcomer, challenge_id=chosen.pk) is None


# --- who takes part ----------------------------------------------------------------------------


def names(challenge):
    people = selectors.participants(challenges=[challenge]).get(challenge.pk, [])
    return sorted(p.member.display_name for p in people)


def test_the_whole_crew_takes_part_by_default(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert names(proposal) == ["Ana", "Bogdan", "Cristina"]


def test_the_creator_chooses_who_takes_part_and_is_always_in(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS, participant_ids=[cristina.pk])
    assert names(proposal) == ["Bogdan", "Cristina"]
    services.set_participants(by=bogdan, challenge_id=proposal.pk, participant_ids=[])
    assert names(proposal) == ["Bogdan"]
    services.set_participants(
        by=bogdan, challenge_id=proposal.pk, participant_ids=[admin.pk, cristina.pk]
    )
    assert names(proposal) == ["Ana", "Bogdan", "Cristina"]


def test_only_crew_members_can_take_part(crew):
    _, bogdan, _ = crew
    stranger = MemberFactory.create()
    with pytest.raises(ValidationFailed) as error:
        services.propose_challenge(by=bogdan, shape=PUSHUPS, participant_ids=[stranger.pk])
    assert "participant_ids" in error.value.fields


def test_only_the_creator_changes_who_takes_part_and_only_before_scheduling(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(services.NotYourProposal):
        services.set_participants(by=cristina, challenge_id=proposal.pk, participant_ids=[])
    with pytest.raises(services.NotYourProposal):
        services.set_participants(by=admin, challenge_id=proposal.pk, participant_ids=[])
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    with pytest.raises(services.NotAProposal):
        services.set_participants(by=bogdan, challenge_id=proposal.pk, participant_ids=[])


def test_removing_someone_deletes_only_their_vote(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    services.cast_vote(by=cristina, challenge_id=proposal.pk)
    services.set_participants(by=bogdan, challenge_id=proposal.pk, participant_ids=[admin.pk])
    assert [v.member for v in Vote.objects.filter(challenge=proposal)] == [admin]


def test_editing_only_who_takes_part_keeps_the_other_votes(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    services.cast_vote(by=cristina, challenge_id=proposal.pk)
    same = services.edit_proposal(
        by=bogdan, challenge_id=proposal.pk, shape=PUSHUPS, participant_ids=[admin.pk]
    )
    assert same.revision == 1
    assert [v.member for v in Vote.objects.filter(challenge=proposal)] == [admin]
    kept = services.edit_proposal(by=bogdan, challenge_id=proposal.pk, shape=PUSHUPS)
    assert names(kept) == ["Ana", "Bogdan"]  # participant_ids=None keeps the list


def test_only_participants_and_admins_see_a_challenge(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS, participant_ids=[])
    assert selectors.get_challenge(member=bogdan, challenge_id=proposal.pk) == proposal
    assert selectors.get_challenge(member=admin, challenge_id=proposal.pk) == proposal
    assert selectors.get_challenge(member=cristina, challenge_id=proposal.pk) is None
    assert selectors.pool(member=cristina).proposals == []
    assert selectors.pool(member=cristina).size == 1  # the limit counts the whole crew's pool
    for action in (
        lambda: services.cast_vote(by=cristina, challenge_id=proposal.pk),
        lambda: services.clear_vote(by=cristina, challenge_id=proposal.pk),
        lambda: services.withdraw_proposal(by=cristina, challenge_id=proposal.pk),
    ):
        with pytest.raises(services.ChallengeNotFound):
            action()

    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    assert selectors.list_chosen(member=cristina) == []
    assert selectors.list_chosen(member=admin) == [proposal]
    with pytest.raises(services.ChallengeNotFound):
        services.stop_taking_part(by=cristina, challenge_id=proposal.pk)


def test_admins_who_do_not_take_part_choose_but_do_not_vote(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS, participant_ids=[])
    with pytest.raises(services.NotAParticipant):
        services.cast_vote(by=admin, challenge_id=proposal.pk)
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    assert names(proposal) == ["Bogdan"]
    with pytest.raises(services.ChallengeNotFound):
        services.stop_taking_part(by=admin, challenge_id=proposal.pk)


def test_moving_and_putting_back_keep_the_participants(crew):
    admin, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS, participant_ids=[cristina.pk])
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    services.schedule_challenge(by=admin, challenge_id=proposal.pk, period_start=date(2026, 12, 1))
    assert names(proposal) == ["Bogdan", "Cristina"]
    services.unschedule_challenge(by=admin, challenge_id=proposal.pk)
    assert names(proposal) == ["Bogdan", "Cristina"]


WEEKLY = {
    "title": "Run",
    "window": "week",
    "need_value": 3,
    "period_kind": "week",
    "period_length": 4,
}


def test_weeks_start_on_a_monday_and_run_their_length(crew):
    admin, bogdan, _ = crew
    run = services.propose_challenge(by=bogdan, shape=WEEKLY)
    with pytest.raises(ValidationFailed):
        services.schedule_challenge(by=admin, challenge_id=run.pk, period_start=date(2026, 11, 3))
    chosen = services.schedule_challenge(
        by=admin, challenge_id=run.pk, period_start=date(2026, 11, 2)
    )
    assert (chosen.period_start, chosen.start_date, chosen.end_date) == (
        date(2026, 11, 2),
        date(2026, 11, 2),
        date(2026, 11, 29),
    )
    moved = services.schedule_challenge(
        by=admin, challenge_id=run.pk, period_start=date(2026, 11, 9)
    )
    assert (moved.end_date, moved.period_length) == (date(2026, 12, 6), 4)  # same length


def test_weeks_under_way_start_tomorrow(crew):
    admin, bogdan, _ = crew
    run = services.propose_challenge(by=bogdan, shape=WEEKLY)
    with time_machine.travel("2026-11-04 12:00Z", tick=False):  # a Wednesday
        chosen = services.schedule_challenge(
            by=admin, challenge_id=run.pk, period_start=date(2026, 11, 2)
        )
    assert (chosen.period_start, chosen.start_date) == (date(2026, 11, 2), date(2026, 11, 5))


def test_a_number_of_days_starts_any_day_from_tomorrow(crew):
    admin, bogdan, _ = crew
    swim = services.propose_challenge(
        by=bogdan,
        shape={"title": "Swim", "window": "period", "need_value": 8, "period_kind": "day"}
        | {"period_length": 21},
    )
    with pytest.raises(ValidationFailed):  # today is the 10th
        services.schedule_challenge(by=admin, challenge_id=swim.pk, period_start=date(2026, 10, 10))
    chosen = services.schedule_challenge(
        by=admin, challenge_id=swim.pk, period_start=date(2026, 10, 17)
    )
    assert (chosen.start_date, chosen.end_date) == (date(2026, 10, 17), date(2026, 11, 6))


def test_several_months_end_with_the_last_month(crew):
    admin, bogdan, _ = crew
    cook = services.propose_challenge(by=bogdan, shape={"title": "Cook", "period_length": 3})
    chosen = services.schedule_challenge(challenge_id=cook.pk, **november(admin))
    assert chosen.end_date == date(2027, 1, 31)


@pytest.mark.parametrize(
    ("kind", "start", "length", "end"),
    [
        ("month", date(2026, 10, 1), 1, date(2026, 10, 31)),
        ("month", date(2026, 12, 1), 2, date(2027, 1, 31)),
        ("month", date(2027, 2, 1), 1, date(2027, 2, 28)),
        ("week", date(2026, 11, 2), 4, date(2026, 11, 29)),
        ("day", date(2026, 10, 10), 21, date(2026, 10, 30)),
    ],
)
def test_period_ends(kind, start, length, end):
    assert periods.period_end(kind, start, length) == end
    with pytest.raises(ValueError, match="Unknown period kind"):
        periods.period_end("", start, length)


# --- lists -----------------------------------------------------------------------------------


def test_lists_by_phase(crew, chosen):
    admin, *_ = crew
    with time_machine.travel("2026-11-05 12:00Z", tick=False):
        assert selectors.list_chosen(member=admin, phases=("active",)) == [chosen]
        assert selectors.list_chosen(member=admin, phases=("upcoming",)) == []
    assert selectors.list_chosen(member=admin) == [chosen]
    assert selectors.pool(member=admin).proposals == []


def test_periods_add_months_across_years():
    from apps.challenges import periods

    assert periods.add_months(date(2026, 11, 1), 2) == date(2027, 1, 1)
    assert periods.add_months(date(2026, 1, 1), 12) == date(2027, 1, 1)


def test_factories_build_a_proposal():
    from tests.factories import ChallengeFactory

    proposal = ChallengeFactory.create()
    assert proposal.created_by is not None
    assert proposal.crew == proposal.created_by.crew
    assert proposal.state == "proposed"


def test_the_database_wants_a_period_kind_and_months_for_a_monthly_window(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    rows = Challenge.objects.filter(pk=proposal.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        rows.update(period_kind="")
    with pytest.raises(IntegrityError), transaction.atomic():
        rows.update(window="month", period_kind="week")
    cook = services.propose_challenge(
        by=bogdan, shape={"title": "Cook", "window": "month", "need_value": 4, "period_length": 3}
    )
    assert (cook.window, cook.period_kind, cook.period_length) == ("month", "month", 3)
