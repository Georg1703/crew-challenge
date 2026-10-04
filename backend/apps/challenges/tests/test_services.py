from datetime import date
from decimal import Decimal

import pytest
import time_machine

from apps.challenges import selectors, services
from apps.challenges.models import Challenge, Participation, Round, Vote
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


@pytest.fixture
def crew():
    """An admin (Ana) and two members (Bogdan, Cristina), on 10 October 2026."""
    with OCT:
        admin = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=admin.crew, display_name="Cristina")
        yield admin, bogdan, cristina


# --- rounds ------------------------------------------------------------------------------------


def test_the_open_round_is_next_month_and_created_once(crew):
    admin, *_ = crew
    first = services.open_round(crew=admin.crew)
    assert (first.period_start, first.period_end) == (date(2026, 11, 1), date(2026, 11, 30))
    assert first.period_kind == "month"
    assert first.selection == "admin"
    assert services.open_round(crew=admin.crew) == first
    assert Round.objects.count() == 1


def test_the_round_follows_the_crew_time_zone(crew):
    admin, *_ = crew
    # 31 Oct 22:30 UTC is already 1 November in Chisinau (UTC+2 in winter).
    with time_machine.travel("2026-10-31 22:30Z", tick=False):
        assert services.open_round(crew=admin.crew).period_start == date(2026, 12, 1)


def test_a_round_nobody_chose_stays_open_into_its_month(crew):
    admin, *_ = crew
    november = services.open_round(crew=admin.crew)
    with time_machine.travel("2026-11-03 12:00Z", tick=False):
        assert services.open_round(crew=admin.crew) == november


def test_after_choosing_people_propose_for_the_month_after(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.choose_challenge(by=admin, challenge_id=proposal.pk)
    assert services.open_round(crew=admin.crew).period_start == date(2026, 12, 1)
    later = services.propose_challenge(by=bogdan, shape=NO_SUGAR)
    assert later.round.period_start == date(2026, 12, 1)


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


# --- proposals ---------------------------------------------------------------------------------


def test_any_member_proposes(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    assert proposal.created_by == bogdan
    assert proposal.state == "proposed"
    assert proposal.round.period_start == date(2026, 11, 1)
    assert (proposal.measure, proposal.unit, proposal.target_value) == (
        "quantity",
        "push-ups",
        Decimal("50"),
    )


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

    by_admin = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.withdraw_proposal(by=admin, challenge_id=by_admin.pk)
    with pytest.raises(services.ChallengeNotFound):
        services.withdraw_proposal(by=admin, challenge_id=by_admin.pk)


def test_nothing_changes_once_the_round_is_closed(crew):
    admin, bogdan, _ = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    other = services.propose_challenge(by=bogdan, shape=NO_SUGAR)
    services.choose_challenge(by=admin, challenge_id=chosen.pk)
    for challenge in (chosen, other):
        with pytest.raises(services.RoundClosed):
            services.edit_proposal(by=bogdan, challenge_id=challenge.pk, shape=PUSHUPS)
        with pytest.raises(services.RoundClosed):
            services.withdraw_proposal(by=bogdan, challenge_id=challenge.pk)
        with pytest.raises(services.RoundClosed):
            services.cast_vote(by=bogdan, challenge_id=challenge.pk)
    with pytest.raises(services.RoundClosed):
        services.clear_vote(by=bogdan, round_id=chosen.round_id)


def test_other_crews_cannot_see_or_touch_a_proposal(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    stranger = AdminFactory.create()
    for action in (
        lambda: services.cast_vote(by=stranger, challenge_id=proposal.pk),
        lambda: services.edit_proposal(by=stranger, challenge_id=proposal.pk, shape=PUSHUPS),
        lambda: services.withdraw_proposal(by=stranger, challenge_id=proposal.pk),
        lambda: services.choose_challenge(by=stranger, challenge_id=proposal.pk),
    ):
        with pytest.raises(services.ChallengeNotFound):
            action()
    assert selectors.get_challenge(crew=stranger.crew, challenge_id=proposal.pk) is None


# --- votes -------------------------------------------------------------------------------------


def test_one_vote_per_member_that_can_change(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.cast_vote(by=bogdan, challenge_id=first.pk)  # your own proposal is fine
    services.cast_vote(by=cristina, challenge_id=first.pk)
    services.cast_vote(by=cristina, challenge_id=second.pk)
    view = selectors.round_view(round_=first.round, member=cristina)
    assert view.my_vote == second.pk
    assert view.tallies[first.pk].count == 1
    assert [m.display_name for m in view.tallies[first.pk].voters] == ["Bogdan"]
    assert view.tallies[second.pk].count == 1

    services.clear_vote(by=cristina, round_id=first.round_id)
    assert selectors.round_view(round_=first.round, member=cristina).my_vote is None


def test_votes_for_withdrawn_proposals_are_refused(crew):
    _, bogdan, cristina = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.withdraw_proposal(by=bogdan, challenge_id=proposal.pk)
    with pytest.raises(services.ChallengeNotFound):
        services.cast_vote(by=cristina, challenge_id=proposal.pk)


# --- choosing --------------------------------------------------------------------------------


def test_only_admins_choose(crew):
    _, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with pytest.raises(PermissionDenied):
        services.choose_challenge(by=bogdan, challenge_id=proposal.pk)


def test_choosing_before_the_month_runs_the_whole_month_for_the_whole_crew(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    other = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.cast_vote(by=bogdan, challenge_id=other.pk)  # votes guide, the admin decides
    round_ = services.choose_challenge(by=admin, challenge_id=chosen.pk)

    chosen.refresh_from_db()
    other.refresh_from_db()
    assert (round_.state, round_.chosen, round_.chosen_by) == ("closed", chosen, admin)
    assert (chosen.state, chosen.start_date, chosen.end_date) == (
        "chosen",
        date(2026, 11, 1),
        date(2026, 11, 30),
    )
    assert other.state == "not_chosen"
    assert sorted(p.member.display_name for p in selectors.participants(challenge=chosen)) == [
        "Ana",
        "Bogdan",
        "Cristina",
    ]
    assert selectors.phase(chosen, date(2026, 10, 31)) == "upcoming"
    assert selectors.phase(chosen, date(2026, 11, 1)) == "active"
    assert selectors.phase(chosen, date(2026, 12, 1)) == "finished"
    assert selectors.phase(other, date(2026, 11, 1)) is None


def test_choosing_the_same_challenge_twice_changes_nothing(crew):
    admin, bogdan, _ = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.choose_challenge(by=admin, challenge_id=chosen.pk)
    services.choose_challenge(by=admin, challenge_id=chosen.pk)
    assert Participation.objects.filter(challenge=chosen).count() == 3


def test_admins_can_change_the_choice_until_the_start(crew):
    admin, bogdan, cristina = crew
    first = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    second = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.choose_challenge(by=admin, challenge_id=first.pk)
    services.stop_taking_part(by=cristina, challenge_id=first.pk)

    round_ = services.choose_challenge(by=admin, challenge_id=second.pk)
    first.refresh_from_db()
    assert round_.chosen == second
    assert (first.state, first.start_date) == ("not_chosen", None)
    assert not Participation.objects.filter(challenge=first).exists()
    assert Participation.objects.filter(challenge=second).count() == 3  # opt-outs start over

    with (
        time_machine.travel("2026-11-01 08:00Z", tick=False),
        pytest.raises(services.ChallengeStarted),
    ):
        services.choose_challenge(by=admin, challenge_id=first.pk)


def test_choosing_late_starts_tomorrow_and_ends_with_the_month(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with time_machine.travel("2026-11-10 12:00Z", tick=False):
        services.choose_challenge(by=admin, challenge_id=proposal.pk)
    proposal.refresh_from_db()
    assert (proposal.start_date, proposal.end_date) == (date(2026, 11, 11), date(2026, 11, 30))
    assert {p.joined_on for p in Participation.objects.filter(challenge=proposal)} == {
        date(2026, 11, 11)
    }


def test_choosing_on_the_last_day_is_too_late(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    with time_machine.travel("2026-11-30 12:00Z", tick=False), pytest.raises(services.PeriodOver):
        services.choose_challenge(by=admin, challenge_id=proposal.pk)


# --- taking part ---------------------------------------------------------------------------


@pytest.fixture
def chosen(crew):
    admin, bogdan, _ = crew
    proposal = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    services.choose_challenge(by=admin, challenge_id=proposal.pk)
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


# --- proposing again -----------------------------------------------------------------------


def test_a_challenge_not_chosen_can_be_proposed_again(crew):
    admin, bogdan, cristina = crew
    chosen = services.propose_challenge(by=bogdan, shape=PUSHUPS)
    lost = services.propose_challenge(by=cristina, shape=NO_SUGAR)
    services.choose_challenge(by=admin, challenge_id=chosen.pk)

    copy = services.repropose(by=admin, challenge_id=lost.pk)
    assert copy.pk != lost.pk
    assert copy.round.period_start == date(2026, 12, 1)
    assert (copy.title, copy.weekdays, copy.created_by) == (lost.title, lost.weekdays, admin)
    assert copy.state == "proposed"
    with pytest.raises(Exception, match="not chosen"):
        services.repropose(by=admin, challenge_id=copy.pk)


# --- lists -----------------------------------------------------------------------------------


def test_lists_by_phase(crew, chosen):
    admin, *_ = crew
    with time_machine.travel("2026-11-05 12:00Z", tick=False):
        assert selectors.list_chosen(crew=admin.crew, phases=("active",)) == [chosen]
        assert selectors.list_chosen(crew=admin.crew, phases=("upcoming",)) == []
    assert selectors.list_chosen(crew=admin.crew) == [chosen]
    assert [r.chosen for r in selectors.list_closed_rounds(crew=admin.crew)] == [chosen]


def test_factories_build_a_proposal():
    from tests.factories import ChallengeFactory

    proposal = ChallengeFactory.create()
    assert proposal.created_by is not None
    assert proposal.round.crew == proposal.crew == proposal.created_by.crew
    assert proposal.state == "proposed"
