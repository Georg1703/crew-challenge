from datetime import date

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
    "window": "week",
    "need_kind": "amount",
    "need_value": "20",
    "proof_required": True,
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


NOVEMBER = {"period_start": "2026-11-01"}


def schedule(admin, challenge, start=date(2026, 11, 1)):
    services.schedule_challenge(by=admin, challenge_id=challenge.pk, period_start=start)


def test_propose_vote_and_read_the_pool(browser, people):
    admin, member = people
    client = as_member(browser, member)
    created = client.post("/api/v1/challenges", SHAPE, format="json")
    assert created.status_code == 201
    body = created.json()
    assert body["created_by"]["display_name"] == "Bogdan"
    assert (body["state"], body["phase"], body["start_date"]) == ("proposed", None, None)
    assert (body["period_kind"], body["period_length"]) == ("month", 1)  # the default length
    assert (body["window"], body["on_days"], body["need_kind"], body["need_value"]) == (
        "week",
        [],
        "amount",
        20.0,
    )
    assert body["day_min"] is None
    assert (body["vote_count"], body["my_vote"], body["mine"]) == (0, False, True)

    voted = client.put(f"/api/v1/challenges/{body['id']}/vote")
    assert voted.status_code == 200
    assert (voted.json()["vote_count"], voted.json()["my_vote"]) == (1, True)
    pool = client.get("/api/v1/proposals").json()
    assert (pool["size"], pool["limit"]) == (1, 50)
    [proposal] = pool["proposals"]
    assert proposal["voters"][0]["display_name"] == "Bogdan"
    assert proposal["my_vote"] is True

    as_admin = as_member(browser, admin).get("/api/v1/proposals").json()["proposals"][0]
    assert (as_admin["my_vote"], as_admin["mine"]) == (False, False)
    cleared = as_member(browser, member).delete(f"/api/v1/challenges/{body['id']}/vote")
    assert (cleared.json()["vote_count"], cleared.json()["my_vote"]) == (0, False)


def test_invalid_shapes_return_field_errors(browser, people):
    _, member = people
    response = as_member(browser, member).post(
        "/api/v1/challenges", {**SHAPE, "unit": ""}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
    assert "unit" in response.json()["error"]["fields"]


def test_a_full_pool_answers_409(browser, people):
    admin, member = people
    admin.crew.max_proposals = 1
    admin.crew.save()
    services.propose_challenge(by=admin, shape=SHAPE)
    response = as_member(browser, member).post("/api/v1/challenges", SHAPE, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "pool_full"


def test_edit_resets_votes_and_delete_withdraws(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    services.cast_vote(by=admin, challenge_id=proposal.pk)
    client = as_member(browser, member)
    edited = client.put(
        f"/api/v1/challenges/{proposal.pk}", {**SHAPE, "title": "Run 25 km"}, format="json"
    )
    assert edited.status_code == 200
    assert (edited.json()["revision"], edited.json()["vote_count"]) == (2, 0)

    assert client.delete(f"/api/v1/challenges/{proposal.pk}").status_code == 204
    assert client.get("/api/v1/proposals").json()["proposals"] == []
    assert client.get(f"/api/v1/challenges/{proposal.pk}").status_code == 404


def test_only_the_creator_edits(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    response = as_member(browser, admin).put(
        f"/api/v1/challenges/{proposal.pk}", SHAPE, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_your_proposal"


def test_admin_schedules_and_everyone_sees_it(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    url = f"/api/v1/challenges/{proposal.pk}/schedule"
    refused = as_member(browser, member).put(url, NOVEMBER, format="json")
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "not_crew_admin"

    chosen = as_member(browser, admin).put(url, NOVEMBER, format="json")
    assert chosen.status_code == 200
    body = chosen.json()
    assert (body["state"], body["phase"], body["period_kind"]) == ("chosen", "upcoming", "month")
    assert (body["period_start"], body["start_date"], body["end_date"]) == (
        "2026-11-01",
        "2026-11-01",
        "2026-11-30",
    )
    assert body["chosen_by"]["display_name"] == "Ana"
    assert body["taking_part"] is True
    assert names(body) == ["Ana", "Bogdan"]

    assert [c["id"] for c in browser.get("/api/v1/challenges?phase=upcoming").json()] == [
        str(proposal.pk)
    ]
    assert browser.get("/api/v1/challenges?phase=active").json() == []
    assert browser.get("/api/v1/proposals").json()["proposals"] == []

    vote = browser.put(f"/api/v1/challenges/{proposal.pk}/vote")
    assert vote.status_code == 409
    assert vote.json()["error"]["code"] == "not_a_proposal"

    back = browser.delete(url)
    assert back.status_code == 200
    assert back.json()["state"] == "proposed"
    assert names(back.json()) == ["Ana", "Bogdan"]  # who takes part stays as it was


@pytest.mark.parametrize(
    ("payload", "status", "code"),
    [
        ({"period_start": "2026-11-02"}, 400, "validation_failed"),  # a month starts on the 1st
        ({"period_start": "2027-12-01"}, 400, "period_too_far"),
        ({"period_start": "2026-09-01"}, 409, "period_over"),
        ({"period_start": "november"}, 400, "validation_failed"),
    ],
)
def test_bad_periods_answer_with_a_code(browser, people, payload, status, code):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    response = as_member(browser, admin).put(
        f"/api/v1/challenges/{proposal.pk}/schedule", payload, format="json"
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_opting_out_removes_the_challenge_for_the_member(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    schedule(admin, proposal)
    client = as_member(browser, member)
    url = f"/api/v1/challenges/{proposal.pk}"
    assert client.get(url).json()["taking_part"] is True
    assert client.delete(f"{url}/participation").status_code == 204
    assert client.get(url).status_code == 404
    left = as_member(browser, admin).get(url).json()
    assert [p["member"]["display_name"] for p in left["participants"]] == ["Ana"]


def test_other_crews_get_404(browser, people):
    _, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE)
    stranger = as_member(browser, AdminFactory.create())
    assert stranger.get(f"/api/v1/challenges/{proposal.pk}").status_code == 404
    assert stranger.put(f"/api/v1/challenges/{proposal.pk}/vote").status_code == 404
    response = stranger.put(f"/api/v1/challenges/{proposal.pk}/schedule", NOVEMBER, format="json")
    assert response.status_code == 404
    assert stranger.get("/api/v1/proposals").json()["proposals"] == []


def test_needs_a_crew(auth_client):
    assert auth_client.get("/api/v1/proposals").status_code == 403


def test_propose_for_some_people_and_change_the_list(browser, people):
    admin, member = people
    other = MemberFactory.create(crew=admin.crew, display_name="Cristina")
    client = as_member(browser, member)
    created = client.post(
        "/api/v1/challenges", {**SHAPE, "participant_ids": [str(other.pk)]}, format="json"
    ).json()
    # Same join time under frozen time, so compare without order.
    assert names(created) == ["Bogdan", "Cristina"]
    assert created["taking_part"] is True
    assert created["participants"][0]["left_on"] is None

    url = f"/api/v1/challenges/{created['id']}/participants"
    changed = client.put(url, {"participant_ids": [str(admin.pk)]}, format="json")
    assert changed.status_code == 200
    assert names(changed.json()) == ["Ana", "Bogdan"]

    hidden = as_member(browser, other)
    assert hidden.get(f"/api/v1/challenges/{created['id']}").status_code == 404
    assert hidden.get("/api/v1/proposals").json()["proposals"] == []
    refused = hidden.put(url, {"participant_ids": []}, format="json")
    assert refused.status_code == 404


def names(body):
    return sorted(p["member"]["display_name"] for p in body["participants"])


def test_the_whole_crew_takes_part_when_the_list_is_left_out(browser, people):
    _, member = people
    body = as_member(browser, member).post("/api/v1/challenges", SHAPE, format="json").json()
    assert names(body) == ["Ana", "Bogdan"]


def test_an_admin_who_does_not_take_part_sees_it_but_cannot_vote(browser, people):
    admin, member = people
    proposal = services.propose_challenge(by=member, shape=SHAPE, participant_ids=[])
    client = as_member(browser, admin)
    body = client.get(f"/api/v1/challenges/{proposal.pk}").json()
    assert body["taking_part"] is False
    vote = client.put(f"/api/v1/challenges/{proposal.pk}/vote")
    assert vote.status_code == 403
    assert vote.json()["error"]["code"] == "not_a_participant"


def test_strangers_cannot_take_part(browser, people):
    _, member = people
    response = as_member(browser, member).post(
        "/api/v1/challenges",
        {**SHAPE, "participant_ids": [str(AdminFactory.create().pk)]},
        format="json",
    )
    assert response.status_code == 400
    assert "participant_ids" in response.json()["error"]["fields"]


def test_a_proposal_says_how_long_and_the_admin_picks_the_monday(browser, people):
    admin, member = people
    weeks = {**SHAPE, "period_kind": "week", "period_length": 4}
    created = as_member(browser, member).post("/api/v1/challenges", weeks, format="json").json()
    assert (created["period_kind"], created["period_length"]) == ("week", 4)
    scheduled = as_member(browser, admin).put(
        f"/api/v1/challenges/{created['id']}/schedule",
        {"period_start": "2026-11-02"},
        format="json",
    )
    assert scheduled.status_code == 200
    body = scheduled.json()
    assert (body["period_start"], body["start_date"], body["end_date"]) == (
        "2026-11-02",
        "2026-11-02",
        "2026-11-29",
    )
