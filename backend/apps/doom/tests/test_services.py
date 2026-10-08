"""Spins on "Swim 3 times a week" (Chisinau: UTC+2 from October 25, 2026, UTC+3 before)."""

import random
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
import time_machine

from apps.challenges import services as challenges
from apps.checkins import services as checkins
from apps.doom import selectors, services
from apps.doom.models import Spin
from apps.proofs import services as proofs
from tests.factories import AdminFactory

pytestmark = pytest.mark.django_db

PUNISHMENTS = [
    {"text": "20 burpees", "proof_required": True},
    {"text": "No phone after 21:00"},
]
SWIM = {
    "title": "Swim",
    "measure": "check",
    "window": "week",
    "need_value": 3,
    "period_kind": "week",
    "period_length": 2,
    "punishments": PUNISHMENTS,
}


def at(moment: str):
    return time_machine.travel(moment, tick=False)


class Pick(random.Random):
    """Draws the punishment at `index`, so a test knows what it gets."""

    def __init__(self, index: int) -> None:
        super().__init__()
        self.index = index

    def choice(self, seq: Any) -> Any:
        return seq[self.index]


def scheduled(admin, by, start: date, shape=SWIM):
    with at("2026-10-10 12:00Z"):
        challenge = challenges.propose_challenge(by=by, shape=shape)
        challenges.schedule_challenge(by=admin, challenge_id=challenge.pk, period_start=start)
    return challenge


def check_in(member, challenge, day: date, amount=None):
    with at(f"{day.isoformat()} 08:00Z"):
        checkins.check_in(by=member, challenge_id=challenge.pk, day=day, amount=amount)


@pytest.fixture
def swim(crew):
    """Weeks of November 2 and 9; Bogdan swims once in the first, Ana never."""
    ana, bogdan = crew
    challenge = scheduled(ana, bogdan, date(2026, 11, 2))
    check_in(bogdan, challenge, date(2026, 11, 2))
    return ana, bogdan, challenge


def numbers(member) -> list[int]:
    return list(Spin.objects.filter(member=member).values_list("number", flat=True))


@pytest.mark.parametrize(
    ("start", "before", "after"),
    [
        (date(2026, 11, 2), "2026-11-08 21:59Z", "2026-11-08 22:01Z"),  # 23:59 / 00:01 local
        (date(2026, 10, 19), "2026-10-25 21:59Z", "2026-10-25 22:01Z"),  # the 25-hour Sunday
    ],
)
def test_a_week_that_ended_short_opens_one_spin_per_missing_check_in(crew, start, before, after):
    ana, bogdan = crew
    challenge = scheduled(ana, bogdan, start)
    check_in(bogdan, challenge, start)
    with at(before):
        assert services.open_spins() == 0  # the week is still open
    with at(after):
        assert services.open_spins() == 5  # Bogdan 1 of 3, Ana 0 of 3
        assert services.open_spins() == 0  # never twice
    assert numbers(bogdan) == [1, 2]
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    assert (spin.window_first, spin.need, spin.done) == (start, Decimal(3), Decimal(1))


def test_met_weeks_totals_and_challenges_without_punishments(crew):
    ana, bogdan = crew
    run = scheduled(
        ana,
        bogdan,
        date(2026, 11, 2),
        {**SWIM, "title": "Run", "measure": "quantity", "unit": "km"}
        | {"need_kind": "amount", "need_value": 50},
    )
    plain = scheduled(ana, bogdan, date(2026, 11, 2), {**SWIM, "title": "Walk", "punishments": []})
    for day in (2, 3, 4):
        check_in(ana, run, date(2026, 11, day), amount=Decimal(20))  # 60 of 50: met
    check_in(
        bogdan, run, date(2026, 11, 2), amount=Decimal(30)
    )  # 30 of 50: one spin, however short
    with at("2026-11-09 08:00Z"):
        services.open_spins()
    assert list(Spin.objects.values_list("member__display_name", "challenge__title")) == [
        ("Bogdan", "Run")
    ]
    assert not Spin.objects.filter(challenge=plain).exists()


def test_a_member_who_left_still_owes_the_cut_week(swim):
    ana, _, challenge = swim
    with at("2026-11-04 08:00Z"):  # Wednesday: Monday to today counts, 1 of 3 x 3/7
        challenges.stop_taking_part(by=ana, challenge_id=challenge.pk)
    with at("2026-11-08 22:01Z"):
        services.open_spins()
        assert numbers(ana) == [1]
        owed = selectors.owed(member=ana)
    assert (owed.to_spin, owed.to_serve) == (1, 0)
    assert owed.spins[0].window_last == date(2026, 11, 4)


def test_drawing_is_mine_once_and_sets_the_day_to_serve_by(swim):
    ana, bogdan, _ = swim
    with at("2026-11-08 22:01Z"):
        services.open_spins()
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    with pytest.raises(services.SpinNotFound):
        services.draw(by=ana, spin_id=spin.pk)

    with at("2026-11-09 21:30Z"):  # 23:30 local, Monday
        drawn = services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(1))
        again = services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))  # a second tap
    assert drawn.punishment is not None
    assert drawn.punishment.position == 2
    assert again.punishment_id == drawn.punishment_id
    assert drawn.serve_by == date(2026, 11, 16)

    rows = selectors.owed(member=bogdan).spins
    with at("2026-11-16 21:00Z"):
        assert not selectors.late(next(s for s in rows if s.pk == spin.pk))
    with at("2026-11-16 22:30Z"):  # 00:30 on the 17th
        assert selectors.late(next(s for s in rows if s.pk == spin.pk))


def test_a_draw_picks_from_the_challenges_punishments_with_the_random_source(swim):
    _, bogdan, _ = swim
    with at("2026-11-08 22:01Z"):
        services.open_spins()
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    with at("2026-11-09 08:00Z"):
        drawn = services.draw(by=bogdan, spin_id=spin.pk, rng=random.Random(7))
    assert drawn.punishment is not None
    assert drawn.punishment.position == random.Random(7).choice([1, 2])


def test_serving_with_proof_or_done(swim, object_storage):
    _, bogdan, _ = swim
    with at("2026-11-08 22:01Z"):
        services.open_spins()
    first, second = Spin.objects.filter(member=bogdan).order_by("number")
    photo: dict[str, Any] = {"kind": "photo", "content_type": "image/jpeg", "size": 4}
    with at("2026-11-09 08:00Z"):
        with pytest.raises(services.NotDrawn):
            services.mark_done(by=bogdan, spin_id=first.pk)
        with pytest.raises(services.NotDrawn):
            services.start_proof(by=bogdan, spin_id=first.pk, **photo)
        services.draw(by=bogdan, spin_id=first.pk, rng=Pick(0))  # 20 burpees: needs proof
        services.draw(by=bogdan, spin_id=second.pk, rng=Pick(1))  # no phone: "Done"

        with pytest.raises(services.ProofNeeded):
            services.mark_done(by=bogdan, spin_id=first.pk)
        with pytest.raises(services.ProofNotNeeded):
            services.start_proof(by=bogdan, spin_id=second.pk, **photo)

        plan = services.start_proof(by=bogdan, spin_id=first.pk, **photo)
        assert plan.proof.subject == first
        object_storage.put_object(key=plan.proof.original.key, data=b"jpeg", content_type="")
        proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)
        services.mark_done(by=bogdan, spin_id=second.pk)
        services.mark_done(by=bogdan, spin_id=second.pk)  # repeat-safe
        assert selectors.owed(member=bogdan).spins == []  # both served

        proofs.delete_proof(by=bogdan, proof_id=plan.proof.pk)  # the same day: allowed
        assert [s.pk for s in selectors.owed(member=bogdan).spins] == [first.pk]


def test_the_crew_sees_drawn_spins_only(swim):
    ana, bogdan, _ = swim
    with at("2026-11-08 22:01Z"):
        services.open_spins()
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    assert not selectors.journal(member=ana).exists()  # nothing drawn yet
    with at("2026-11-09 08:00Z"):
        services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(1))
    assert [s.pk for s in selectors.journal(member=ana)] == [spin.pk]
    assert not selectors.served(member=ana).exists()
    with at("2026-11-10 08:00Z"):
        services.mark_done(by=bogdan, spin_id=spin.pk)
    served = [s.activity_at for s in selectors.served(member=ana)]  # type: ignore[attr-defined]
    assert served == [datetime(2026, 11, 10, 8, tzinfo=UTC)]  # at "Done"
    assert selectors.reactable_spin(ana, spin.pk) == spin
    stranger = AdminFactory.create()
    assert not selectors.journal(member=stranger).exists()
    assert selectors.reactable_spin(stranger, spin.pk) is None
