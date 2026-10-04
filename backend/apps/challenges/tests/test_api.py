import pytest
import time_machine

from apps.challenges import services
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

SHAPE = {
    "title": "Run 20 km a week",
    "icon": "running",
    "measure": "quantity",
    "unit": "km",
    "frequency": "times_per_week",
    "times": 3,
    "target_scope": "per_week",
    "target_value": "20",
    "proof_kind": "photo_or_video",
    "proof_required": False,
}


@pytest.fixture(autouse=True)
def october():
    with time_machine.travel("2026-10-10 12:00Z", tick=False):
        yield


@pytest.fixture
def people():
    admin = AdminFactory.create(display_name="Ana")
    member = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
    return admin, member


def as_member(client, member):
    client.force_login(member.user)
    return client


def test_propose_vote_and_read_the_round(browser, people):
    admin, member = people
    client = as_member(browser, member)
    created = client.post("/api/v1/challenges", SHAPE, format="json")
    assert created.status_code == 201
    body = created.json()
    assert body["created_by"]["display_name"] == "Bogdan"
    assert body["state"] == "proposed"
    assert body["phase"] is None
    assert body["target_value"] == 20.0
    assert body["times"] == 3

    voted = client.put(
        f"/api/v1/rounds/{body['round_id']}/vote", {"challenge_id": body["id"]}, format="json"
    )
    assert voted.status_code == 200
    round_ = client.get("/api/v1/rounds/current").json()
    assert round_["period_start"] == "2026-11-01"
    assert round_["state"] == "open"
    assert round_["my_vote"] == body["id"]
    assert round_["votes_cast"] == 1
    [proposal] = round_["proposals"]
    assert proposal["vote_count"] == 1
    assert proposal["voters"][0]["display_name"] == "Bogdan"
    assert proposal["mine"] is True

    cleared = client.delete(f"/api/v1/rounds/{body['round_id']}/vote")
    assert cleared.json()["my_vote"] is None


def test_invalid_shapes_return_field_errors(browser, people):
    _, member = people
    response = as_member(browser, member).post(
        "/api/v1/challenges", {**SHAPE, "unit": ""}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
    assert "unit" in response.json()["error"]["fields"]


def test_edit_resets_votes_and_delete_withdraws(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    client = as_member(browser, member)
    edited = client.put(
        f"/api/v1/challenges/{proposal.pk}", {**SHAPE, "title": "Run 25 km"}, format="json"
    )
    assert edited.status_code == 200
    assert edited.json()["revision"] == 2
    assert client.get("/api/v1/rounds/current").json()["votes_cast"] == 0

    assert client.delete(f"/api/v1/challenges/{proposal.pk}").status_code == 204
    assert client.get("/api/v1/rounds/current").json()["proposals"] == []
    assert client.get(f"/api/v1/challenges/{proposal.pk}").status_code == 404


def test_only_the_creator_edits(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    response = as_member(browser, admin).put(
        f"/api/v1/challenges/{proposal.pk}", SHAPE, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_your_proposal"


def test_admin_chooses_and_everyone_sees_it(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    refused = as_member(browser, member).put(
        f"/api/v1/rounds/{proposal.round_id}/choice",
        {"challenge_id": str(proposal.pk)},
        format="json",
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "not_crew_admin"

    chosen = as_member(browser, admin).put(
        f"/api/v1/rounds/{proposal.round_id}/choice",
        {"challenge_id": str(proposal.pk)},
        format="json",
    )
    assert chosen.status_code == 200
    body = chosen.json()
    assert body["state"] == "closed"
    assert body["chosen_id"] == str(proposal.pk)
    assert body["chosen_by"]["display_name"] == "Ana"

    detail = browser.get(f"/api/v1/challenges/{proposal.pk}").json()
    assert detail["phase"] == "upcoming"
    assert detail["start_date"] == "2026-11-01"
    assert detail["taking_part"] is True
    assert [p["member"]["display_name"] for p in detail["participants"]] == ["Ana", "Bogdan"]
    assert [c["id"] for c in browser.get("/api/v1/challenges?phase=upcoming").json()] == [
        str(proposal.pk)
    ]
    assert browser.get("/api/v1/challenges?phase=active").json() == []
    assert browser.get(f"/api/v1/rounds/{proposal.round_id}").json()["chosen_id"] == str(
        proposal.pk
    )
    # The next round is open for proposals.
    assert browser.get("/api/v1/rounds/current").json()["period_start"] == "2026-12-01"


def test_choice_must_be_from_that_round(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    other_round = services.open_round(crew=admin.crew)
    services.choose_challenge(by=admin, challenge_id=proposal.pk)
    december = services.open_round(crew=admin.crew)
    assert december != other_round
    response = as_member(browser, admin).put(
        f"/api/v1/rounds/{december.pk}/choice", {"challenge_id": str(proposal.pk)}, format="json"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "challenge_not_found"


def test_opt_out_and_back_in(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    services.choose_challenge(by=admin, challenge_id=proposal.pk)
    client = as_member(browser, member)
    out = client.delete(f"/api/v1/challenges/{proposal.pk}/participation").json()
    assert out["taking_part"] is False
    assert [p["member"]["display_name"] for p in out["participants"]] == ["Ana"]
    back = client.put(f"/api/v1/challenges/{proposal.pk}/participation").json()
    assert back["taking_part"] is True


def test_repropose_copies_into_the_open_round(browser, people):
    admin, member = people
    chosen = services.propose_challenge(by=member, shape=SHAPE)
    lost = services.propose_challenge(by=admin, shape={**SHAPE, "title": "Swim"})
    services.choose_challenge(by=admin, challenge_id=chosen.pk)
    response = as_member(browser, member).post(f"/api/v1/challenges/{lost.pk}/repropose")
    assert response.status_code == 201
    assert response.json()["title"] == "Swim"
    assert response.json()["created_by"]["display_name"] == "Bogdan"


def test_other_crews_get_404(browser, people):
    _, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    stranger = as_member(browser, AdminFactory.create())
    assert stranger.get(f"/api/v1/challenges/{proposal.pk}").status_code == 404
    assert stranger.get(f"/api/v1/rounds/{proposal.round_id}").status_code == 404
    vote = stranger.put(
        f"/api/v1/rounds/{proposal.round_id}/vote",
        {"challenge_id": str(proposal.pk)},
        format="json",
    )
    assert vote.status_code == 404


def test_needs_a_crew(auth_client):
    assert auth_client.get("/api/v1/rounds/current").status_code == 403
