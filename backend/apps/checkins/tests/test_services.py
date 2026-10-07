from datetime import date
from decimal import Decimal

import pytest
import time_machine

from apps.challenges import services as challenges
from apps.checkins import selectors, services
from apps.checkins.days import DayState
from apps.checkins.models import CheckIn, CheckInEntry
from apps.core.errors import ValidationFailed
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

READ = {
    "title": "Read",
    "measure": "quantity",
    "unit": "pages",
    "day_min": 20,
}
WALK = {"title": "Walk"}
MONDAYS = {"title": "Gym", "on_days": [0]}

TUE = date(2026, 11, 10)  # a Tuesday


def at(moment: str):
    return time_machine.travel(moment, tick=False)


@pytest.fixture
def crew():
    """Ana (admin), Bogdan, Cristina; on 10 October 2026."""
    with at("2026-10-10 12:00Z"):
        admin = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=admin.crew, display_name="Cristina")
        yield admin, bogdan, cristina


def november(admin, by, shape, participant_ids=None):
    """A challenge proposed by `by` and scheduled for November."""
    challenge = challenges.propose_challenge(by=by, shape=shape, participant_ids=participant_ids)
    challenges.schedule_challenge(
        by=admin, challenge_id=challenge.pk, period_kind="month", period_start=date(2026, 11, 1)
    )
    challenge.refresh_from_db()
    return challenge


def test_a_plain_check_in_counts_once(crew):
    admin, bogdan, _ = crew
    walk = november(admin, bogdan, WALK)
    with at("2026-11-10 08:00Z"):
        first = services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)
        again = services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)
    assert first == again
    assert first.status == CheckIn.Status.DONE
    assert first.amount is None
    assert CheckInEntry.objects.count() == 1


def test_numbers_add_up_and_count_once_the_target_is_reached(crew):
    admin, bogdan, _ = crew
    read = november(admin, bogdan, READ)
    with at("2026-11-10 08:00Z"):
        row = services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=Decimal(12))
        assert (row.amount, row.status) == (Decimal(12), CheckIn.Status.IN_PROGRESS)
        row = services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=Decimal(8))
        assert (row.amount, row.status) == (Decimal(20), CheckIn.Status.DONE)
        for bad in (None, Decimal(0), Decimal(-1), Decimal(1_000_001)):
            with pytest.raises(ValidationFailed):
                services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=bad)


def test_only_today_counts_in_the_crew_time_zone(crew):
    admin, bogdan, _ = crew
    walk = november(admin, bogdan, WALK)
    with at("2026-11-10 08:00Z"):
        for day in (date(2026, 11, 9), date(2026, 11, 11)):
            with pytest.raises(services.DayClosed):
                services.check_in(by=bogdan, challenge_id=walk.pk, day=day)
    # 21:59 UTC on 10 Nov is 23:59 in Chisinau; 22:01 UTC is already 11 Nov there.
    with at("2026-11-10 21:59Z"):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)
    with at("2026-11-10 22:01Z"), pytest.raises(services.DayClosed):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)


def test_only_participants_check_in_and_only_on_due_days(crew):
    admin, bogdan, cristina = crew
    walk = november(admin, bogdan, WALK, participant_ids=[cristina.pk])
    gym = november(admin, bogdan, MONDAYS)
    stranger = MemberFactory.create()
    with at("2026-11-10 08:00Z"):
        with pytest.raises(services.ChallengeNotFound):
            services.check_in(by=stranger, challenge_id=walk.pk, day=TUE)
        with pytest.raises(services.NotTakingPart):
            services.check_in(
                by=admin, challenge_id=walk.pk, day=TUE
            )  # sees it, does not take part
        with pytest.raises(services.NotDueToday):
            services.check_in(by=bogdan, challenge_id=gym.pk, day=TUE)
    with at("2026-11-12 08:00Z"):
        services.check_in(by=cristina, challenge_id=walk.pk, day=date(2026, 11, 12))
        challenges.stop_taking_part(by=cristina, challenge_id=walk.pk)  # leaves on Thursday
        with pytest.raises(services.ChallengeNotFound):  # gone for her at once
            services.check_in(by=cristina, challenge_id=walk.pk, day=date(2026, 11, 12))
    with at("2026-11-13 08:00Z"):
        board = selectors.board(member=bogdan, challenge_id=walk.pk, month=date(2026, 11, 1))
        assert board is not None
        row = next(r for r in board.rows if r.member == cristina)
        assert row.states[11:13] == ["done", "outside"]  # her Thursday counts, then she is out


def test_a_challenge_that_has_not_started_has_no_check_ins(crew):
    admin, bogdan, _ = crew
    walk = november(admin, bogdan, WALK)
    with at("2026-10-20 08:00Z"), pytest.raises(services.NotTakingPart):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=date(2026, 10, 20))


def test_undo_removes_the_last_entry_then_the_check_in(crew):
    admin, bogdan, _ = crew
    read = november(admin, bogdan, READ)
    with at("2026-11-10 08:00Z"):
        services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=Decimal(12))
        services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=Decimal(8))
        row = services.undo_last(by=bogdan, challenge_id=read.pk, day=TUE)
        assert row is not None
        assert (row.amount, row.status) == (Decimal(12), CheckIn.Status.IN_PROGRESS)
        assert services.undo_last(by=bogdan, challenge_id=read.pk, day=TUE) is None
        assert not CheckIn.objects.exists()
        with pytest.raises(services.NothingToUndo):
            services.undo_last(by=bogdan, challenge_id=read.pk, day=TUE)
    with at("2026-11-11 08:00Z"), pytest.raises(services.DayClosed):
        services.undo_last(by=bogdan, challenge_id=read.pk, day=TUE)


def test_today_has_my_cards_and_the_crew(crew):
    admin, bogdan, cristina = crew
    walk = november(admin, bogdan, WALK)
    read = november(admin, bogdan, READ)
    november(admin, bogdan, MONDAYS)  # not due on a Tuesday: no ring segment
    secret = november(admin, cristina, WALK, participant_ids=[])  # only Cristina sees it
    with at("2026-11-09 08:00Z"):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=date(2026, 11, 9))
    with at("2026-11-10 08:00Z"):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)
        services.check_in(by=bogdan, challenge_id=read.pk, day=TUE, amount=Decimal(5))
        services.check_in(by=cristina, challenge_id=secret.pk, day=TUE)
        today = selectors.today(member=bogdan)

    assert today.day == TUE
    assert today.deadline.isoformat() == "2026-11-10T22:00:00+00:00"
    cards = {c.challenge.title: c for c in today.cards}
    assert set(cards) == {"Walk", "Read", "Gym"}
    assert (cards["Walk"].state, cards["Walk"].streak, cards["Walk"].settled) == ("done", 2, True)
    assert (cards["Read"].state, cards["Read"].total) == (DayState.PARTIAL, Decimal(5))
    assert cards["Gym"].settled is None
    assert [s for _, s in cards["Walk"].week][:3] == ["done", "done", "future"]  # Mon 9 - Wed 11
    crew_row = {r.member.display_name: (r.done, r.needed) for r in today.crew}
    # Bogdan sees Cristina only on the challenges he can see (not her secret one).
    assert crew_row == {"Ana": (0, 2), "Bogdan": (1, 2), "Cristina": (0, 2)}


def test_the_month_board(crew):
    admin, bogdan, cristina = crew
    walk = november(admin, bogdan, WALK)
    with at("2026-11-12 08:00Z"):
        challenges.stop_taking_part(by=cristina, challenge_id=walk.pk)
    with at("2026-11-10 08:00Z"):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=TUE)
        board = selectors.board(member=bogdan, challenge_id=walk.pk, month=date(2026, 11, 1))
        assert selectors.board(member=bogdan, challenge_id=walk.pk, month=date(2026, 12, 5))
    assert board is not None
    assert len(board.days) == 30
    rows = {r.member.display_name: r.states for r in board.rows}
    assert rows["Bogdan"][8:11] == ["missed", "done", "future"]
    assert rows["Cristina"][12] == "outside"  # left on the 12th
    stranger = AdminFactory.create()
    assert selectors.board(member=stranger, challenge_id=walk.pk, month=TUE) is None
    proposal = challenges.propose_challenge(by=bogdan, shape=WALK)
    assert selectors.board(member=bogdan, challenge_id=proposal.pk, month=TUE) is None


def test_card_is_none_when_not_taking_part_today(crew):
    admin, bogdan, _ = crew
    walk = november(admin, bogdan, WALK)
    with at("2026-10-20 08:00Z"):
        assert selectors.card(member=bogdan, challenge_id=walk.pk) is None


def test_the_25_hour_day_when_clocks_go_back(crew):
    admin, bogdan, _ = crew
    with at("2026-10-20 08:00Z"):
        walk = challenges.propose_challenge(by=bogdan, shape=WALK)
        challenges.schedule_challenge(  # chosen late: runs 21-31 October
            by=admin, challenge_id=walk.pk, period_kind="month", period_start=date(2026, 10, 1)
        )
    sunday = date(2026, 10, 25)  # Chisinau goes from UTC+3 to UTC+2 at 04:00 local
    with at("2026-10-25 21:30Z"):  # 23:30 local, still Sunday
        services.check_in(by=bogdan, challenge_id=walk.pk, day=sunday)
        today = selectors.today(member=bogdan)
    assert today.deadline.isoformat() == "2026-10-25T22:00:00+00:00"
    with at("2026-10-25 22:00Z"), pytest.raises(services.DayClosed):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=sunday)


def test_a_day_is_missed_from_local_midnight_also_when_the_clocks_go_back(crew):
    admin, bogdan, _ = crew
    walk = challenges.propose_challenge(by=bogdan, shape=WALK, participant_ids=None)
    challenges.schedule_challenge(  # October is under way: it starts tomorrow, the 11th
        by=admin, challenge_id=walk.pk, period_kind="month", period_start=date(2026, 10, 1)
    )
    with at("2026-10-24 12:00Z"):
        services.check_in(by=bogdan, challenge_id=walk.pk, day=date(2026, 10, 24))

    def today_and_streak(moment: str) -> tuple[date, int | None]:
        with at(moment):
            now = selectors.today(member=bogdan)
            return now.day, now.cards[0].streak

    # Summer time (UTC+3) until 04:00 on Sunday the 25th, then UTC+2.
    assert today_and_streak("2026-10-24 20:59Z") == (date(2026, 10, 24), 1)  # 23:59 on the 24th
    assert today_and_streak("2026-10-24 21:01Z") == (date(2026, 10, 25), 1)  # 00:01: still open
    assert today_and_streak("2026-10-25 21:59Z") == (date(2026, 10, 25), 1)  # 23:59, UTC+2
    assert today_and_streak("2026-10-25 22:01Z") == (date(2026, 10, 26), 0)  # the 25th is missed
