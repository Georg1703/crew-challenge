import pytest

from apps.crews import targets
from apps.crews.models import Member
from apps.reactions import services as reactions
from tests.factories import MemberFactory, UserFactory

pytestmark = pytest.mark.django_db

FIRE = "\U0001f525"


@pytest.fixture
def person():
    targets.register(
        targets.Target(
            key="person",
            model=Member,
            visible=lambda m: Member.objects.filter(crew=m.crew),
            owner="pk",
        )
    )
    yield "person"
    targets.unregister("person")


def test_news_over_http(browser, person):
    ana = MemberFactory.create()
    bogdan = MemberFactory.create(crew=ana.crew)
    reactions.react(member=bogdan, target=person, target_id=ana.pk, emoji=FIRE)
    browser.force_login(ana.user)

    page = browser.get("/api/v1/notifications").json()
    assert page["unread"] == 1
    (row,) = page["results"]
    assert (row["kind"], row["actor"]["id"], row["read_at"]) == ("reaction", str(bogdan.pk), None)
    assert row["target"] == {"type": person, "id": str(ana.pk)}
    assert row["facts"] == {"emoji": FIRE, "on": person}
    assert browser.get(f"/api/v1/notifications?before={row['created_at']}").json()["results"] == []
    assert browser.get("/api/v1/notifications?before=yesterday").status_code == 400

    assert browser.put("/api/v1/notifications/read").status_code == 204
    again = browser.get("/api/v1/notifications").json()
    assert (again["unread"], again["results"][0]["read_at"] is not None) == (0, True)


def test_news_needs_a_crew(browser):
    assert browser.get("/api/v1/notifications").status_code == 401
    browser.force_login(UserFactory.create())
    assert browser.get("/api/v1/notifications").status_code == 403


def test_push_subscriptions_over_http(browser, settings):
    user = UserFactory.create()
    browser.force_login(user)
    assert browser.get("/api/v1/push/key").json() == {"public_key": "test-public-key"}

    body = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "p", "auth": "a"}}
    assert browser.put("/api/v1/push/subscriptions", body, format="json").status_code == 204
    assert user.push_subscriptions.get().endpoint == body["endpoint"]
    bad = browser.put("/api/v1/push/subscriptions", {"endpoint": "nope"}, format="json")
    assert bad.status_code == 400
    assert browser.delete("/api/v1/push/subscriptions").status_code == 400
    gone = browser.delete(f"/api/v1/push/subscriptions?endpoint={body['endpoint']}")
    assert (gone.status_code, user.push_subscriptions.exists()) == (204, False)

    settings.PUSH_BACKEND = "off"
    assert browser.get("/api/v1/push/key").json() == {"public_key": ""}


def test_push_needs_a_login(browser):
    assert browser.get("/api/v1/push/key").status_code == 401
