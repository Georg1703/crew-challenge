"""A member's page: their month on the challenges you can see, streaks and proofs by day."""

from datetime import date

import pytest

from apps.checkins import selectors
from apps.checkins.tests.test_feed import shown_photo
from apps.checkins.tests.test_proofs import at, check_in, scheduled
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def crew():
    """Ana (admin), Bogdan, Cristina. Walk: all three. Read: Ana and Bogdan. November 2026."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=ana.crew, display_name="Cristina")
        walk = scheduled(ana, bogdan, date(2026, 11, 1), proof_required=True)
        read = scheduled(
            ana, bogdan, date(2026, 11, 1), [ana.pk], title="Read", proof_required=True
        )
    return ana, bogdan, cristina, walk, read


def test_a_members_month_with_streaks_and_proofs(object_storage, crew, browser):
    ana, bogdan, cristina, walk, read = crew
    for n in (1, 2, 3, 5, 6):  # walks; misses the 4th
        with at(f"2026-11-0{n} 08:00Z"):
            check_in(bogdan, walk, day=date(2026, 11, n))
    with at("2026-11-06 09:00Z"):
        check_in(bogdan, read, day=date(2026, 11, 6))
        shown_photo(object_storage, bogdan, walk, day=date(2026, 11, 6))
        shown_photo(object_storage, bogdan, read, day=date(2026, 11, 6))
        browser.force_login(ana.user)
        body = browser.get(f"/api/v1/members/{bogdan.pk}/progress").json()
        browser.force_login(cristina.user)
        hers = browser.get(f"/api/v1/members/{bogdan.pk}/progress?month=2026-11").json()

    assert body["member"]["display_name"] == "Bogdan"
    assert (body["streak"], body["longest_streak"]) == (2, 3)  # now 5-6, before 1-3
    # Walk: 6 due, 5 done; Read: 6 due, 1 done (the 6th, today, counts once done)
    assert (body["month_done"], body["month_due"]) == (6, 12)
    walks = next(c for c in body["challenges"] if c["challenge"]["title"] == "Walk")
    assert walks["states"][:7] == ["done", "done", "done", "missed", "done", "done", "future"]
    assert (walks["proof_days"], walks["today"], walks["streak"]) == (["2026-11-06"], "done", 2)
    assert len(body["days"]) == 30
    assert [(p["day"], p["challenge"]["title"], len(p["proofs"])) for p in body["proof_days"]] == [
        ("2026-11-06", "Read", 1),
        ("2026-11-06", "Walk", 1),
    ]
    # Cristina does not take part in Read: she sees only Walk
    assert [c["challenge"]["title"] for c in hers["challenges"]] == ["Walk"]
    assert [p["challenge"]["title"] for p in hers["proof_days"]] == ["Walk"]


def test_another_crews_member_or_a_bad_month_is_refused(crew, browser):
    ana, *_ = crew
    with at("2026-11-06 09:00Z"):
        stranger = AdminFactory.create(display_name="Zoe")
        browser.force_login(ana.user)
        missing = browser.get(f"/api/v1/members/{stranger.pk}/progress")
        bad = browser.get(f"/api/v1/members/{ana.pk}/progress?month=november")
        quiet = selectors.member_progress(viewer=ana, member_id=ana.pk, month=date(2027, 1, 1))

    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "member_not_found")
    assert bad.status_code == 400
    assert quiet is not None
    assert (quiet.challenges, quiet.proof_days, quiet.streak) == ([], [], 0)
