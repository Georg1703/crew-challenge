"""Fixtures shared by the check-in tests."""

from datetime import date

import pytest

from apps.checkins.tests.test_proofs import DAY, at, photo, scheduled, send
from apps.proofs import services as proofs
from tests.factories import AdminFactory, MemberFactory


@pytest.fixture
def crew():
    """Ana (admin), Bogdan, Cristina in November 2026. Walk: all three. Read: Bogdan and Ana."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
        cristina = MemberFactory.create(crew=ana.crew, display_name="Cristina")
        walk = scheduled(ana, bogdan, date(2026, 11, 1), proof_required=True)
        read = scheduled(
            ana, bogdan, date(2026, 11, 1), [ana.pk], title="Read", proof_required=True
        )
    return ana, bogdan, cristina, walk, read


def shown_photo(storage, member, challenge, day=DAY):
    plan = photo(member, challenge, day=day)
    send(storage, plan)
    return proofs.complete_proof(by=member, proof_id=plan.proof.pk)
