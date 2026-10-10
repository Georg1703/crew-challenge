"""The journal over HTTP: one card per post as it was posted, its proofs, its own reactions, and
the day counts for the dividers."""

from datetime import date
from importlib import import_module

import pytest
from django.apps import apps as registry
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.checkins import services as checkins
from apps.checkins.models import CheckIn
from apps.comments import services as comments
from apps.comments.models import Comment
from apps.doom import services as doom
from apps.doom.models import Spin
from apps.doom.tests.test_services import Pick, at, check_in, scheduled
from apps.journal.models import JournalEntry
from apps.proofs import services as proofs
from apps.reactions import services as reactions
from apps.reactions.models import Reaction
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

FIRE, CLAP = "\U0001f525", "\U0001f44f"


@pytest.fixture
def week():
    """Bogdan swam on Monday the 2nd; on Monday the 9th Ana swims at 07:00Z and Bogdan, owing
    two spins, draws one at 08:00Z."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
    challenge = scheduled(ana, bogdan, date(2026, 11, 2))
    check_in(bogdan, challenge, date(2026, 11, 2))
    with at("2026-11-09 07:00Z"):
        doom.open_spins()
        checkins.check_in(by=ana, challenge_id=challenge.pk, day=date(2026, 11, 9))
    spin = Spin.objects.filter(member=bogdan).order_by("number").first()
    assert spin is not None
    with at("2026-11-09 08:00Z"):
        doom.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))  # 20 burpees: needs proof
    return ana, bogdan, spin


def journal(browser, member, query=""):
    browser.force_login(member.user)
    return browser.get(f"/api/v1/journal{query}").json()


def test_the_journal_shows_each_card_as_it_was_posted(browser, week):
    ana, _, spin = week
    with at("2026-11-09 09:00Z"):
        body = journal(browser, ana)

    assert [(r["kind"], r["day"], r["member"]["display_name"]) for r in body["results"]] == [
        ("spin", "2026-11-09", "Bogdan"),
        ("check_in", "2026-11-09", "Ana"),
        ("check_in", "2026-11-02", "Bogdan"),
    ]
    drawn, swam = body["results"][0], body["results"][1]
    assert drawn["spin"]["punishment"]["text"] == "20 burpees"
    assert (drawn["spin"]["need"], drawn["spin"]["done"], drawn["spin"]["serve_by"]) == (
        3.0,
        1.0,  # he swam once that week
        "2026-11-16",
    )
    assert (drawn["check_in"], drawn["served"], drawn["crew_day"], drawn["proofs"]) == (
        None,
        None,
        None,
        [],
    )
    assert (swam["check_in"]["action"], swam["check_in"]["proofs"]) == ("check", 0)
    assert body["days"] == [
        {"day": "2026-11-09", "check_ins": 1, "proofs": 0},
        {"day": "2026-11-02", "check_ins": 1, "proofs": 0},
    ]
    assert body["next"] is None
    assert browser.get("/api/v1/journal?cursor=nope").status_code == 400


def test_a_served_spin_is_a_card_of_its_own_with_its_photo(browser, week, object_storage):
    ana, bogdan, spin = week
    with at("2026-11-11 10:00Z"):  # Wednesday: the photo uploads, then "Serve"
        plan = doom.start_proof(
            by=bogdan, spin_id=spin.pk, kind="photo", content_type="image/jpeg", size=4
        )
        object_storage.put_object(key=plan.proof.original.key, data=b"jpeg", content_type="")
        proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)
        before = journal(browser, ana)  # a draft: nobody sees it yet
        doom.serve(by=bogdan, spin_id=spin.pk)
        body = journal(browser, ana)

    assert before["results"][0]["kind"] == "spin"
    served, drawn = body["results"][0], body["results"][1]
    assert (served["kind"], served["day"], served["served"]["proofs"]) == (
        "served",
        "2026-11-11",
        1,
    )
    assert [p["id"] for p in served["proofs"]] == [str(plan.proof.pk)]
    assert (drawn["kind"], drawn["proofs"]) == ("spin", [])
    assert body["days"][0] == {"day": "2026-11-11", "check_ins": 0, "proofs": 1}


def test_each_card_takes_its_own_reactions(browser, week, object_storage):
    ana, bogdan, spin = week
    with at("2026-11-10 08:00Z"):
        doom.draw(by=bogdan, spin_id=spin.pk)  # repeat-safe: already drawn
    drawn = JournalEntry.objects.get(kind=JournalEntry.Kind.SPIN)
    swim = JournalEntry.objects.filter(kind=JournalEntry.Kind.CHECK_IN, member=ana).get()
    browser.force_login(bogdan.user)
    for card, emoji in ((drawn, FIRE), (swim, CLAP)):
        url = f"/api/v1/reactions/entry/{card.pk}"
        assert browser.put(url, {"emoji": emoji}, format="json").status_code == 200
    stranger = AdminFactory.create()
    browser.force_login(stranger.user)
    hidden = browser.put(f"/api/v1/reactions/entry/{drawn.pk}", {"emoji": FIRE}, format="json")
    assert hidden.status_code == 404

    body = journal(browser, ana)
    by_id = {r["id"]: r["reactions"]["groups"] for r in body["results"]}
    assert [g["emoji"] for g in by_id[str(drawn.pk)]] == [FIRE]
    assert [g["emoji"] for g in by_id[str(swim.pk)]] == [CLAP]


def test_a_fuller_page_costs_no_more_queries(browser, week):
    ana, bogdan, _ = week
    browser.force_login(ana.user)
    with CaptureQueriesContext(connection) as few:
        browser.get("/api/v1/journal")
    with at("2026-11-10 08:00Z"):
        for member in (ana, bogdan):
            challenge = Spin.objects.get(member=bogdan, number=1).challenge
            checkins.check_in(by=member, challenge_id=challenge.pk, day=date(2026, 11, 10))
    with CaptureQueriesContext(connection) as more:
        browser.get("/api/v1/journal")
    assert len(more) == len(few)


def test_old_reactions_move_to_their_cards(week):
    ana, bogdan, spin = week
    check_in_row = CheckIn.objects.get(member=ana)
    for target in (check_in_row, spin):
        Reaction.objects.create(
            crew=ana.crew,
            member=bogdan,
            emoji=FIRE,
            target_type=ContentType.objects.get_for_model(target),
            target_id=target.pk,
        )
    undrawn = Spin.objects.exclude(pk=spin.pk).first()  # never drawn: no card
    assert undrawn is not None
    lost = Reaction.objects.create(
        crew=ana.crew,
        member=ana,
        emoji=CLAP,
        target_type=ContentType.objects.get_for_model(Spin),
        target_id=undrawn.pk,
    )

    import_module("apps.journal.migrations.0003_reactions_on_cards").move(registry, None)

    entry_type = ContentType.objects.get_for_model(JournalEntry)
    cards = {
        (r.target_type, JournalEntry.objects.get(pk=r.target_id).kind)
        for r in Reaction.objects.all()
    }
    assert cards == {(entry_type, "check_in"), (entry_type, "spin")}
    assert not Reaction.objects.filter(pk=lost.pk).exists()


def test_cards_carry_their_comments_and_open_on_their_own(browser, week):
    ana, bogdan, _ = week
    swim = JournalEntry.objects.get(kind=JournalEntry.Kind.CHECK_IN, member=ana)
    url = f"/api/v1/comments/entry/{swim.pk}"
    browser.force_login(bogdan.user)
    assert browser.post(url, {"text": "Bravo!"}, format="json").status_code == 201

    with at("2026-11-09 09:00Z"):
        page = journal(browser, ana)
        one = browser.get(f"/api/v1/journal/{swim.pk}").json()
    shown = next(r for r in page["results"] if r["id"] == str(swim.pk))
    assert shown["comments"] == {"count": 1, "member_ids": [str(bogdan.pk)]}
    assert one == shown
    assert [c["text"] for c in browser.get(url).json()["results"]] == ["Bravo!"]

    browser.force_login(AdminFactory.create().user)  # another crew
    gone = browser.get(f"/api/v1/journal/{swim.pk}")
    assert (gone.status_code, gone.json()["error"]["code"]) == (404, "card_not_found")
    assert browser.get(url).status_code == 404


def test_a_post_others_commented_on_cannot_be_undone(week):
    ana, bogdan, _ = week
    swim = JournalEntry.objects.get(kind=JournalEntry.Kind.CHECK_IN, member=ana)
    undo = {"by": ana, "challenge_id": swim.challenge_id, "day": date(2026, 11, 9)}
    with at("2026-11-09 10:00Z"):
        mine = comments.add(member=ana, target="entry", target_id=swim.pk, text="Rece!")
        reactions.react(member=bogdan, target="comment", target_id=mine.pk, emoji=FIRE)
        theirs = comments.add(member=bogdan, target="entry", target_id=swim.pk, text="Bravo!")
        with pytest.raises(checkins.PostHasComments):
            checkins.undo_last(**undo)
        comments.delete(member=bogdan, comment_id=theirs.pk)  # within its minute
        checkins.undo_last(**undo)  # only her own words left: they go with the card

    assert not JournalEntry.objects.filter(pk=swim.pk).exists()
    assert not Comment.all_objects.filter(target_id=swim.pk).exists()
    assert not Reaction.objects.filter(target_id=mine.pk).exists()
