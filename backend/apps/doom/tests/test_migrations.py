"""The Wheel of Doom's data migrations, run on today's models."""

from datetime import date
from importlib import import_module
from typing import Any

import pytest
from django.apps import apps as registry
from django.db.models import F

from apps.doom import services
from apps.doom.models import Spin
from apps.doom.tests.test_services import Pick, at, scheduled
from apps.proofs import services as proofs
from apps.proofs.models import Proof

pytestmark = pytest.mark.django_db


def fill(migration: str) -> None:
    fill_post_ids = import_module(f"apps.doom.migrations.{migration}").fill
    Proof.objects.update(post_id=None)  # as the release before recorded them
    fill_post_ids(registry, None)
    fill_post_ids(registry, None)  # twice is once


PHOTO: dict[str, Any] = {"kind": "photo", "content_type": "image/jpeg", "size": 4}


@pytest.fixture
def spin_proofs(crew, object_storage):
    """Ana's spin with a proof the crew can see and one still uploading."""
    ana, bogdan = crew
    scheduled(ana, bogdan, date(2026, 11, 2))
    with at("2026-11-09 08:00Z"):
        services.open_spins()
        spin = Spin.objects.filter(member=ana).first()  # Ana never swam
        assert spin is not None
        services.draw(by=ana, spin_id=spin.pk, rng=Pick(0))  # 20 burpees: needs proof
        uploading = services.start_proof(by=ana, spin_id=spin.pk, **PHOTO).proof
        shown = services.start_proof(by=ana, spin_id=spin.pk, **PHOTO).proof
        object_storage.put_object(key=shown.original.key, data=b"jpeg", content_type="")
        proofs.complete_proof(by=ana, proof_id=shown.pk)
    return spin, shown, uploading


def test_a_spins_shown_proofs_point_at_the_spin(spin_proofs):
    spin, shown, uploading = spin_proofs
    fill("0002_fill_proof_post_id")
    assert dict(Proof.objects.values_list("pk", "post_id")) == {
        shown.pk: spin.pk,
        uploading.pk: None,
    }


def test_then_every_proof_of_a_spin_points_at_it(spin_proofs):
    spin, shown, uploading = spin_proofs
    fill("0003_fill_proof_post_id_again")
    assert dict(Proof.objects.values_list("pk", "post_id")) == {
        shown.pk: spin.pk,
        uploading.pk: spin.pk,
    }


def test_a_spin_its_shown_proof_served_gets_that_time_the_rest_are_drafts(crew, spin_proofs):
    ana, _ = crew
    spin, shown, uploading = spin_proofs
    other = Spin.objects.filter(member=ana).exclude(pk=spin.pk).first()
    assert other is not None
    with at("2026-11-09 08:00Z"):
        services.draw(by=ana, spin_id=other.pk, rng=Pick(0))
        waiting = services.start_proof(by=ana, spin_id=other.pk, **PHOTO).proof
    Proof.objects.update(post_id=F("subject_id"))  # as the release before posted them all
    Spin.objects.update(done_at=None)

    import_module("apps.doom.migrations.0004_served_by_posting").fill(registry, None)

    spin.refresh_from_db()
    other.refresh_from_db()
    assert spin.done_at == Proof.objects.get(pk=shown.pk).updated_at
    assert other.done_at is None
    assert dict(Proof.objects.values_list("pk", "post_id")) == {
        shown.pk: spin.pk,
        uploading.pk: spin.pk,
        waiting.pk: None,  # its spin is still to serve: a draft
    }
