from datetime import timedelta

import pytest
import time_machine

from apps.core import clock
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


def test_crew_lists_members_in_rotation_order(api_client):
    admin = AdminFactory.create()
    second = MemberFactory.create(crew=admin.crew)
    MemberFactory.create()  # another crew, must not appear
    body = logged_in(api_client, second).get("/api/v1/crew").json()
    assert [m["id"] for m in body["members"]] == [str(admin.id), str(second.id)]
    assert body["reveal_time"] == "20:00:00"


def test_crew_requires_membership(auth_client):
    response = auth_client.get("/api/v1/crew")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_member"


def test_admin_reorders_rotation(browser):
    admin = AdminFactory.create()
    other = MemberFactory.create(crew=admin.crew)
    response = logged_in(browser, admin).patch(
        "/api/v1/crew/rotation", {"member_ids": [str(other.id), str(admin.id)]}, format="json"
    )
    assert response.status_code == 200
    assert [m["id"] for m in response.json()["members"]] == [str(other.id), str(admin.id)]


def test_member_cannot_reorder_rotation(browser):
    admin = AdminFactory.create()
    other = MemberFactory.create(crew=admin.crew)
    response = logged_in(browser, other).patch(
        "/api/v1/crew/rotation", {"member_ids": [str(other.id), str(admin.id)]}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_crew_admin"


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
    assert body["member"]["rotation_position"] == 1
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
