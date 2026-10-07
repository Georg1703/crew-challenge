import pytest

from apps.crews.models import Member
from apps.reactions import targets


def _find_member(member, target_id):
    return Member.objects.filter(pk=target_id).first()  # any crew: the service must still refuse


@pytest.fixture
def member_target():
    """Members as a stand-in target, so these tests need no domain app."""
    targets.register(targets.Target(key="test_member", model=Member, find=_find_member))
    yield "test_member"
    targets.unregister("test_member")
