"""Fixtures shared by the Wheel of Doom tests."""

import pytest

from apps.doom.tests.test_services import at
from tests.factories import AdminFactory, MemberFactory


@pytest.fixture
def crew():
    """Ana (admin) and Bogdan, on October 10, 2026."""
    with at("2026-10-10 12:00Z"):
        ana = AdminFactory.create(display_name="Ana")
        bogdan = MemberFactory.create(crew=ana.crew, display_name="Bogdan")
    return ana, bogdan
