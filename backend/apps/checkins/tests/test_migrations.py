"""Check-ins' data migrations, run on today's models."""

from datetime import date
from decimal import Decimal
from importlib import import_module

import pytest
from django.apps import apps as registry

from apps.checkins import services
from apps.checkins.models import CheckInEntry
from apps.checkins.tests.conftest import shown_photo
from apps.checkins.tests.test_proofs import DAY, at, photo, scheduled
from apps.proofs.models import Proof

pytestmark = pytest.mark.django_db

fill_post_ids = import_module("apps.checkins.migrations.0006_fill_proof_post_id").fill


def test_a_check_ins_proofs_point_at_its_first_entry(crew, object_storage):
    ana, bogdan, _, walk, _ = crew
    with at("2026-10-10 12:00Z"):
        run = scheduled(
            ana,
            bogdan,
            date(2026, 11, 1),
            title="Run",
            measure="quantity",
            unit="km",
            proof_required=True,
        )
    with at("2026-11-10 08:00Z"):
        for amount in (5, 3):
            services.check_in(by=bogdan, challenge_id=run.pk, day=DAY, amount=Decimal(amount))
        shown = shown_photo(object_storage, bogdan, run)
        uploading = photo(bogdan, run).proof
        services.check_in(by=ana, challenge_id=walk.pk, day=DAY)
        walked = shown_photo(object_storage, ana, walk)

    fill_post_ids(registry, None)
    fill_post_ids(registry, None)  # twice is once

    first = CheckInEntry.objects.get(check_in__member=bogdan, number=1)
    ana_entry = CheckInEntry.objects.get(check_in__member=ana)
    assert dict(Proof.objects.values_list("pk", "post_id")) == {
        shown.pk: first.pk,
        uploading.pk: first.pk,
        walked.pk: ana_entry.pk,
    }
