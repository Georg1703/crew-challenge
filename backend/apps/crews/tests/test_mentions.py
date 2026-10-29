"""Who a text points at with `@Name`."""

import pytest

from apps.crews import mentions
from tests.factories import MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def crew():
    ana = MemberFactory.create(display_name="Ana")
    ana_maria = MemberFactory.create(crew=ana.crew, display_name="Ana Maria")
    dan = MemberFactory.create(crew=ana.crew, display_name="Dan-Ion 2")
    MemberFactory.create(display_name="Ana")  # another crew's Ana
    return ana, ana_maria, dan


def names(text, crew):
    found = mentions.find(text, crew_id=crew[0].crew_id)
    return [m.display_name for m in found.members], found.everyone


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("@Ana vezi", (["Ana"], False)),
        ("bravo @ana!", (["Ana"], False)),
        ("@Ana Maria vezi", (["Ana Maria"], False)),  # the longest name wins
        ("@Ana, @Ana Maria", (["Ana", "Ana Maria"], False)),
        ("@Ana @Ana @ANA", (["Ana"], False)),  # once
        ("@Anastasia", ([], False)),  # a name must end there
        ("@dan-ion 2 si @Dan", (["Dan-Ion 2"], False)),
        ("ana@example.com @ nimeni @Zoe", ([], False)),
        ("@all la treaba", ([], True)),
        ("@All, @Ana!", (["Ana"], True)),
        ("@allison", ([], False)),
        ("", ([], False)),
    ],
)
def test_who_is_mentioned(crew, text, expected):
    assert names(text, crew) == expected
