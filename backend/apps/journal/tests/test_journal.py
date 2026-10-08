"""The journal merges check-ins and drawn spins by activity, page by page."""

from datetime import date

import pytest

from apps.checkins import services as checkins
from apps.doom import services as doom
from apps.doom.models import Spin
from apps.doom.tests.test_services import Pick, at, check_in, scheduled
from apps.journal import selectors
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db


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
        doom.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))
    return ana, bogdan, spin


def test_pages_merge_both_kinds_latest_first(week):
    ana, _, spin = week
    seen = []
    cursor = None
    while True:
        entries, cursor = selectors.page(member=ana, cursor=cursor, size=1)
        seen += [(e.kind, e.item.pk == spin.pk) for e in entries]
        if cursor is None:
            break
    assert seen == [("spin", True), ("check_in", False), ("check_in", False)]


def test_the_journal_endpoint(browser, week):
    ana, _, spin = week
    browser.force_login(ana.user)
    with at("2026-11-09 09:00Z"):
        body = browser.get("/api/v1/journal").json()
    assert [r["kind"] for r in body["results"]] == ["spin", "check_in", "check_in"]
    assert body["next"] is None
    item = body["results"][0]["spin"]
    assert (item["id"], item["state"], item["day"], item["punishment_count"]) == (
        str(spin.pk),
        "spun",
        "2026-11-09",
        2,
    )
    assert item["punishment"]["text"] == "20 burpees"
    assert body["results"][0]["check_in"] is None
    assert body["results"][1]["check_in"]["day"] == "2026-11-09"
    assert browser.get("/api/v1/journal?cursor=nope").status_code == 400
