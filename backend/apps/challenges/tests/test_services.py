from datetime import date
from decimal import Decimal

import pytest
import time_machine

from apps.challenges import selectors, services
from apps.challenges.models import Challenge, Participation, Vote
from apps.core.errors import PermissionDenied, ValidationFailed
from apps.crews import services as crews
from tests.factories import AdminFactory, InviteFactory, MemberFactory

pytestmark = pytest.mark.django_db

PUSHUPS = {
    "title": "50 push-ups a day",
    "icon": "dumbbell",
    "measure": "quantity",
    "unit": "push-ups",
    "frequency": "daily",
    "target_scope": "per_check_in",
    "target_value": 50,
    "proof_kind": "video",
    "proof_required": True,
}
NO_SUGAR = {
    "title": "No sugar on weekdays",
    "measure": "abstain",
    "frequency": "weekdays",
    "weekdays": [0, 1, 2, 3, 4],
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
    assert shape.target_value == Decimal("50")
    weekdays = services.clean_shape(NO_SUGAR)
    assert weekdays.weekdays == 0b11111
    assert weekdays.unit == ""
    no_proof = services.clean_shape({"title": "Read", "proof_kind": "none", "proof_required": True})
    assert no_proof.proof_required is False


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"title": "   "}, "title"),
        ({"icon": "rocket"}, "icon"),
        ({"unit": ""}, "unit"),
        ({"measure": "check"}, "target_scope"),
        ({"target_value": 0}, "target_value"),
        ({"target_value": "abc"}, "target_value"),
        ({"frequency": "weekdays", "weekdays": []}, "weekdays"),
        ({"frequency": "weekdays", "weekdays": [7]}, "weekdays"),
        ({"frequency": "times_per_week", "times": 8}, "times"),
        ({"frequency": "times_per_period", "times": None}, "times"),
        ({"proof_kind": "audio"}, "proof_kind"),
        ({"measure": "dance"}, "measure"),
        ({"frequency": "hourly"}, "frequency"),
        ({"target_scope": "per_year"}, "target_scope"),
        ({"rules": "x" * 501}, "rules"),
    ],
)
def test_bad_shapes_name_the_field(change, field):
    with pytest.raises(ValidationFailed) as error:
        services.clean_shape({**PUSHUPS, **change})
    assert field in error.value.fields


# --- the pool ----------------------------------------------------------------------------------


def november(by):
    return {"by": by, "period_kind": "month", "period_start": date(2026, 11, 1)}


def test_any_member_proposes_into_the_pool(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert proposal.created_by == bogdan
    assert proposal.state == "proposed"
    assert (proposal.period_kind, proposal.period_start, proposal.start_date) == ("", None, None)
    assert (proposal.measure, proposal.unit, proposal.target_value) == (
        "quantity",
        "push-ups",
        Decimal("50"),
    )


def test_the_pool_is_newest_first_with_its_size_and_limit(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with LATER:
        second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    pool = selectors.pool(crew=admin.crew)
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
    assert selectors.pool(crew=admin.crew).size == 3
    with pytest.raises(services.PoolFull):
        services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert third.state == "proposed"


def test_lowering_the_limit_keeps_every_proposal(crew):
    admin, bogdan, _ = crew
    services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.propose_challenge(by=bogdan, shape=NO_SUGAR)
    admin.crew.max_proposals = 1
    admin.crew.save()
    assert selectors.pool(crew=admin.crew).size == 2
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
        by=bogdan, challenge_id=proposal.pk, shape={**PUSHUPS, "target_value": 60}
    )
    assert edited.revision == 2
    assert edited.target_value == Decimal("60")
    assert not Vote.objects.filter(challenge=proposal).exists()
    assert Vote.objects.filter(challenge=other).count() == 1  # other proposals keep theirs


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
    assert selectors.pool(crew=admin.crew).proposals == []

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
    assert selectors.get_challenge(crew=stranger.crew, challenge_id=proposal.pk) is None
    assert selectors.pool(crew=stranger.crew).proposals == []


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
    assert sorted(p.member.display_name for p in selectors.participants(challenge=chosen)) == [
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
    upcoming = selectors.list_chosen(crew=admin.crew, phases=("upcoming",))
    assert upcoming == [first, second]  # same start: by title
    assert Participation.objects.count() == 6


def test_scheduling_the_same_period_twice_changes_nothing(crew):
    admin, bogdan, _ = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    services.stop_taking_part(by=bogdan, challenge_id=chosen.pk)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    assert Participation.objects.filter(challenge=chosen).count() == 2  # the opt-out stays


def test_moving_before_the_start_resets_opt_outs_and_is_locked_after(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
    services.stop_taking_part(by=cristina, challenge_id=chosen.pk)

    services.schedule_challenge(
        by=admin, challenge_id=chosen.pk, period_kind="month", period_start=date(2027, 1, 1)
    )
    chosen.refresh_from_db()
    assert (chosen.start_date, chosen.end_date) == (date(2027, 1, 1), date(2027, 1, 31))
    assert {p.joined_on for p in Participation.objects.filter(challenge=chosen)} == {
        date(2027, 1, 1)
    }
    assert Participation.objects.filter(challenge=chosen).count() == 3

    with time_machine.travel("2027-01-01 08:00Z", tick=False):
        with pytest.raises(services.ChallengeStarted):
            services.schedule_challenge(challenge_id=chosen.pk, **november(admin))
        with pytest.raises(services.ChallengeStarted):
            services.unschedule_challenge(by=admin, challenge_id=chosen.pk)


def test_putting_back_in_the_pool_reopens_votes_and_removes_participants(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.cast_vote(by=cristina, challenge_id=chosen.pk)
    services.schedule_challenge(challenge_id=chosen.pk, **november(admin))

    back = services.unschedule_challenge(by=admin, challenge_id=chosen.pk)
    assert (back.state, back.period_kind, back.period_start, back.start_date) == (
        "proposed",
        "",
        None,
        None,
    )
    assert (back.end_date, back.chosen_by, back.chosen_at) == (None, None, None)
    assert not Participation.objects.filter(challenge=chosen).exists()
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
    assert {p.joined_on for p in Participation.objects.filter(challenge=proposal)} == {
        date(2026, 11, 11)
    }


def test_scheduling_on_the_last_day_or_for_a_past_month_is_too_late(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with time_machine.travel("2026-11-30 12:00Z", tick=False), pytest.raises(services.PeriodOver):
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    with pytest.raises(services.PeriodOver):
        services.schedule_challenge(
            by=admin, challenge_id=proposal.pk, period_kind="month", period_start=date(2026, 9, 1)
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
                period_kind="month",
                period_start=date(2026, 10, 1),
            )
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    proposal.refresh_from_db()
    assert proposal.start_date == date(2026, 11, 1)


@pytest.mark.parametrize(
    ("period_kind", "period_start", "error"),
    [
        ("week", date(2026, 11, 2), services.PeriodKindNotAvailable),
        ("month", date(2026, 11, 2), ValidationFailed),
        ("month", date(2027, 11, 1), services.PeriodTooFar),
    ],
)
def test_bad_periods_are_refused(crew, period_kind, period_start, error):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(error):
        services.schedule_challenge(
            by=admin, challenge_id=proposal.pk, period_kind=period_kind, period_start=period_start
        )


def test_twelve_months_ahead_is_the_limit(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(
        by=admin, challenge_id=proposal.pk, period_kind="month", period_start=date(2027, 10, 1)
    )


def test_a_late_start_with_too_few_days_for_the_times_is_refused(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(
        by=bogdan, shape={"title": "Swim", "frequency": "times_per_period", "times": 10}
    )
    with (
        time_machine.travel("2026-11-25 12:00Z", tick=False),
        pytest.raises(services.TooFewDays),
    ):
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    with time_machine.travel("2026-11-19 12:00Z", tick=False):  # 20 Nov - 30 Nov: 11 days
        services.schedule_challenge(challenge_id=proposal.pk, **november(admin))


# --- taking part ---------------------------------------------------------------------------


@pytest.fixture
def chosen(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.schedule_challenge(challenge_id=proposal.pk, **november(admin))
    proposal.refresh_from_db()
    return proposal


def test_opting_out_and_back_in_before_the_start(crew, chosen):
    _, _, cristina = crew
    services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
    services.stop_taking_part(by=cristina, challenge_id=chosen.pk)  # twice is fine
    assert not Participation.objects.filter(challenge=chosen, member=cristina).exists()
    participation = services.take_part(by=cristina, challenge_id=chosen.pk)
    assert participation.joined_on == date(2026, 11, 1)


def test_leaving_a_running_challenge_keeps_the_days_so_far(crew, chosen):
    _, _, cristina = crew
    with time_machine.travel("2026-11-12 12:00Z", tick=False):
        services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
        services.stop_taking_part(by=cristina, challenge_id=chosen.pk)
        with pytest.raises(services.ChallengeStarted):
            services.take_part(by=cristina, challenge_id=chosen.pk)
    participation = Participation.objects.get(challenge=chosen, member=cristina)
    assert participation.ended_on == date(2026, 11, 12)
    with (
        time_machine.travel("2026-12-02 12:00Z", tick=False),
        pytest.raises(services.ChallengeFinished),
    ):
        services.stop_taking_part(by=cristina, challenge_id=chosen.pk)


def test_proposals_have_no_participants(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(services.NotChosenYet):
        services.take_part(by=bogdan, challenge_id=proposal.pk)
    with pytest.raises(services.NotChosenYet):
        services.stop_taking_part(by=bogdan, challenge_id=proposal.pk)


def test_new_members_join_upcoming_and_running_challenges(crew, chosen):
    admin, *_ = crew
    with time_machine.travel("2026-11-15 12:00Z", tick=False):
        invite = crews.create_invite(by=admin)
        newcomer = crews.accept_invite(
            code=invite.code, username="newbie", password="garden-flame-2026", display_name="Eva"
        )
    participation = Participation.objects.get(challenge=chosen, member=newcomer)
    assert participation.joined_on == date(2026, 11, 15)

    with time_machine.travel("2026-12-02 12:00Z", tick=False):
        late = crews.accept_invite(
            code=InviteFactory.create(created_by=admin).code,
            username="late1",
            password="garden-flame-2026",
            display_name="Late",
        )
    assert not Participation.objects.filter(challenge=chosen, member=late).exists()


# --- lists -----------------------------------------------------------------------------------


def test_lists_by_phase(crew, chosen):
    admin, *_ = crew
    with time_machine.travel("2026-11-05 12:00Z", tick=False):
        assert selectors.list_chosen(crew=admin.crew, phases=("active",)) == [chosen]
        assert selectors.list_chosen(crew=admin.crew, phases=("upcoming",)) == []
    assert selectors.list_chosen(crew=admin.crew) == [chosen]
    assert selectors.pool(crew=admin.crew).proposals == []


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
