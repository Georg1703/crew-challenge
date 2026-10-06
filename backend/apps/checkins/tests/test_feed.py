"""The crew feed and the day sheet: who sees what, in which order, and paging."""

from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.checkins import selectors, services
from apps.checkins.tests.test_proofs import DAY, at, check_in, photo, scheduled, send
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def crew():
    """Ana (admin), Bogdan, Cristina in November 2026. Walk: all three. Read: Bogdan and Ana."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=ana.crew, display_name="Cristina")
        walk = scheduled(ana, bogdan, date(2026, 11, 1), proof_kind="photo_or_video")
        read = scheduled(ana, bogdan, date(2026, 11, 1), [ana.pk], title="Read", proof_kind="photo")
    return ana, bogdan, cristina, walk, read


def shown_photo(storage, member, challenge, day=DAY):
    plan = photo(member, challenge, day=day)
    send(storage, plan)
    return services.complete_proof(by=member, proof_id=plan.proof.pk)


def items(member):
    return [
        (c.member.display_name, c.challenge.title, len(c.shown_proofs))  # type: ignore[attr-defined]
        for c in selectors.feed(member=member).order_by("-activity_at")
    ]


def test_the_feed_shows_what_you_can_see_latest_activity_first(object_storage, crew):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk)
    with at("2026-11-10 09:00Z"):
        check_in(cristina, walk)
    with at("2026-11-10 10:00Z"):
        check_in(bogdan, read)
    with at("2026-11-10 11:00Z"):
        shown_photo(object_storage, bogdan, walk)  # brings Bogdan's walk back to the top
        photo(bogdan, walk)  # still uploading: not shown

    assert items(cristina) == [("Bogdan", "Walk", 1), ("Cristina", "Walk", 0)]
    assert items(ana) == [("Bogdan", "Walk", 1), ("Bogdan", "Read", 0), ("Cristina", "Walk", 0)]


def test_the_day_sheet_shows_everyone_on_that_day(object_storage, crew, browser):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk)
        shown_photo(object_storage, bogdan, walk)
        check_in(cristina, walk)
        photo(cristina, walk)  # still uploading: not shown

        rows = selectors.day_sheet(member=cristina, challenge_id=walk.pk, day=DAY)
        assert rows is not None
        assert {r.member.display_name: (r.state, len(r.proofs)) for r in rows} == {
            "Ana": ("todo", 0),
            "Bogdan": ("done", 1),
            "Cristina": ("done", 0),  # her upload is still running
        }
        assert selectors.day_sheet(member=cristina, challenge_id=read.pk, day=DAY) is None

        browser.force_login(cristina.user)
        body = browser.get(f"/api/v1/challenges/{walk.pk}/days/2026-11-10").json()  # a list
        hidden = browser.get(f"/api/v1/challenges/{read.pk}/days/2026-11-10")
        bad_day = browser.get(f"/api/v1/challenges/{walk.pk}/days/tuesday")

    by_name = {r["member"]["display_name"]: r for r in body}
    assert by_name["Bogdan"]["state"] == "done"
    assert by_name["Bogdan"]["proofs"][0]["url"]
    assert hidden.json()["error"]["code"] == "challenge_not_found"
    assert bad_day.status_code == 400


def test_feed_pages_are_stable_while_the_crew_keeps_going(object_storage, crew, browser):
    _, bogdan, _, walk, _ = crew
    for n in range(1, 6):  # Bogdan walks on 1-5 November
        with at(f"2026-11-0{n} 08:00Z"):
            check_in(bogdan, walk, day=date(2026, 11, n))
    browser.force_login(bogdan.user)

    with at("2026-11-05 09:00Z"):
        first = browser.get("/api/v1/feed?page_size=2").json()
        shown_photo(object_storage, bogdan, walk, day=date(2026, 11, 5))  # new activity
        second = browser.get(f"/api/v1/feed?page_size=2&cursor={first['next']}").json()
        third = browser.get(f"/api/v1/feed?page_size=2&cursor={second['next']}").json()

    days = [i["day"] for page in (first, second, third) for i in page["results"]]
    assert days == ["2026-11-05", "2026-11-04", "2026-11-03", "2026-11-02", "2026-11-01"]
    assert third["next"] is None
    item = first["results"][0]
    assert (item["member"]["display_name"], item["challenge"]["title"], item["status"]) == (
        "Bogdan",
        "Walk",
        "done",
    )


def test_a_fuller_feed_page_costs_no_more_queries(object_storage, crew, browser):
    ana, bogdan, cristina, walk, read = crew
    browser.force_login(ana.user)

    def queries():
        with CaptureQueriesContext(connection) as ctx:
            assert browser.get("/api/v1/feed").status_code == 200
        return len(ctx)

    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk)
        shown_photo(object_storage, bogdan, walk)
        one_item = queries()
        for member, challenge in ((cristina, walk), (bogdan, read), (ana, walk)):
            check_in(member, challenge)
            shown_photo(object_storage, member, challenge)
        four_items = queries()

    assert four_items == one_item
