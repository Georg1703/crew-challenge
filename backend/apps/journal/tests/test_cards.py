"""The stored journal: a card per post written with it and never edited, the crew's day, a page."""

import io
from datetime import date
from decimal import Decimal
from importlib import import_module
from typing import Any

import pytest
from django.apps import apps as registry
from django.core.management import call_command

from apps.checkins import services as checkins
from apps.checkins.tests.test_proofs import at, photo, scheduled, send
from apps.doom import services as doom
from apps.doom.models import Spin
from apps.doom.tests.test_services import SWIM, Pick
from apps.journal import selectors, services
from apps.journal.models import JournalEntry
from apps.proofs import services as proofs
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

Kind = JournalEntry.Kind
NOV_1, NOV_2, NOV_3 = date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)


@pytest.fixture
def crew():
    """Ana (admin) and Bogdan: Walk every day of November, Run (km, 10 a day) too."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        walk = scheduled(ana, bogdan, NOV_1)
        run = scheduled(
            ana, bogdan, NOV_1, [bogdan.pk], title="Run", measure="quantity", unit="km", day_min=10
        )
    return ana, bogdan, walk, run


def post(member, challenge, day, amount=None):
    with at(f"{day.isoformat()} 08:00Z"):
        return checkins.check_in(by=member, challenge_id=challenge.pk, day=day, amount=amount)


def cards(kind=None):
    rows = JournalEntry.objects.order_by("created_at", "kind")
    return list(rows.filter(kind=kind) if kind else rows)


def test_a_card_is_written_once_and_dropped(crew):
    ana, _, _, _ = crew
    first = services.post(
        Kind.CREW_DAY, ana.crew, day=NOV_1, facts={"n": Decimal("1.5")}, member=None, challenge=None
    )
    again = services.post(
        Kind.CREW_DAY, ana.crew, day=NOV_1, facts={"n": 2}, member=None, challenge=None
    )
    assert (again.pk, again.facts, again.crew_id) == (first.pk, {"n": "1.5"}, ana.crew_id)
    services.drop(Kind.CREW_DAY, ana.crew, day=NOV_1)
    assert not JournalEntry.objects.exists()


def test_each_post_writes_its_card_frozen_as_it_was(crew, object_storage):
    _, bogdan, _, run = crew
    post(bogdan, run, NOV_1, Decimal(5))
    post(bogdan, run, NOV_1, Decimal(6))  # 11 of 10: done
    with at("2026-11-01 09:00Z"):
        send(object_storage, plan := photo(bogdan, run, day=NOV_1))
        proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)
    post(bogdan, run, NOV_1)  # the photo, added later

    facts = [
        (c.facts["action"], c.facts["amount"], c.facts["total"], c.facts["proofs"]) for c in cards()
    ]
    assert facts == [
        ("amount", "5.00", "5.00", 0),
        ("amount", "6.00", "11.00", 0),
        ("files", None, "11.00", 1),
    ]
    assert {c.member for c in cards()} == {bogdan}

    with at("2026-11-01 10:00Z"):
        checkins.undo_last(by=bogdan, challenge_id=run.pk, day=NOV_1)
    assert [c.facts["total"] for c in cards()] == ["5.00", "11.00"]  # the others never change


def test_a_streak_milestone_is_on_the_post_that_reached_it(crew):
    _, bogdan, walk, _ = crew
    for day in (NOV_1, NOV_2, NOV_3):
        post(bogdan, walk, day)
    assert [(c.facts["streak"], c.facts["milestone"]) for c in cards(Kind.CHECK_IN)] == [
        (1, None),
        (2, None),
        (3, 3),
    ]


def test_the_crew_day_comes_with_the_last_one_due_and_goes_with_an_undo(crew):
    ana, bogdan, walk, run = crew
    post(ana, walk, NOV_1)
    post(bogdan, walk, NOV_1)
    assert cards(Kind.CREW_DAY) == []  # Bogdan's run is due too
    post(bogdan, run, NOV_1, Decimal(10))

    (day,) = cards(Kind.CREW_DAY)
    assert (day.day, day.member, day.challenge) == (NOV_1, None, None)
    assert sorted(day.facts["members"]) == sorted([str(ana.pk), str(bogdan.pk)])

    with at("2026-11-01 09:00Z"):
        checkins.undo_last(by=bogdan, challenge_id=run.pk, day=NOV_1)
    assert cards(Kind.CREW_DAY) == []


def test_a_week_judged_challenge_makes_no_crew_day(crew):
    ana, bogdan, _, _ = crew
    with at("2026-10-10 12:00Z"):
        swim = scheduled(ana, bogdan, NOV_1, title="Swim", window="week", need_value=3)
    post(ana, swim, NOV_2)
    assert cards(Kind.CREW_DAY) == []


def test_a_spin_writes_a_card_when_drawn_and_when_served_in_the_crews_time(crew):
    ana, bogdan, _, _ = crew
    with at("2026-10-10 12:00Z"):
        swim = scheduled(ana, bogdan, NOV_2, **SWIM)
    with at("2026-11-08 22:01Z"):
        doom.open_spins()
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    with at("2026-11-09 21:30Z"):  # 23:30 local, Monday the 9th
        doom.draw(by=bogdan, spin_id=spin.pk, rng=Pick(1))  # no phone: "Done"
    with at("2026-11-09 22:30Z"):  # 00:30 on the 10th
        doom.serve(by=bogdan, spin_id=spin.pk)

    drawn, served = cards()
    assert (drawn.kind, drawn.day, drawn.challenge) == (Kind.SPIN, date(2026, 11, 9), swim)
    assert drawn.facts["punishment"]["text"] == "No phone after 21:00"
    assert (served.kind, served.day, served.facts["proofs"]) == (Kind.SERVED, date(2026, 11, 10), 0)


def test_a_page_is_latest_first_walks_without_gaps_and_hides_what_you_cannot_see(
    crew, django_assert_max_num_queries
):
    ana, bogdan, walk, run = crew
    post(bogdan, walk, NOV_1)
    post(bogdan, run, NOV_1, Decimal(10))
    post(ana, walk, NOV_1)  # the crew's day too

    seen, cursor = [], None
    while True:
        with django_assert_max_num_queries(2):
            found, cursor = selectors.page(member=ana, cursor=cursor, size=2)
        seen += found
        if cursor is None:
            break
    assert sorted(c.kind for c in seen) == [Kind.CHECK_IN] * 3 + [Kind.CREW_DAY]
    assert len({c.pk for c in seen}) == 4  # no repeats
    assert seen == sorted(seen, key=lambda c: (c.created_at, c.pk), reverse=True)  # ties: by id
    stranger = AdminFactory.create()
    assert selectors.page(member=stranger, cursor=None, size=10) == ([], None)
    mine, _ = selectors.page(member=bogdan, cursor=None, size=10)
    assert len(mine) == 4  # Run is Bogdan's and Ana's (the admin) to see


def test_the_backfill_writes_the_same_cards_and_twice_is_once(crew):
    ana, bogdan, walk, run = crew
    post(bogdan, run, NOV_1, Decimal(4))
    post(bogdan, run, NOV_1, Decimal(7))
    post(bogdan, walk, NOV_1)
    post(ana, walk, NOV_1)
    post(bogdan, walk, NOV_2)
    written = {(c.kind, c.subject_id, c.day, c.created_at, str(c.facts)) for c in cards()}
    JournalEntry.objects.all().delete()

    call_command("journal_backfill", stdout=io.StringIO())  # today, placing cards in the past
    call_command("journal_backfill", stdout=io.StringIO())

    assert {(c.kind, c.subject_id, c.day, c.created_at, str(c.facts)) for c in cards()} == written


def test_the_migration_serves_spins_left_with_a_posted_proof(crew, object_storage):
    ana, bogdan, _, _ = crew
    with at("2026-10-10 12:00Z"):
        scheduled(ana, bogdan, NOV_2, **SWIM)
    with at("2026-11-08 22:01Z"):
        doom.open_spins()
    old, waiting = Spin.objects.filter(member=bogdan).order_by("number")[:2]  # of his 3
    photo_shape: dict[str, Any] = {"kind": "photo", "content_type": "image/jpeg", "size": 4}
    with at("2026-11-09 08:00Z"):
        for spin in (old, waiting):
            doom.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))  # 20 burpees: needs proof
            plan = doom.start_proof(by=bogdan, spin_id=spin.pk, **photo_shape)
            object_storage.put_object(key=plan.proof.original.key, data=b"jpeg", content_type="")
            proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)
    proofs.of_subject(old).update(post_id=old.pk)  # as the release before posted it

    migration = import_module("apps.journal.migrations.0002_backfill")
    migration.serve_shown(registry, None)

    old.refresh_from_db()
    waiting.refresh_from_db()
    assert old.done_at is not None  # served by its posted proof
    assert waiting.done_at is None  # its photo is a draft: still to serve
