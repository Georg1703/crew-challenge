"""Check-ins as reaction targets: which ones take reactions, and how the feed shows them."""

from datetime import date
from decimal import Decimal

import pytest

from apps.checkins import services
from apps.checkins.models import CheckIn
from apps.checkins.tests.conftest import shown_photo
from apps.checkins.tests.test_proofs import DAY, at, check_in, scheduled
from apps.reactions import targets
from apps.reactions.models import Reaction
from tests.factories import MemberFactory

pytestmark = pytest.mark.django_db

FIRE = "\U0001f525"
CLAP = "\U0001f44f"


def react(browser, check_in_id, emoji=FIRE):
    return browser.put(f"/api/v1/reactions/check_in/{check_in_id}", {"emoji": emoji}, format="json")


def test_check_ins_are_registered_as_a_target():
    target = targets.get("check_in")
    assert target is not None
    assert target.model is CheckIn


def test_the_crew_reacts_to_a_proof_card_and_the_feed_shows_it(object_storage, crew, browser):
    ana, bogdan, cristina, walk, _ = crew
    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk)
        shown_photo(object_storage, bogdan, walk)
        card = CheckIn.objects.get(member=bogdan)
        browser.force_login(cristina.user)
        assert react(browser, card.pk, CLAP).json()["mine"] == CLAP
    with at("2026-11-10 08:05Z"):
        browser.force_login(ana.user)
        assert react(browser, card.pk).status_code == 200
        item = browser.get("/api/v1/feed").json()["results"][0]

    assert item["reactions"] == {
        "groups": [
            {"emoji": CLAP, "member_ids": [str(cristina.pk)]},
            {"emoji": FIRE, "member_ids": [str(ana.pk)]},
        ],
        "mine": FIRE,
    }


def test_plain_and_hidden_check_ins_take_no_reactions(object_storage, crew, browser):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-11-10 08:00Z"):
        check_in(cristina, walk)  # plain: said together with others in the journal
        check_in(bogdan, read)
        shown_photo(object_storage, bogdan, read)  # Cristina does not take part in Read
        plain = CheckIn.objects.get(member=cristina)
        hidden = CheckIn.objects.get(member=bogdan)

        browser.force_login(cristina.user)
        for target in (plain, hidden):
            response = react(browser, target.pk)
            assert (response.status_code, response.json()["error"]["code"]) == (
                404,
                "target_not_found",
            )
        browser.force_login(MemberFactory.create().user)  # another crew
        assert react(browser, plain.pk).status_code == 404


def test_numbers_and_milestones_take_reactions(crew, browser):
    ana, bogdan, cristina, _, _ = crew
    with at("2026-10-10 12:00Z"):
        pages = scheduled(
            ana, bogdan, date(2026, 11, 1), title="Pages", measure="quantity", unit="p"
        )
        walk = scheduled(ana, bogdan, date(2026, 11, 1), title="Steps")
    for n in (1, 2, 3):
        with at(f"2026-11-0{n} 08:00Z"):
            check_in(bogdan, walk, day=date(2026, 11, n))
    with at("2026-11-03 09:00Z"):
        services.check_in(
            by=bogdan, challenge_id=pages.pk, day=date(2026, 11, 3), amount=Decimal(4)
        )
        by_day = {c.day.day: c for c in CheckIn.objects.filter(challenge=walk)}
        number = CheckIn.objects.get(challenge=pages)

        browser.force_login(cristina.user)
        assert react(browser, number.pk).status_code == 200
        assert react(browser, by_day[3].pk).status_code == 200  # 3 days in a row
        assert react(browser, by_day[2].pk).status_code == 404  # just a check-in


def test_deleting_a_check_in_deletes_its_reactions(object_storage, crew, browser):
    _, bogdan, cristina, walk, _ = crew
    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk, day=DAY)
        shown_photo(object_storage, bogdan, walk)
        card = CheckIn.objects.get(member=bogdan)
        browser.force_login(cristina.user)
        react(browser, card.pk)
    assert Reaction.objects.count() == 1
    card.delete()
    assert not Reaction.objects.exists()
