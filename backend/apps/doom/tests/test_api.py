from datetime import date

import pytest

from apps.doom import services
from apps.doom.models import Spin
from apps.doom.tests.test_services import Pick, at, check_in, scheduled

pytestmark = pytest.mark.django_db


@pytest.fixture
def owed(crew):
    """Bogdan swam once in the week of November 2: two spins, on Monday the 9th."""
    ana, bogdan = crew
    challenge = scheduled(ana, bogdan, date(2026, 11, 2))
    check_in(bogdan, challenge, date(2026, 11, 2))
    with at("2026-11-08 22:01Z"):
        services.open_spins()
    with at("2026-11-09 08:00Z"):
        yield ana, bogdan, challenge


def test_my_spins_draw_and_done(browser, owed):
    ana, bogdan, _ = owed
    browser.force_login(bogdan.user)
    body = browser.get("/api/v1/spins").json()
    assert (body["to_spin"], body["to_serve"]) == (2, 0)
    first = body["spins"][0]
    assert (first["state"], first["punishment"], first["need"], first["done"]) == (
        "pending",
        None,
        3.0,
        1.0,
    )
    assert [p["position"] for p in first["punishments"]] == [1, 2]

    spin = Spin.objects.get(pk=first["id"])
    services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(1))  # "No phone": no proof
    drawn = browser.post(f"/api/v1/spins/{spin.pk}/draw").json()  # a second tap: the same
    assert (drawn["state"], drawn["punishment"]["position"], drawn["serve_by"]) == (
        "spun",
        2,
        "2026-11-16",
    )
    proof = {"kind": "photo", "content_type": "image/jpeg", "size": 4}
    refused = browser.post(f"/api/v1/spins/{spin.pk}/proofs", proof, format="json")
    assert (refused.status_code, refused.json()["error"]["code"]) == (409, "proof_not_needed")
    done = browser.post(f"/api/v1/spins/{spin.pk}/done").json()
    assert done["state"] == "served"
    assert browser.get("/api/v1/spins").json()["to_spin"] == 1

    browser.force_login(ana.user)
    assert browser.post(f"/api/v1/spins/{spin.pk}/draw").status_code == 404


def test_proof_on_a_spin_starts_and_resumes(browser, owed, object_storage):
    _, bogdan, _ = owed
    browser.force_login(bogdan.user)
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    services.draw(by=bogdan, spin_id=spin.pk, rng=Pick(0))  # "20 burpees": needs proof
    video = {"kind": "video", "content_type": "video/mp4", "size": 10, "fingerprint": "a|10|1"}
    started = browser.post(f"/api/v1/spins/{spin.pk}/proofs", video, format="json")
    assert started.status_code == 201
    resume = f"/api/v1/spins/{spin.pk}/proofs/resume?fingerprint="
    assert browser.get(f"{resume}a|10|1").json()["proof"]["id"] == started.json()["proof"]["id"]
    assert browser.get(f"{resume}b").status_code == 404
    assert browser.post(f"/api/v1/spins/{spin.pk}/done").json()["error"]["code"] == "proof_needed"


def test_the_crew_reacts_to_a_drawn_spin(browser, owed):
    ana, bogdan, _ = owed
    spin = Spin.objects.filter(member=bogdan).first()
    assert spin is not None
    browser.force_login(ana.user)
    url = f"/api/v1/reactions/spin/{spin.pk}"
    assert browser.put(url, {"emoji": "\U0001f525"}, format="json").status_code == 404  # not drawn
    services.draw(by=bogdan, spin_id=spin.pk)
    assert browser.put(url, {"emoji": "\U0001f525"}, format="json").status_code == 200
