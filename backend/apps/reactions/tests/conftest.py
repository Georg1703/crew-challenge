import pytest

from apps.crews import targets
from apps.crews.models import Member


def _every_member(member):
    return Member.objects.all()  # any crew: the service must still refuse


@pytest.fixture
def member_target():
    """Members as a stand-in target, so these tests need no domain app."""
    targets.register(targets.Target(key="test_member", model=Member, visible=_every_member))
    yield "test_member"
    targets.unregister("test_member")
