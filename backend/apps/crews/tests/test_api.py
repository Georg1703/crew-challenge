from datetime import timedelta

import pytest
import time_machine
from rest_framework.test import APIClient

from apps.core import clock
from apps.crews import services
from apps.crews.models import Invite
from tests.factories import AdminFactory, InviteFactory, MemberFactory, UserFactory

pytestmark = pytest.mark.django_db

STRONG = "garden-flame-2026"


def logged_in(client, member):
    client.force_login(member.user)
    return client


# --- /me -------------------------------------------------------------------------------------


def test_me_requires_login(api_client):
    response = api_client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_returns_user_member_and_crew(api_client):
    member = MemberFactory.create(display_name="Ana", user__username="ana")
    body = logged_in(api_client, member).get("/api/v1/me").json()
    assert body["user"] == {
        "id": str(member.user.id),
        "username": "ana",
        "preferred_language": "ro",
    }
    assert body["member"]["display_name"] == "Ana"
    assert body["crew"]["timezone"] == "Europe/Chisinau"


def test_me_outside_a_crew(auth_client):
    body = auth_client.get("/api/v1/me").json()
    assert body["member"] is None
    assert body["crew"] is None


def test_me_update(auth_client, user):
    member = MemberFactory.create(user=user)
    response = auth_client.patch(
        "/api/v1/me", {"display_name": "Tata", "preferred_language": "en"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["member"]["display_name"] == "Tata"
    assert response.json()["user"]["preferred_language"] == "en"
    member.refresh_from_db()
    assert member.display_name == "Tata"


def test_me_update_display_name_needs_a_crew(auth_client):
    response = auth_client.patch("/api/v1/me", {"display_name": "Tata"}, format="json")
    assert response.status_code == 400
    assert "display_name" in response.json()["error"]["fields"]


# --- /crew -----------------------------------------------------------------------------------


def test_crew_lists_members_in_join_order(api_client):
    admin = AdminFactory.create()
    second = MemberFactory.create(crew=admin.crew)
    MemberFactory.create()  # another crew, must not appear
    body = logged_in(api_client, second).get("/api/v1/crew").json()
    assert [m["id"] for m in body["members"]] == [str(admin.id), str(second.id)]
    assert "rotation_position" not in body["members"][0]


def test_crew_requires_membership(auth_client):
    response = auth_client.get("/api/v1/crew")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_member"


# --- invites ---------------------------------------------------------------------------------


def test_admin_creates_an_invite_link(browser, settings):
    settings.APP_PUBLIC_URL = "https://crew.example.com/"
    response = logged_in(browser, AdminFactory.create()).post("/api/v1/crew/invites")
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == f"https://crew.example.com/join/{body['code']}"


def test_member_cannot_create_invites(browser):
    response = logged_in(browser, MemberFactory.create()).post("/api/v1/crew/invites")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_admin"


@pytest.mark.parametrize("state", ["valid", "used", "expired"])
def test_invite_preview(api_client, state):
    invite = InviteFactory.create(created_by__crew__name="Familia")
    if state == "used":
        Invite.objects.filter(pk=invite.pk).update(used_at=clock.now())
    if state == "expired":
        Invite.objects.filter(pk=invite.pk).update(expires_at=clock.now() - timedelta(seconds=1))
    body = api_client.get(f"/api/v1/invites/{invite.code}").json()
    assert body["crew_name"] == "Familia"
    assert body["status"] == state
    if state == "valid":
        admin = invite.created_by
        assert admin is not None
        assert body["invited_by"] == {
            "display_name": admin.display_name,
            "avatar_seed": admin.avatar_seed,
        }
        assert [m["display_name"] for m in body["members"]] == [admin.display_name]
    else:
        # A used or expired link does not tell strangers who is in the crew.
        assert body["invited_by"] is None
        assert body["members"] == []


def test_invite_preview_is_rate_limited(api_client):
    for _ in range(30):  # REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["invite_preview"]
        api_client.get("/api/v1/invites/guess")
    assert api_client.get("/api/v1/invites/guess").status_code == 429


def test_admin_lists_pending_invites(browser, settings):
    settings.APP_PUBLIC_URL = "https://crew.example.com"
    admin = AdminFactory.create(display_name="Ana")
    client = logged_in(browser, admin)
    created = client.post("/api/v1/crew/invites").json()
    InviteFactory.create()  # another crew
    body = client.get("/api/v1/crew/invites").json()
    assert len(body) == 1
    assert body[0]["code"] == created["code"]
    assert body[0]["url"] == created["url"]
    assert body[0]["created_by"]["display_name"] == "Ana"
    assert "id" in body[0]


def test_member_cannot_list_invites(browser):
    response = logged_in(browser, MemberFactory.create()).get("/api/v1/crew/invites")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_admin"


def test_admin_revokes_an_invite(browser):
    admin = AdminFactory.create()
    client = logged_in(browser, admin)
    client.post("/api/v1/crew/invites")
    invite_id = client.get("/api/v1/crew/invites").json()[0]["id"]
    assert client.delete(f"/api/v1/crew/invites/{invite_id}").status_code == 204
    assert client.get("/api/v1/crew/invites").json() == []
    missing = client.delete(f"/api/v1/crew/invites/{invite_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "invite_not_found"


def test_member_cannot_revoke_invites(browser):
    invite = InviteFactory.create()
    member = MemberFactory.create(crew=invite.crew)
    response = logged_in(browser, member).delete(f"/api/v1/crew/invites/{invite.id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_admin"


def test_unknown_invite_preview(api_client):
    response = api_client.get("/api/v1/invites/doesnotexist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "invite_not_found"


def _join(client, code, **overrides):
    payload = {"username": "cristina", "password": STRONG, "display_name": "Cris", **overrides}
    return client.post(f"/api/v1/invites/{code}/accept", payload, format="json")


def test_joining_creates_the_account_logs_in_and_lands_in_the_crew(browser):
    invite = InviteFactory.create()
    response = _join(browser, invite.code)
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "cristina"
    assert body["crew"]["id"] == str(invite.crew_id)
    # The session is live: the new member can see the crew right away.
    assert browser.get("/api/v1/crew").status_code == 200


def test_joining_needs_a_csrf_token(api_client):
    response = _join(api_client, InviteFactory.create().code)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_joining_reports_field_errors(browser):
    UserFactory.create(username="cristina")
    response = _join(browser, InviteFactory.create().code, password="123")
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "username_taken"
    assert "username" in error["fields"]


def test_joining_with_an_expired_invite(browser):
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        invite = InviteFactory.create()
    with time_machine.travel("2026-11-09 12:00Z", tick=False):
        response = _join(browser, invite.code)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invite_expired"


def test_signed_in_users_cannot_join_with_a_new_account(browser):
    client = logged_in(browser, MemberFactory.create())
    response = _join(client, InviteFactory.create().code)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_signed_in"


def test_signed_in_user_joins_with_their_account(browser):
    elsewhere = MemberFactory.create(display_name="Eva")
    invite = InviteFactory.create()
    client = logged_in(browser, elsewhere)
    response = client.post(
        f"/api/v1/invites/{invite.code}/join", {"display_name": "Eva"}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["crew"]["id"] == str(invite.crew_id)
    assert body["member"]["display_name"] == "Eva"
    # The session now acts in the new crew.
    assert client.get("/api/v1/crew").json()["id"] == str(invite.crew_id)


def test_joining_with_an_account_needs_login(browser):
    invite = InviteFactory.create()
    response = browser.post(
        f"/api/v1/invites/{invite.code}/join", {"display_name": "X"}, format="json"
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_members_cannot_join_their_own_crew_again(browser):
    invite = InviteFactory.create()
    response = logged_in(browser, invite.created_by).post(
        f"/api/v1/invites/{invite.code}/join", {"display_name": "Twice"}, format="json"
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_member"


# --- several crews -----------------------------------------------------------------------------


def test_me_lists_every_crew_and_switching_changes_the_active_one(browser):
    first = MemberFactory.create(crew__name="Alpha")
    second = services.join_with_account(
        user=first.user,
        code=InviteFactory.create(created_by__crew__name="Beta").code,
        display_name="Me",
    )
    client = logged_in(browser, first)
    body = client.get("/api/v1/me").json()
    assert [c["crew_name"] for c in body["crews"]] == ["Alpha", "Beta"]
    assert body["crew"]["id"] == str(second.crew_id)  # joined most recently

    response = client.put("/api/v1/me/crew", {"crew_id": str(first.crew_id)}, format="json")
    assert response.status_code == 200
    assert response.json()["crew"]["id"] == str(first.crew_id)
    assert client.get("/api/v1/crew").json()["name"] == "Alpha"


def test_the_chosen_crew_opens_after_the_next_login(api_client, browser):
    first = MemberFactory.create(crew__name="Alpha")
    services.join_with_account(user=first.user, code=InviteFactory.create().code, display_name="Me")
    logged_in(browser, first).put("/api/v1/me/crew", {"crew_id": str(first.crew_id)}, format="json")

    other_device = APIClient(enforce_csrf_checks=True)
    other_device.force_login(first.user)
    assert other_device.get("/api/v1/crew").json()["name"] == "Alpha"


def test_switching_to_a_crew_you_are_not_in(browser):
    member = MemberFactory.create()
    stranger_crew = MemberFactory.create().crew
    response = logged_in(browser, member).put(
        "/api/v1/me/crew", {"crew_id": str(stranger_crew.id)}, format="json"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "crew_not_found"


def test_preview_tells_members_they_are_already_in(browser, api_client):
    invite = InviteFactory.create()
    anonymous = api_client.get(f"/api/v1/invites/{invite.code}").json()
    assert anonymous["already_member"] is False
    assert anonymous["crew_id"] is None

    member = logged_in(browser, invite.created_by).get(f"/api/v1/invites/{invite.code.upper()}")
    assert member.json()["already_member"] is True
    assert member.json()["crew_id"] == str(invite.crew_id)


def test_joining_keeps_the_sign_up_language(browser):
    response = _join(browser, InviteFactory.create().code, preferred_language="en")
    assert response.json()["user"]["preferred_language"] == "en"
