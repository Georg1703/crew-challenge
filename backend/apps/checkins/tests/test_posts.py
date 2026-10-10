"""Posts: files upload first as drafts, the post publishes them, only posts count."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from apps.checkins import selectors, services
from apps.checkins.models import CheckIn
from apps.checkins.tests.test_proofs import DAY, at, photo, scheduled, send, uploaded
from apps.media import services as media
from apps.proofs import services as proofs
from apps.proofs.models import Proof
from tests.factories import AdminFactory, MemberFactory

pytestmark = pytest.mark.django_db

YESTERDAY = date(2026, 11, 9)


@pytest.fixture
def people():
    """Ana (admin) and Bogdan in November 2026: Walk and Run (km) ask for proof, Gym does not."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        walk = scheduled(ana, bogdan, date(2026, 11, 1), proof_required=True)
        run = scheduled(
            ana, bogdan, date(2026, 11, 1), title="Run", measure="quantity", unit="km",
            proof_required=True,
        )  # fmt: skip
        gym = scheduled(ana, bogdan, date(2026, 11, 1), title="Gym")
    with at("2026-11-10 08:00Z"):
        yield ana, bogdan, walk, run, gym


def post(member, challenge, day=DAY, amount=None):
    return services.check_in(by=member, challenge_id=challenge.pk, day=day, amount=amount)


def test_no_post_without_a_finished_file_where_proof_is_asked(object_storage, people):
    _, bogdan, walk, run, _ = people
    with pytest.raises(services.ProofRequired):
        post(bogdan, walk)
    plan = photo(bogdan, walk)
    with pytest.raises(proofs.UploadsRunning):
        post(bogdan, walk)
    send(object_storage, plan)
    proofs.complete_proof(by=bogdan, proof_id=plan.proof.pk)

    row = post(bogdan, walk)

    entry = row.entries.get()
    assert (row.status, Proof.objects.get(pk=plan.proof.pk).post_id) == ("done", entry.pk)
    with pytest.raises(services.ProofRequired):
        post(bogdan, run, amount=Decimal(5))
    uploaded(object_storage, bogdan, run)
    assert post(bogdan, run, amount=Decimal(5)).amount == Decimal(5)
    with pytest.raises(services.ProofRequired):  # every "+N" brings its own
        post(bogdan, run, amount=Decimal(3))


def test_files_are_optional_elsewhere_and_failed_ones_are_dropped(object_storage, people):
    _, bogdan, _, _, gym = people
    assert post(bogdan, gym).status == CheckIn.Status.DONE  # no file: posted at once
    ready = uploaded(object_storage, bogdan, gym)
    failed = photo(bogdan, gym).proof
    Proof.objects.filter(pk=failed.pk).update(status=Proof.Status.FAILED)

    row = post(bogdan, gym)  # the files, added later

    later = row.entries.get(number=2)
    assert (row.status, later.amount) == (CheckIn.Status.DONE, None)
    assert Proof.objects.get(pk=ready.pk).post_id == later.pk
    assert not Proof.objects.filter(pk=failed.pk).exists()
    assert post(bogdan, gym).entries.count() == 2  # nothing left to post: a tap changes nothing


def test_a_number_challenge_starts_with_a_number(object_storage, people):
    _, bogdan, _, run, _ = people
    uploaded(object_storage, bogdan, run)
    with pytest.raises(services.ValidationFailed):
        post(bogdan, run)  # files alone cannot open the day
    post(bogdan, run, amount=Decimal(4))
    uploaded(object_storage, bogdan, run)
    row = post(bogdan, run)  # files added later: no number
    assert (row.amount, row.entries.count()) == (Decimal(4), 2)


def test_undo_takes_the_latest_post_with_its_files_and_drafts_keep_the_day_pending(
    object_storage, people
):
    _, bogdan, _, _, gym = people
    post(bogdan, gym)
    added = uploaded(object_storage, bogdan, gym)
    post(bogdan, gym)

    row = services.undo_last(by=bogdan, challenge_id=gym.pk, day=DAY)

    assert row is not None
    assert (row.status, row.entries.count()) == (CheckIn.Status.DONE, 1)
    assert not Proof.objects.filter(pk=added.pk).exists()
    uploaded(object_storage, bogdan, gym)  # a draft waits
    row = services.undo_last(by=bogdan, challenge_id=gym.pk, day=DAY)
    assert row is not None
    assert (row.status, row.amount) == (CheckIn.Status.PENDING, None)
    with pytest.raises(services.NothingToUndo):
        services.undo_last(by=bogdan, challenge_id=gym.pk, day=DAY)


def test_only_posts_count_and_the_crew_sees_only_posted_files(object_storage, people):
    ana, bogdan, walk, _, _ = people
    draft = uploaded(object_storage, bogdan, walk)

    def bogdan_on_walk():
        sheet = selectors.day_sheet(member=ana, challenge_id=walk.pk, day=DAY)
        assert sheet is not None
        row = next(r for r in sheet if r.member == bogdan)
        feed = [c.member for c in selectors.feed(member=ana)]
        return row.state, [p.pk for p in row.proofs], feed.count(bogdan)

    assert bogdan_on_walk() == ("todo", [], 0)
    assert selectors.today(member=bogdan).cards[0].state == "todo"

    post(bogdan, walk)

    assert bogdan_on_walk() == ("done", [draft.pk], 1)


def test_midnight_ends_the_day_for_its_draft_files_too(object_storage, people):
    _, bogdan, walk, _, _ = people
    with at("2026-11-09 21:50Z"):  # 23:50 local on the 9th
        ready = uploaded(object_storage, bogdan, walk, day=YESTERDAY)
        late = photo(bogdan, walk, day=YESTERDAY)
    assert late.proof.original.expires_at == datetime(2026, 11, 9, 22, tzinfo=UTC)  # its midnight

    with at("2026-11-09 22:10Z"):  # 00:10 on the 10th
        send(object_storage, late)
        with pytest.raises(media.UploadClosed):
            proofs.complete_proof(by=bogdan, proof_id=late.proof.pk)
        with pytest.raises(services.DayClosed):
            post(bogdan, walk, day=YESTERDAY)
        assert proofs.expire_proofs() == 2  # both drafts go: the day is over

    assert not Proof.objects.filter(pk__in=[ready.pk, late.proof.pk]).exists()
