from datetime import date

import pytest
import time_machine

from apps.challenges import services as challenges
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

READ = {
    "title": "Read",
    "measure": "quantity",
    "unit": "pages",
    "frequency": "daily",
    "target_scope": "per_check_in",
    "target_value": 20,
}


@pytest.fixture
def setup():
    with time_machine.travel("2026-10-10 12:00Z", tick=False):
        admin = AdminFactory.create(display_name="Ana")
        member = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        read = challenges.propose_challenge(by=member, shape=READ)
        challenges.schedule_challenge(
            by=admin, challenge_id=read.pk, period_kind="month", period_start=date(2026, 11, 1)
        )
    with time_machine.travel("2026-11-10 08:00Z", tick=False):
        yield admin, member, read


def test_check_in_and_read_today(browser, setup):
    _, member, read = setup
    browser.force_login(member.user)
    url = f"/api/v1/challenges/{read.pk}/check-ins"
    first = browser.post(url, {"day": "2026-11-10", "amount": "12"}, format="json")
    assert first.status_code == 200
    body = first.json()
    assert (body["state"], body["total"], body["settled"]) == ("partial", 12.0, False)
    assert len(body["week"]) == 7
    second = browser.post(url, {"day": "2026-11-10", "amount": 8}, format="json").json()
    assert (second["state"], second["total"], second["streak"]) == ("done", 20.0, 1)

    today = browser.get("/api/v1/today").json()
    assert today["day"] == "2026-11-10"
    assert today["deadline"] == "2026-11-10T22:00:00Z"
    assert [c["title"] for c in today["challenges"]] == ["Read"]
    assert {r["member"]["display_name"]: r["done"] for r in today["crew"]} == {
        "Ana": 0,
        "Bogdan": 1,
    }

    undone = browser.delete(f"/api/v1/challenges/{read.pk}/check-ins/2026-11-10/last").json()
    assert (undone["state"], undone["total"]) == ("partial", 12.0)


def test_yesterday_is_closed(browser, setup):
    _, member, read = setup
    browser.force_login(member.user)
    response = browser.post(
        f"/api/v1/challenges/{read.pk}/check-ins", {"day": "2026-11-09", "amount": 5}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "day_closed"
    bad = browser.delete(f"/api/v1/challenges/{read.pk}/check-ins/yesterday/last")
    assert bad.status_code == 400


def test_board(browser, setup):
    _, member, read = setup
    browser.force_login(member.user)
    body = browser.get(f"/api/v1/challenges/{read.pk}/board?month=2026-11").json()
    assert len(body["days"]) == 30
    assert sorted(r["member"]["display_name"] for r in body["rows"]) == ["Ana", "Bogdan"]
    assert browser.get(f"/api/v1/challenges/{read.pk}/board").status_code == 200
    assert browser.get(f"/api/v1/challenges/{read.pk}/board?month=nov").status_code == 400
    browser.force_login(AdminFactory.create().user)
    assert browser.get(f"/api/v1/challenges/{read.pk}/board").status_code == 404


def test_not_taking_part_answers_403(browser, setup):
    admin, _, read = setup
    browser.force_login(admin.user)
    challenges.stop_taking_part(by=admin, challenge_id=read.pk)  # today is the last day
    with time_machine.travel("2026-11-11 08:00Z", tick=False):
        response = browser.post(
            f"/api/v1/challenges/{read.pk}/check-ins",
            {"day": "2026-11-11", "amount": 5},
            format="json",
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_taking_part"
