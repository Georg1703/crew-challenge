"""The crew's day: the day sheet of a challenge and everyone's state on Today."""

from datetime import date
from decimal import Decimal

import pytest

from apps.checkins import selectors, services
from apps.checkins.tests.conftest import shown_photo
from apps.checkins.tests.test_proofs import DAY, at, check_in, photo, scheduled

pytestmark = pytest.mark.django_db


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


def test_today_says_each_persons_state_per_challenge(crew, browser):
    ana, bogdan, cristina, walk, read = crew
    with at("2026-10-10 12:00Z"):
        pages = scheduled(
            ana, bogdan, date(2026, 11, 1), [ana.pk], title="Pages", measure="quantity",
            unit="pages", day_min="30",
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
