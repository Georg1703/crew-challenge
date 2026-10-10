from datetime import date

import pytest
import time_machine

from apps.challenges import services as challenges
from apps.checkins import services
from apps.media.models import MiB
from apps.proofs import services as proofs
from apps.proofs.models import Proof
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

READ = {
    "title": "Read",
    "measure": "quantity",
    "unit": "pages",
    "day_min": 20,
}


@pytest.fixture
def setup():
    with time_machine.travel("2026-10-10 12:00Z", tick=False):
        admin = AdminFactory.create(display_name="Ana")
        member = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        read = challenges.propose_challenge(by=member, shape=READ)
        challenges.schedule_challenge(
            by=admin, challenge_id=read.pk, period_start=date(2026, 11, 1)
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


def start(browser, read, **body):
    url = f"/api/v1/challenges/{read.pk}/check-ins/2026-11-10/proofs"
    return browser.post(url, body, format="json")


def test_photo_proof_over_http(browser, setup, object_storage):
    admin, member, read = setup
    browser.force_login(member.user)
    response = start(browser, read, kind="photo", content_type="image/jpeg", size=4, thumb_size=2)

    assert response.status_code == 201
    body = response.json()
    assert (body["mode"], body["part_size"], body["parts"]) == ("single", None, [])
    assert body["put_url"]
    assert body["thumb_put_url"]
    assert (body["proof"]["status"], body["proof"]["url"]) == ("uploading", None)
    proof_id = body["proof"]["id"]
    for name, data in (("original.jpg", b"jpeg"), ("thumb.jpg", b"tn")):
        key = f"crews/{member.crew_id}/proofs/{proof_id}/{name}"
        object_storage.put_object(key=key, data=data, content_type="image/jpeg")

    done = browser.post(f"/api/v1/proofs/{proof_id}/complete").json()
    assert (done["status"], bool(done["url"]), bool(done["thumb_url"])) == ("ready", True, True)
    card = browser.get("/api/v1/today").json()["challenges"][0]
    assert [(p["id"], p["posted"]) for p in card["proofs"]] == [(proof_id, False)]  # a draft
    assert card["proof_days"] == []

    posted = browser.post(
        f"/api/v1/challenges/{read.pk}/check-ins", {"day": "2026-11-10", "amount": 5}, format="json"
    ).json()
    assert ([p["posted"] for p in posted["proofs"]], posted["proof_days"]) == (
        [True],
        ["2026-11-10"],
    )
    board = browser.get(f"/api/v1/challenges/{read.pk}/board").json()
    assert {r["member"]["display_name"]: r["proof_days"] for r in board["rows"]} == {
        "Ana": [],
        "Bogdan": ["2026-11-10"],
    }

    browser.force_login(admin.user)  # someone else's proof is not found
    assert browser.delete(f"/api/v1/proofs/{proof_id}").json()["error"]["code"] == (
        "proof_not_found"
    )
    browser.force_login(member.user)
    kept = browser.delete(f"/api/v1/proofs/{proof_id}")
    assert (kept.status_code, kept.json()["error"]["code"]) == (409, "proof_posted")
    draft = start(browser, read, kind="photo", content_type="image/jpeg", size=4).json()
    assert browser.delete(f"/api/v1/proofs/{draft['proof']['id']}").status_code == 204


def test_video_proof_resumes_over_http(browser, setup, object_storage, transcoder):
    _, member, read = setup
    browser.force_login(member.user)
    check_in = {"day": "2026-11-10", "amount": 5}
    browser.post(f"/api/v1/challenges/{read.pk}/check-ins", check_in, format="json")
    body = start(
        browser,
        read,
        kind="video",
        content_type="video/mp4",
        size=10,
        fingerprint="a.mp4|10|1",
        thumb_size=2,
    ).json()
    assert (body["mode"], body["put_url"], body["part_size"], body["part_count"]) == (
        "multipart",
        None,
        16 * MiB,
        1,
    )
    proof_id = body["proof"]["id"]

    signed = browser.post(f"/api/v1/proofs/{proof_id}/parts", {"numbers": [1]}, format="json")
    assert [p["number"] for p in signed.json()["parts"]] == [1]
    upload_id, upload = next(iter(object_storage.uploads.items()))  # the browser's PUT
    etag = object_storage.upload_part(
        key=upload.key, upload_id=upload_id, part_number=1, data=b"x" * 10
    )
    reported = browser.put(f"/api/v1/proofs/{proof_id}/parts/1", {"etag": etag}, format="json")
    assert reported.status_code == 204

    resume = f"/api/v1/challenges/{read.pk}/check-ins/proofs/resume?fingerprint="
    resumed = browser.get(f"{resume}a.mp4|10|1").json()
    assert resumed["parts"] == [{"number": 1, "etag": etag}]
    assert browser.get(f"{resume}b").status_code == 404
    thumb = Proof.objects.get(pk=proof_id).thumb  # the phone's frame, PUT by the browser
    assert thumb is not None
    object_storage.put_object(key=thumb.key, data=b"tn", content_type="image/jpeg")
    done = browser.post(f"/api/v1/proofs/{proof_id}/complete").json()
    assert (done["status"], done["hls_url"]) == ("processing", None)  # renditions on their way
    assert "thumb" in done["thumb_url"]  # meanwhile the phone's frame stands in

    proofs.finish_videos()  # starts the job
    prefix = upload.key.rsplit(".", 1)[0]
    object_storage.put_object(
        key=f"{prefix}/poster.0000000.jpg", data=b"j" * 10_000, content_type="image/jpeg"
    )
    transcoder.finish(next(iter(transcoder.jobs)))
    proofs.finish_videos()
    shown = browser.get("/api/v1/today").json()["challenges"][0]["proofs"][0]
    assert shown["status"] == "ready"
    assert "poster" in shown["thumb_url"]  # the server's poster wins over the phone's frame
    assert "thumb" in shown["phone_thumb_url"]  # the fallback when the poster will not load
    assert shown["hls_url"] is None  # locally the original plays


def test_proof_input_is_checked(browser, setup):
    _, member, read = setup
    browser.force_login(member.user)
    bad_day = browser.post(
        f"/api/v1/challenges/{read.pk}/check-ins/today/proofs",
        {"kind": "photo", "content_type": "image/jpeg", "size": 4},
        format="json",
    )
    assert bad_day.status_code == 400
    assert start(browser, read, kind="audio", content_type="audio/mp4", size=4).status_code == 400


def test_windows_show_what_each_week_asks_for(browser):
    swim = {
        "title": "Swim",
        "measure": "check",
        "window": "week",
        "need_value": 3,
        "period_kind": "day",
        "period_length": 10,
    }
    with time_machine.travel("2026-10-10 12:00Z", tick=False):
        admin = AdminFactory.create(display_name="Ana")
        member = MemberFactory.create(crew=admin.crew, display_name="Bogdan")
        challenge = challenges.propose_challenge(by=member, shape=swim, participant_ids=[member.pk])
        url = f"/api/v1/challenges/{challenge.pk}/windows"
        browser.force_login(admin.user)
        assert browser.get(url).json() == []  # a proposal has no dates yet
        preview = browser.get(f"{url}?start=2026-11-05").json()  # a Thursday
        assert [
            (w["first"], w["last"], w["need"], w["full_need"], w["state"]) for w in preview
        ] == [
            ("2026-11-05", "2026-11-08", 2.0, 3.0, None),
            ("2026-11-09", "2026-11-14", 3.0, 3.0, None),
        ]
        assert browser.get(f"{url}?start=soon").status_code == 400
        challenges.schedule_challenge(
            by=admin, challenge_id=challenge.pk, period_start=date(2026, 11, 5)
        )
    with time_machine.travel("2026-11-06 08:00Z", tick=False):
        services.check_in(by=member, challenge_id=challenge.pk, day=date(2026, 11, 6))
        watching = browser.get(url).json()  # Ana sees the weeks but doesn't take part
        assert [(w["need"], w["done"], w["state"]) for w in watching] == [
            (2.0, None, None),
            (3.0, None, None),
        ]

        browser.force_login(member.user)
        mine = browser.get(url).json()
        assert [(w["done"], w["state"]) for w in mine] == [(1.0, "open"), (0.0, "future")]
        leaving = browser.get(f"{url}?until=2026-11-06").json()  # Thursday and Friday
        assert [(w["last"], w["need"], w["state"]) for w in leaving] == [("2026-11-06", 1.0, "met")]
        card = browser.get("/api/v1/today").json()["challenges"][0]
        assert card["current"] == {
            "first": "2026-11-05",
            "last": "2026-11-08",
            "need": 2.0,
            "full_need": 3.0,
            "done": 1.0,
            "state": "open",
        }

        browser.force_login(AdminFactory.create().user)
        assert browser.get(url).status_code == 404
