import logging
import uuid
from datetime import UTC, date, datetime

import pytest
import time_machine
from django.test import override_settings

from apps.challenges import services as challenges
from apps.checkins import selectors, services
from apps.checkins.models import CheckIn
from apps.core.errors import ValidationFailed
from apps.media import services as media
from apps.media.models import MiB, Transcode, Upload
from apps.proofs import services as proofs
from apps.proofs import tasks
from apps.proofs.models import Proof
from integrations.transcoding import get_transcoder
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

DAY = date(2026, 11, 10)
CLIP = "clip.mp4|16777226|1759600000000"


def at(moment: str):
    return time_machine.travel(moment, tick=False)


def scheduled(admin, by, month: date, participant_ids=None, **shape):
    challenge = challenges.propose_challenge(
        by=by,
        shape={"title": "Walk", **shape},
        participant_ids=participant_ids,
    )
    challenges.schedule_challenge(by=admin, challenge_id=challenge.pk, period_start=month)
    return challenge


@pytest.fixture
def walk():
    """Ana (admin) and Bogdan take part in Walk (photo or video) all of November 2026."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        challenge = scheduled(ana, bogdan, date(2026, 11, 1), proof_required=True)
    with at("2026-11-10 08:00Z"):
        yield ana, bogdan, challenge


def photo(member, challenge, day=DAY, size=4, thumb_size=2, content_type="image/jpeg"):
    return services.start_proof(
        by=member,
        challenge_id=challenge.pk,
        day=day,
        kind="photo",
        content_type=content_type,
        size=size,
        thumb_size=thumb_size,
    )


def video(member, challenge, size=16 * MiB + 10, content_type="video/mp4"):
    return services.start_proof(
        by=member,
        challenge_id=challenge.pk,
        day=DAY,
        kind="video",
        content_type=content_type,
        size=size,
        fingerprint=CLIP,
    )


def send(storage, plan, data=b"jpeg", thumb=b"tn"):
    """Play the browser: PUT the photo and its thumbnail straight to storage."""
    storage.put_object(key=plan.proof.original.key, data=data, content_type="image/jpeg")
    if thumb is not None and plan.proof.thumb is not None:
        storage.put_object(key=plan.proof.thumb.key, data=thumb, content_type="image/jpeg")


def check_in(member, challenge, day=DAY):
    """Post: the day's check-in with its uploaded draft files."""
    services.check_in(by=member, challenge_id=challenge.pk, day=day)


def uploaded(storage, member, challenge, day=DAY) -> Proof:
    """A photo uploaded as a draft file, not posted yet."""
    plan = photo(member, challenge, day=day)
    send(storage, plan)
    return proofs.complete_proof(by=member, proof_id=plan.proof.pk)


def test_photo_round_trip(object_storage, walk):
    _, bogdan, challenge = walk
    plan = photo(bogdan, challenge)  # before checking in: a draft file
    proof = plan.proof

    assert plan.put_url
    assert plan.thumb_put_url
    assert proof.original.key == f"crews/{bogdan.crew_id}/proofs/{proof.pk}/original.jpg"
    assert proof.original.expires_at == datetime(2026, 11, 10, 22, tzinfo=UTC)  # its midnight
    card = selectors.card(member=bogdan, challenge_id=challenge.pk)
    assert card is not None
    assert [p.status for p in card.proofs] == ["uploading"]
    assert card.proof_days == []  # nothing the crew can see yet

    send(object_storage, plan)
    done = proofs.complete_proof(by=bogdan, proof_id=proof.pk)

    assert done.status == Proof.Status.READY
    assert done.thumb is not None
    assert (done.original.status, done.thumb.status) == ("complete", "complete")  # fresh rows
    assert proofs.complete_proof(by=bogdan, proof_id=proof.pk).status == Proof.Status.READY
    card = selectors.today(member=bogdan).cards[0]
    assert ([p.pk for p in card.proofs], card.proof_days) == ([proof.pk], [])  # mine, a draft

    check_in(bogdan, challenge)

    card = selectors.today(member=bogdan).cards[0]
    assert (card.state, card.proof_days) == ("done", [DAY])
    first = CheckIn.objects.get().entries.get()
    assert Proof.objects.get().post_id == first.pk


def test_a_video_resumes_on_its_own_challenge_until_midnight(walk):
    ana, bogdan, challenge = walk
    with at("2026-10-10 12:00Z"):
        read = scheduled(ana, bogdan, date(2026, 11, 1), title="Read", proof_required=True)
    plan = video(bogdan, challenge)
    with pytest.raises(proofs.ProofNotFound):  # the same file on another challenge starts fresh
        services.resume_proof(by=bogdan, challenge_id=read.pk, fingerprint=CLIP)
    resumed = services.resume_proof(by=bogdan, challenge_id=challenge.pk, fingerprint=CLIP)
    assert resumed.proof.pk == plan.proof.pk
    with at("2026-11-10 22:30Z"), pytest.raises(proofs.ProofNotFound):  # 00:30: the day is over
        services.resume_proof(by=bogdan, challenge_id=challenge.pk, fingerprint=CLIP)


def test_video_resumes_from_the_parts_it_reported(object_storage, walk):
    ana, bogdan, challenge = walk
    plan = video(bogdan, challenge)
    original = plan.proof.original
    assert (plan.put_url, original.mode, original.part_count) == (None, "multipart", 2)

    first = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=1, data=b"a" * 16 * MiB
    )
    proofs.record_part(by=bogdan, proof_id=plan.proof.pk, number=1, etag=first)

    resumed = services.resume_proof(
        by=bogdan, challenge_id=challenge.pk, fingerprint=CLIP
    )  # the app was closed
    assert (resumed.proof.pk, resumed.parts) == (plan.proof.pk, {1: first})
    with pytest.raises(proofs.ProofNotFound):
        services.resume_proof(by=ana, challenge_id=challenge.pk, fingerprint=CLIP)
    with pytest.raises(proofs.ProofNotFound):
        services.resume_proof(by=bogdan, challenge_id=challenge.pk, fingerprint="")

    assert list(proofs.sign_parts(by=bogdan, proof_id=plan.proof.pk, numbers=[2])) == [2]
    last = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=2, data=b"b" * 10
    )
    proofs.record_part(by=bogdan, proof_id=plan.proof.pk, number=2, etag=last)
    done = proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)
    assert done.status == Proof.Status.PROCESSING  # transcoding next


def test_a_draft_file_needs_no_check_in_only_a_day_that_counts_today(walk):
    ana, bogdan, challenge = walk
    with at("2026-10-10 12:00Z"):
        mondays = scheduled(ana, bogdan, date(2026, 11, 1), title="Swim", on_days=[0])
    plan = photo(bogdan, challenge)

    check_in = CheckIn.objects.get()
    assert (check_in.status, plan.proof.post_id) == (CheckIn.Status.PENDING, None)
    with at("2026-11-11 08:00Z"), pytest.raises(services.DayClosed):
        photo(bogdan, challenge)  # yesterday's
    with pytest.raises(services.DayClosed):
        photo(bogdan, challenge, day=date(2026, 11, 9))
    with pytest.raises(services.NotDueToday):
        photo(bogdan, mondays)  # a Tuesday


def test_any_challenge_takes_a_photo_or_a_video(walk):
    ana, bogdan, challenge = walk
    with at("2026-10-10 12:00Z"):
        no_proof = scheduled(ana, bogdan, date(2026, 11, 1), title="Gym")
    assert photo(bogdan, no_proof).proof.status == Proof.Status.UPLOADING

    for refused, field in [
        (lambda: photo(bogdan, challenge, content_type="image/gif"), "content_type"),
        (lambda: photo(bogdan, challenge, size=50 * MiB + 1), "size"),
        (lambda: photo(bogdan, challenge, thumb_size=2 * MiB + 1), "thumb_size"),
        (lambda: video(bogdan, challenge, size=20 * 1024 * MiB + 1), "size"),
    ]:
        with pytest.raises(ValidationFailed) as error:
            refused()
        assert field in error.value.fields

    webm = video(bogdan, challenge, content_type="video/webm;codecs=vp9,opus").proof.original
    assert (webm.content_type, webm.key.rsplit(".", 1)[1]) == ("video/webm", "webm")


def test_five_draft_files_at_a_time_not_counting_failed_ones(walk):
    _, bogdan, challenge = walk
    plans = [photo(bogdan, challenge) for _ in range(5)]
    with pytest.raises(proofs.TooManyProofs):
        photo(bogdan, challenge)

    Proof.objects.filter(pk=plans[0].proof.pk).update(status=Proof.Status.FAILED)
    assert photo(bogdan, challenge).proof.status == Proof.Status.UPLOADING

    Proof.objects.exclude(status=Proof.Status.FAILED).update(status=Proof.Status.READY)
    check_in(bogdan, challenge)  # posted: the next post takes 5 again
    assert photo(bogdan, challenge).proof.post_id is None


def test_a_missing_thumbnail_is_dropped(object_storage, walk):
    _, bogdan, challenge = walk
    plan = photo(bogdan, challenge)
    thumb = plan.proof.thumb
    send(object_storage, plan, thumb=None)

    done = proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    assert (done.status, done.thumb) == (Proof.Status.READY, None)
    assert Upload.all_objects.get(pk=thumb.pk).is_deleted


def test_a_file_of_another_size_fails_the_proof(object_storage, walk):
    _, bogdan, challenge = walk
    plan = photo(bogdan, challenge)
    send(object_storage, plan, data=b"much bigger than announced")

    with pytest.raises(media.UploadSizeMismatch):
        proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    proof = Proof.objects.get(pk=plan.proof.pk)
    assert proof.status == Proof.Status.FAILED
    assert object_storage.objects == {}
    assert proofs.complete_proof(by=bogdan, proof_id=proof.pk).status == Proof.Status.FAILED


def test_an_upload_must_finish_before_its_days_midnight():
    """25 October 2026 has 25 hours in Chisinau: its midnight is 22:00 UTC, not 21:00."""
    with at("2026-09-10 12:00Z"):
        ana = AdminFactory.create()
        challenge = scheduled(ana, ana, date(2026, 10, 1), proof_required=True)
    with at("2026-10-25 21:59Z"):  # 23:59 local
        late = photo(ana, challenge, day=date(2026, 10, 25), thumb_size=None)
        too_late = photo(ana, challenge, day=date(2026, 10, 25), thumb_size=None)
    assert late.proof.original.expires_at == datetime(2026, 10, 25, 22, tzinfo=UTC)
    storage = media.get_object_storage()
    send(storage, late)
    send(storage, too_late)

    with at("2026-10-25 21:59:30Z"):
        assert proofs.complete_proof(by=ana, proof_id=late.proof.pk).status == "ready"
    with at("2026-10-25 22:00Z"), pytest.raises(media.UploadClosed):
        proofs.complete_proof(by=ana, proof_id=too_late.proof.pk)


def test_only_my_own_draft_files_can_be_removed(object_storage, walk):
    ana, bogdan, challenge = walk
    draft = uploaded(object_storage, bogdan, challenge)

    with pytest.raises(proofs.ProofNotFound):
        proofs.delete_proof(by=ana, proof_id=draft.pk)
    proofs.delete_proof(by=bogdan, proof_id=draft.pk)

    assert Proof.all_objects.get(pk=draft.pk).is_deleted
    assert object_storage.objects == {}
    card = selectors.card(member=bogdan, challenge_id=challenge.pk)
    assert card is not None
    assert card.proofs == []

    posted = uploaded(object_storage, bogdan, challenge)
    check_in(bogdan, challenge)
    with pytest.raises(proofs.ProofPosted):
        proofs.delete_proof(by=bogdan, proof_id=posted.pk)  # it goes only with its post


def test_late_draft_files_go_and_late_posted_uploads_fail_once(object_storage, walk):
    _, bogdan, challenge = walk
    draft = video(bogdan, challenge).proof
    ready = uploaded(object_storage, bogdan, challenge)  # uploaded, never posted
    posted = photo(bogdan, challenge).proof  # as a spin's: posted as it starts
    Proof.objects.filter(pk=posted.pk).update(post_id=uuid.uuid4())

    assert proofs.expire_proofs() == 0  # still within its time
    with at("2026-11-10 22:00Z"):  # midnight
        assert tasks.expire_proofs.delay().get() == 3
        assert proofs.expire_proofs() == 0

    assert Proof.all_objects.get(pk=draft.pk).is_deleted
    assert Proof.all_objects.get(pk=ready.pk).is_deleted
    assert Proof.objects.get(pk=posted.pk).status == Proof.Status.FAILED
    assert (object_storage.uploads, object_storage.objects) == ({}, {})  # aborted and removed


def test_undoing_the_check_in_takes_its_proofs(object_storage, walk):
    _, bogdan, challenge = walk
    uploaded(object_storage, bogdan, challenge)
    check_in(bogdan, challenge)

    assert services.undo_last(by=bogdan, challenge_id=challenge.pk, day=DAY) is None

    assert not CheckIn.objects.exists()
    assert not Proof.all_objects.exists()
    assert object_storage.objects == {}


def test_the_board_marks_days_with_proof(object_storage, walk):
    ana, bogdan, challenge = walk
    uploaded(object_storage, bogdan, challenge)
    check_in(bogdan, challenge)
    with at("2026-11-11 08:00Z"):
        uploaded(object_storage, bogdan, challenge, day=date(2026, 11, 11))  # a draft: no mark

        board = selectors.board(member=ana, challenge_id=challenge.pk, month=DAY)

    assert board is not None
    assert {r.member.display_name: r.proof_days for r in board.rows} == {
        "Ana": [],
        "Bogdan": [DAY],
    }


@pytest.fixture
def sent_video(object_storage, walk):
    """Bogdan sent every part of a 10-byte video; it is not completed yet."""
    _, bogdan, challenge = walk
    plan = video(bogdan, challenge, size=10)
    original = plan.proof.original
    etag = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=1, data=b"x" * 10
    )
    proofs.record_part(by=bogdan, proof_id=plan.proof.pk, number=1, etag=etag)
    return bogdan, plan.proof


def test_a_video_is_ready_once_its_renditions_are_made(transcoder, sent_video):
    bogdan, proof = sent_video
    proofs.complete_proof(by=bogdan, proof_id=proof.pk)

    assert proofs.finish_videos() == 0  # the job starts
    (job_id,) = transcoder.jobs
    assert proofs.finish_videos() == 0  # still running
    transcoder.finish(job_id)

    assert proofs.finish_videos() == 1
    assert proofs.finish_videos() == 0
    proof.refresh_from_db()
    assert proof.status == Proof.Status.READY
    assert Transcode.objects.get().status == Transcode.Status.DONE


def test_a_failed_job_still_shows_the_video(transcoder, sent_video, caplog):
    bogdan, proof = sent_video
    proofs.complete_proof(by=bogdan, proof_id=proof.pk)
    proofs.finish_videos()
    transcoder.finish(next(iter(transcoder.jobs)), error="Unsupported codec")

    with caplog.at_level(logging.WARNING):
        assert proofs.finish_videos() == 1

    assert Proof.objects.get(pk=proof.pk).status == Proof.Status.READY  # the original plays
    assert "Unsupported codec" in caplog.text


def test_an_unreachable_transcoder_is_tried_again_later(transcoder, sent_video, caplog):
    bogdan, proof = sent_video
    proofs.complete_proof(by=bogdan, proof_id=proof.pk)
    proofs.finish_videos()
    transcoder.jobs.clear()  # the service no longer knows the job

    assert proofs.finish_videos() == 0

    assert Proof.objects.get(pk=proof.pk).status == Proof.Status.PROCESSING
    assert "could not be started or checked" in caplog.text


def test_completing_a_video_starts_its_job_at_once(
    transcoder, sent_video, django_capture_on_commit_callbacks
):
    bogdan, proof = sent_video

    with django_capture_on_commit_callbacks(execute=True):
        proofs.complete_proof(by=bogdan, proof_id=proof.pk)

    assert len(transcoder.jobs) == 1
    assert tasks.finish_videos.delay().get() == 0  # the beat run finds it still running


def test_without_transcoding_a_video_is_ready_at_once(sent_video):
    bogdan, proof = sent_video
    get_transcoder.cache_clear()

    with override_settings(TRANSCODER_BACKEND="off"):
        done = proofs.complete_proof(by=bogdan, proof_id=proof.pk)

    assert done.status == Proof.Status.READY


def test_a_videos_length_comes_from_the_phone(walk, browser):
    _, bogdan, challenge = walk
    browser.force_login(bogdan.user)
    url = f"/api/v1/challenges/{challenge.pk}/check-ins/2026-11-10/proofs"
    shape = {"kind": "video", "content_type": "video/mp4", "size": 20 * MiB, "duration": 42}
    started = browser.post(url, shape, content_type="application/json")
    too_long = browser.post(
        url, {**shape, "duration": 3 * 3600 + 1}, content_type="application/json"
    )
    photo_with_one = services.start_proof(
        by=bogdan, challenge_id=challenge.pk, day=DAY, kind="photo",
        content_type="image/jpeg", size=4, duration=5,
    )  # fmt: skip

    assert started.status_code == 201
    assert started.json()["proof"]["duration"] == 42
    assert too_long.json()["error"]["fields"]["duration"]
    assert photo_with_one.proof.duration is None  # photos have no length
