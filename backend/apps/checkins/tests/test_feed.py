"""The crew feed and the day sheet: who sees what, in which order, and paging."""

from datetime import date
from decimal import Decimal

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


def test_feed_items_say_the_streak_week_and_milestone_as_of_their_day(
    object_storage, crew, browser
):
    ana, bogdan, _, walk, _ = crew
    for n in (1, 2, 3, 4, 6, 7, 8):  # a miss on the 5th
        with at(f"2026-11-0{n} 08:00Z"):
            check_in(bogdan, walk, day=date(2026, 11, n))
    browser.force_login(ana.user)
    with at("2026-11-08 09:00Z"):
        body = browser.get("/api/v1/feed").json()

    by_day = {i["day"]: i for i in body["results"]}
    third, fourth, eighth = by_day["2026-11-03"], by_day["2026-11-04"], by_day["2026-11-08"]
    assert (third["streak"], third["milestone"]) == (3, {"kind": "streak", "n": 3})
    assert (fourth["streak"], fourth["milestone"]) == (4, None)  # not again the day after
    assert (eighth["streak"], eighth["milestone"]) == (3, {"kind": "streak", "n": 3})
    assert (eighth["day_index"], eighth["day_count"]) == (8, 30)
    assert [d["state"] for d in eighth["week"]] == [
        "done", "done", "done", "missed", "done", "done", "done"
    ]  # fmt: skip
    assert eighth["week"][-1]["day"] == "2026-11-08"
    first_week = by_day["2026-11-02"]["week"]
    assert [d["state"] for d in first_week][:5] == ["outside"] * 5  # before the start
    assert (eighth["last_amount"], eighth["target"]) == (None, None)


def test_feed_items_of_number_challenges_say_the_last_amount_and_the_days_target(
    object_storage, crew, browser
):
    ana, bogdan, _, _, _ = crew
    with at("2026-10-10 12:00Z"):
        pages = scheduled(
            ana,
            bogdan,
            date(2026, 11, 1),
            title="Pages",
            measure="quantity",
            unit="pages",
            target_scope="per_check_in",
            target_value="30",
        )
        km = scheduled(
            ana, bogdan, date(2026, 11, 1), title="Km", measure="quantity", unit="km",
            frequency="times_per_week", times=3,
        )  # fmt: skip
    with at("2026-11-10 08:00Z"):
        services.check_in(by=bogdan, challenge_id=pages.pk, day=DAY, amount=Decimal(8))
        services.check_in(by=bogdan, challenge_id=pages.pk, day=DAY, amount=Decimal(12))
        services.check_in(by=bogdan, challenge_id=km.pk, day=DAY, amount=Decimal("2.5"))
        browser.force_login(ana.user)
        body = browser.get("/api/v1/feed").json()

    by_title = {i["challenge"]["title"]: i for i in body["results"]}
    assert (by_title["Pages"]["total"], by_title["Pages"]["last_amount"]) == (20, 12)
    assert by_title["Pages"]["target"] == 30
    assert (by_title["Pages"]["milestone"], by_title["Pages"]["streak"]) == (None, 0)  # not done
    assert (by_title["Km"]["last_amount"], by_title["Km"]["target"]) == (2.5, None)
    assert by_title["Km"]["milestone"] is None  # weeks, not days in a row


def test_milestones_come_at_7_14_and_30_days(crew):
    _, bogdan, _, walk, _ = crew
    for n in range(1, 31):
        with at(f"2026-11-{n:02d} 08:00Z"):
            check_in(bogdan, walk, day=date(2026, 11, n))
    with at("2026-11-30 09:00Z"):
        page = list(selectors.feed(member=bogdan).filter(challenge=walk))
        details = selectors.feed_details(page)
    hits = sorted(c.day.day for c in page if details[c.pk].milestone)
    assert hits == [3, 7, 14, 30]
    assert selectors.feed_details([]) == {}


def test_each_feed_item_carries_its_days_summary(object_storage, crew, browser):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-11-09 08:00Z"):  # everyone walks and Ana and Bogdan read on the 9th
        for member in (ana, bogdan, cristina):
            check_in(member, walk, day=date(2026, 11, 9))
        for member in (ana, bogdan):
            check_in(member, read, day=date(2026, 11, 9))
    with at("2026-11-10 08:00Z"):  # on the 10th only Bogdan walks, with a photo
        check_in(bogdan, walk)
        shown_photo(object_storage, bogdan, walk)
        photo(bogdan, walk)  # uploading: not counted
        browser.force_login(cristina.user)
        hers = browser.get("/api/v1/feed").json()["results"]
        browser.force_login(ana.user)
        all_of_it = browser.get("/api/v1/feed").json()["results"]

    def summaries(results):
        return {i["day"]: i["day_summary"] for i in results}

    assert summaries(all_of_it) == {
        "2026-11-10": {"check_ins": 1, "proofs": 1, "crew_done": False},
        "2026-11-09": {"check_ins": 5, "proofs": 0, "crew_done": True},
    }
    assert summaries(hers)["2026-11-09"] == {"check_ins": 3, "proofs": 0, "crew_done": True}
    assert selectors.day_summaries(member=ana, on=set()) == {}


def test_a_day_with_nothing_due_is_never_the_crews_whole_day(crew):
    ana, bogdan, _, _, _ = crew
    with at("2026-10-10 12:00Z"):
        weekly = scheduled(
            ana, bogdan, date(2026, 12, 1), title="Gym", frequency="times_per_week", times=2
        )
    with at("2026-12-01 08:00Z"):
        check_in(bogdan, weekly, day=date(2026, 12, 1))
        summary = selectors.day_summaries(member=ana, on={date(2026, 12, 1)})
    assert summary[date(2026, 12, 1)].crew_done is False


def test_today_says_each_persons_state_per_challenge(crew, browser):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-10-10 12:00Z"):
        pages = scheduled(
            ana, bogdan, date(2026, 11, 1), [ana.pk], title="Pages", measure="quantity",
            unit="pages", target_scope="per_check_in", target_value="30",
        )  # fmt: skip
    with at("2026-11-10 08:00Z"):
        check_in(bogdan, walk)
        services.check_in(by=bogdan, challenge_id=pages.pk, day=DAY, amount=Decimal(5))
        browser.force_login(ana.user)
        crew_today = browser.get("/api/v1/today").json()["crew"]

    bogdans = next(r for r in crew_today if r["member"]["display_name"] == "Bogdan")
    states = {c["challenge_id"]: c["state"] for c in bogdans["challenges"]}
    assert states == {str(walk.pk): "done", str(read.pk): "todo", str(pages.pk): "started"}
    assert (bogdans["done"], bogdans["needed"]) == (1, 3)
