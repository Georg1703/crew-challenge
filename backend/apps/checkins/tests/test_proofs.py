import logging
from datetime import UTC, date, datetime

import pytest
import time_machine
from django.test import override_settings

from apps.challenges import services as challenges
from apps.checkins import selectors, services, tasks
from apps.checkins.models import CheckIn, Proof
from apps.core.errors import ValidationFailed
from apps.media import services as media
from apps.media.models import MiB, Transcode, Upload
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
        shape={"title": "Walk", "frequency": "daily", **shape},
        participant_ids=participant_ids,
    )
    challenges.schedule_challenge(
        by=admin, challenge_id=challenge.pk, period_kind="month", period_start=month
    )
    return challenge


@pytest.fixture
def walk():
    """Ana (admin) and Bogdan take part in Walk (photo or video) all of November 2026."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        challenge = scheduled(ana, bogdan, date(2026, 11, 1), proof_kind="photo_or_video")
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
    services.check_in(by=member, challenge_id=challenge.pk, day=day)


def test_photo_round_trip(object_storage, walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = photo(bogdan, challenge)
    proof = plan.proof

    assert plan.put_url
    assert plan.thumb_put_url
    assert proof.original.key == f"crews/{bogdan.crew_id}/proofs/{proof.pk}/original.jpg"
    assert proof.original.expires_at == datetime(2026, 11, 11, 22, tzinfo=UTC)  # day + 24 h
    card = selectors.card(member=bogdan, challenge_id=challenge.pk)
    assert card is not None
    assert [p.status for p in card.proofs] == ["uploading"]
    assert card.proof_days == []  # nothing the crew can see yet

    send(object_storage, plan)
    done = services.complete_proof(by=bogdan, proof_id=proof.pk)

    assert done.status == Proof.Status.READY
    assert done.thumb is not None
    assert (done.original.status, done.thumb.status) == ("complete", "complete")  # fresh rows
    assert services.complete_proof(by=bogdan, proof_id=proof.pk).status == Proof.Status.READY
    card = selectors.today(member=bogdan).cards[0]
    assert [p.pk for p in card.proofs] == [proof.pk]
    assert card.proof_days == [DAY]


def test_video_resumes_from_the_parts_it_reported(object_storage, walk):
    ana, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = video(bogdan, challenge)
    original = plan.proof.original
    assert (plan.put_url, original.mode, original.part_count) == (None, "multipart", 2)

    first = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=1, data=b"a" * 16 * MiB
    )
    services.record_part(by=bogdan, proof_id=plan.proof.pk, number=1, etag=first)

    resumed = services.resume_proof(by=bogdan, fingerprint=CLIP)  # the app was closed
    assert (resumed.proof.pk, resumed.parts) == (plan.proof.pk, {1: first})
    with pytest.raises(services.ProofNotFound):
        services.resume_proof(by=ana, fingerprint=CLIP)
    with pytest.raises(services.ProofNotFound):
        services.resume_proof(by=bogdan, fingerprint="")

    assert list(services.sign_parts(by=bogdan, proof_id=plan.proof.pk, numbers=[2])) == [2]
    last = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=2, data=b"b" * 10
    )
    services.record_part(by=bogdan, proof_id=plan.proof.pk, number=2, etag=last)
    done = services.complete_proof(by=bogdan, proof_id=plan.proof.pk)
    assert done.status == Proof.Status.PROCESSING  # transcoding next


def test_proof_needs_todays_check_in(walk):
    _, bogdan, challenge = walk
    with pytest.raises(services.NotCheckedIn):
        photo(bogdan, challenge)
    check_in(bogdan, challenge)
    with at("2026-11-11 08:00Z"), pytest.raises(services.DayClosed):
        photo(bogdan, challenge)  # yesterday's check-in
    with pytest.raises(services.DayClosed):
        photo(bogdan, challenge, day=date(2026, 11, 9))


def test_kinds_and_types_follow_the_challenge(walk):
    ana, bogdan, challenge = walk
    with at("2026-10-10 12:00Z"):
        photos_only = scheduled(ana, bogdan, date(2026, 11, 1), title="Read", proof_kind="photo")
        no_proof = scheduled(ana, bogdan, date(2026, 11, 1), title="Gym")
    for c in (challenge, photos_only, no_proof):
        check_in(bogdan, c)

    for refused, field in [
        (lambda: video(bogdan, photos_only), "kind"),
        (lambda: photo(bogdan, no_proof), "kind"),
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


def test_five_proofs_a_day_not_counting_failed_ones(walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plans = [photo(bogdan, challenge) for _ in range(5)]
    with pytest.raises(services.TooManyProofs):
        photo(bogdan, challenge)

    Proof.objects.filter(pk=plans[0].proof.pk).update(status=Proof.Status.FAILED)
    assert photo(bogdan, challenge).proof.status == Proof.Status.UPLOADING


def test_a_missing_thumbnail_is_dropped(object_storage, walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = photo(bogdan, challenge)
    thumb = plan.proof.thumb
    send(object_storage, plan, thumb=None)

    done = services.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    assert (done.status, done.thumb) == (Proof.Status.READY, None)
    assert Upload.all_objects.get(pk=thumb.pk).is_deleted


def test_a_file_of_another_size_fails_the_proof(object_storage, walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = photo(bogdan, challenge)
    send(object_storage, plan, data=b"much bigger than announced")

    with pytest.raises(media.UploadSizeMismatch):
        services.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    proof = Proof.objects.get(pk=plan.proof.pk)
    assert proof.status == Proof.Status.FAILED
    assert object_storage.objects == {}
    assert services.complete_proof(by=bogdan, proof_id=proof.pk).status == Proof.Status.FAILED


def test_started_before_midnight_finishes_within_the_grace():
    """25 October 2026 has 25 hours in Chisinau: the grace still ends 24 h after its midnight."""
    with at("2026-09-10 12:00Z"):
        ana = AdminFactory.create()
        challenge = scheduled(ana, ana, date(2026, 10, 1), proof_kind="photo")
    with at("2026-10-25 21:59Z"):  # 23:59 local
        check_in(ana, challenge, day=date(2026, 10, 25))
        late = photo(ana, challenge, day=date(2026, 10, 25), thumb_size=None)
        too_late = photo(ana, challenge, day=date(2026, 10, 25), thumb_size=None)
    assert late.proof.original.expires_at == datetime(2026, 10, 26, 22, tzinfo=UTC)
    storage = media.get_object_storage()
    send(storage, late)
    send(storage, too_late)

    with at("2026-10-26 21:59Z"):
        assert services.complete_proof(by=ana, proof_id=late.proof.pk).status == "ready"
    with at("2026-10-26 22:00Z"), pytest.raises(media.UploadClosed):
        services.complete_proof(by=ana, proof_id=too_late.proof.pk)


def test_remove_only_my_own_and_only_today(object_storage, walk):
    ana, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = photo(bogdan, challenge)
    send(object_storage, plan)
    services.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    with pytest.raises(services.ProofNotFound):
        services.delete_proof(by=ana, proof_id=plan.proof.pk)
    with at("2026-11-10 22:00Z"), pytest.raises(services.DayClosed):
        services.delete_proof(by=bogdan, proof_id=plan.proof.pk)  # local midnight passed

    services.delete_proof(by=bogdan, proof_id=plan.proof.pk)

    assert Proof.all_objects.get(pk=plan.proof.pk).is_deleted
    assert object_storage.objects == {}
    card = selectors.card(member=bogdan, challenge_id=challenge.pk)
    assert card is not None
    assert card.proofs == []


def test_stuck_uploads_expire_once(object_storage, walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = video(bogdan, challenge)

    assert services.expire_proofs() == 0  # still within its time
    with at("2026-11-11 22:00Z"):
        assert tasks.expire_proofs.delay().get() == 1
        assert services.expire_proofs() == 0

    assert Proof.objects.get(pk=plan.proof.pk).status == Proof.Status.FAILED
    assert object_storage.uploads == {}  # the multipart upload was aborted


def test_undoing_the_check_in_takes_its_proofs(object_storage, walk):
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = photo(bogdan, challenge)
    send(object_storage, plan)
    services.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    assert services.undo_last(by=bogdan, challenge_id=challenge.pk, day=DAY) is None

    assert not CheckIn.objects.exists()
    assert not Proof.all_objects.exists()
    assert object_storage.objects == {}


def test_the_board_marks_days_with_proof(object_storage, walk):
    ana, bogdan, challenge = walk
    check_in(bogdan, challenge)
    send(object_storage, ready := photo(bogdan, challenge))
    services.complete_proof(by=bogdan, proof_id=ready.proof.pk)
    with at("2026-11-11 08:00Z"):
        check_in(bogdan, challenge, day=date(2026, 11, 11))
        photo(bogdan, challenge, day=date(2026, 11, 11))  # still uploading: no mark

        board = selectors.board(member=ana, challenge_id=challenge.pk, month=DAY)

    assert board is not None
    assert {r.member.display_name: r.proof_days for r in board.rows} == {
        "Ana": [],
        "Bogdan": [DAY],
    }


@pytest.fixture
def sent_video(object_storage, walk):
    """Bogdan checked in and sent every part of a 10-byte video; it is not completed yet."""
    _, bogdan, challenge = walk
    check_in(bogdan, challenge)
    plan = video(bogdan, challenge, size=10)
    original = plan.proof.original
    etag = object_storage.upload_part(
        key=original.key, upload_id=original.upload_id, part_number=1, data=b"x" * 10
    )
    services.record_part(by=bogdan, proof_id=plan.proof.pk, number=1, etag=etag)
    return bogdan, plan.proof


def test_a_video_is_ready_once_its_renditions_are_made(transcoder, sent_video):
    bogdan, proof = sent_video
    services.complete_proof(by=bogdan, proof_id=proof.pk)

    assert services.finish_videos() == 0  # the job starts
    (job_id,) = transcoder.jobs
    assert services.finish_videos() == 0  # still running
    transcoder.finish(job_id)

    assert services.finish_videos() == 1
    assert services.finish_videos() == 0
    proof.refresh_from_db()
    assert proof.status == Proof.Status.READY
    assert Transcode.objects.get().status == Transcode.Status.DONE


def test_a_failed_job_still_shows_the_video(transcoder, sent_video, caplog):
    bogdan, proof = sent_video
    services.complete_proof(by=bogdan, proof_id=proof.pk)
    services.finish_videos()
    transcoder.finish(next(iter(transcoder.jobs)), error="Unsupported codec")

    with caplog.at_level(logging.WARNING):
        assert services.finish_videos() == 1

    assert Proof.objects.get(pk=proof.pk).status == Proof.Status.READY  # the original plays
    assert "Unsupported codec" in caplog.text


def test_an_unreachable_transcoder_is_tried_again_later(transcoder, sent_video, caplog):
    bogdan, proof = sent_video
    services.complete_proof(by=bogdan, proof_id=proof.pk)
    services.finish_videos()
    transcoder.jobs.clear()  # the service no longer knows the job

    assert services.finish_videos() == 0

    assert Proof.objects.get(pk=proof.pk).status == Proof.Status.PROCESSING
    assert "could not be started or checked" in caplog.text


def test_completing_a_video_starts_its_job_at_once(
    transcoder, sent_video, django_capture_on_commit_callbacks
):
    bogdan, proof = sent_video

    with django_capture_on_commit_callbacks(execute=True):
        services.complete_proof(by=bogdan, proof_id=proof.pk)

    assert len(transcoder.jobs) == 1
    assert tasks.finish_videos.delay().get() == 0  # the beat run finds it still running


def test_without_transcoding_a_video_is_ready_at_once(sent_video):
    bogdan, proof = sent_video
    get_transcoder.cache_clear()

    with override_settings(TRANSCODER_BACKEND="off"):
        done = services.complete_proof(by=bogdan, proof_id=proof.pk)

    assert done.status == Proof.Status.READY
