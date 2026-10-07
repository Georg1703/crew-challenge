import pytest

from tests.factories import MemberFactory

pytestmark = pytest.mark.django_db

FIRE = "\U0001f525"


def test_react_and_take_back_over_http(browser, member_target):
    ana = MemberFactory.create()
    bogdan = MemberFactory.create(crew=ana.crew)
    browser.force_login(ana.user)
    url = f"/api/v1/reactions/{member_target}/{bogdan.pk}"

    set_ = browser.put(url, {"emoji": FIRE}, format="json")
    assert set_.status_code == 200
    assert set_.json() == {"groups": [{"emoji": FIRE, "member_ids": [str(ana.pk)]}], "mine": FIRE}

    cleared = browser.delete(url)
    assert cleared.json() == {"groups": [], "mine": None}


def test_errors_use_stable_codes(browser, member_target):
    ana = MemberFactory.create()
    browser.force_login(ana.user)

    bad = browser.put(f"/api/v1/reactions/{member_target}/{ana.pk}", {"emoji": "hi"}, format="json")
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_emoji"
    assert "emoji" in bad.json()["error"]["fields"]

    unknown = browser.put(f"/api/v1/reactions/nothing/{ana.pk}", {"emoji": FIRE}, format="json")
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "target_not_found")


def test_only_crew_members_react(browser, member_target):
    ana = MemberFactory.create()
    response = browser.put(
        f"/api/v1/reactions/{member_target}/{ana.pk}", {"emoji": FIRE}, format="json"
    )
    assert response.status_code in (401, 403)
