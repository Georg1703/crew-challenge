from datetime import timedelta

import pytest
import time_machine
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.core import clock
from apps.core.errors import ValidationFailed
from apps.crews import selectors, services
from apps.crews.models import Invite, Member
from tests.factories import AdminFactory, CrewFactory, InviteFactory, MemberFactory, UserFactory

pytestmark = pytest.mark.django_db

STRONG = "garden-flame-2026"


# --- create crew -----------------------------------------------------------------------------


def test_create_crew_makes_the_creator_its_first_admin():
    user = UserFactory.create()
    member = services.create_crew_with_admin(name=" Familia ", admin_user=user, display_name="Tata")
    assert member.crew.name == "Familia"
    assert member.crew.timezone == "Europe/Chisinau"
    assert member.is_admin
    assert member.rotation_position == 0
    assert member.avatar_seed


@pytest.mark.parametrize(
    ("kwargs", "field"), [({"name": "  "}, "name"), ({"timezone": "Mars/Base"}, "timezone")]
)
def test_create_crew_validates_input(kwargs, field):
    args = {"name": "Crew", "admin_user": UserFactory.create(), "display_name": "Ana", **kwargs}
    with pytest.raises(ValidationFailed) as err:
        services.create_crew_with_admin(**args)
    assert field in err.value.fields


# --- invites ---------------------------------------------------------------------------------


@time_machine.travel("2026-11-03 10:00Z", tick=False)
def test_admin_creates_a_single_use_invite_valid_for_a_week():
    admin = AdminFactory.create()
    invite = services.create_invite(by=admin)
    assert invite.crew == admin.crew
    assert len(invite.code) == services.INVITE_CODE_LENGTH
    assert set(invite.code) <= set(services.INVITE_CODE_ALPHABET)
    assert invite.expires_at == clock.now() + timedelta(days=7)


def test_members_cannot_create_invites():
    with pytest.raises(services.NotCrewAdmin):
        services.create_invite(by=MemberFactory.create())


def test_accept_invite_creates_user_member_and_uses_up_the_invite():
    invite = InviteFactory.create()
    member = services.accept_invite(
        code=f" {invite.code} ", username="Cristina", password=STRONG, display_name="  Cris  "
    )
    invite.refresh_from_db()
    assert member.crew == invite.crew
    assert member.user.username == "cristina"
    assert member.display_name == "Cris"
    assert member.role == Member.Role.MEMBER
    assert member.rotation_position == 1  # after the admin who created the invite
    assert invite.used_by == member
    assert invite.used_at is not None


def test_unknown_invite():
    with pytest.raises(services.InviteNotFound):
        services.accept_invite(code="nope", username="x1x", password=STRONG, display_name="X")


def test_used_invite_cannot_be_used_again():
    invite = InviteFactory.create()
    services.accept_invite(code=invite.code, username="first", password=STRONG, display_name="A")
    with pytest.raises(services.InviteUsed):
        services.accept_invite(
            code=invite.code, username="second", password=STRONG, display_name="B"
        )
    assert not User.objects.filter(username="second").exists()


def test_expired_invite_is_rejected_and_creates_nothing():
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        invite = InviteFactory.create(expires_at=clock.now() + timedelta(days=7))
    with (
        time_machine.travel("2026-11-08 12:00Z", tick=False),
        pytest.raises(services.InviteExpired),
    ):
        services.accept_invite(
            code=invite.code, username="late", password=STRONG, display_name="Late"
        )
    assert not User.objects.filter(username="late").exists()


def test_failed_join_keeps_the_invite_usable():
    invite = InviteFactory.create()
    UserFactory.create(username="taken")
    with pytest.raises(ValidationFailed):
        services.accept_invite(
            code=invite.code, username="Taken", password=STRONG, display_name="T"
        )
    invite.refresh_from_db()
    assert invite.used_at is None


def test_display_names_are_unique_per_crew_ignoring_case():
    invite = InviteFactory.create(created_by__display_name="Mama")
    with pytest.raises(services.DisplayNameTaken):
        services.accept_invite(
            code=invite.code, username="ana", password=STRONG, display_name="mama"
        )
    # The same name is fine in another crew.
    other = InviteFactory.create()
    member = services.accept_invite(
        code=other.code, username="ana", password=STRONG, display_name="Mama"
    )
    assert member.display_name == "Mama"


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_display_name_length(name):
    with pytest.raises(ValidationFailed) as err:
        services.rename_member(member=MemberFactory.create(), display_name=name)
    assert "display_name" in err.value.fields


def test_rename_member_keeps_own_name_case_change():
    member = MemberFactory.create(display_name="ana")
    assert services.rename_member(member=member, display_name="Ana").display_name == "Ana"


def test_database_rejects_used_by_without_used_at():
    invite = InviteFactory.create()
    invite.used_by = MemberFactory.create(crew=invite.crew)
    with pytest.raises(IntegrityError), transaction.atomic():
        invite.save()


# --- rotation --------------------------------------------------------------------------------


def _crew_of(n):
    admin = AdminFactory.create()
    return [admin] + [MemberFactory.create(crew=admin.crew) for _ in range(n - 1)]


def test_reorder_rotation_swaps_positions_in_one_go():
    a, b, c = _crew_of(3)
    services.reorder_rotation(by=a, member_ids=[c.id, a.id, b.id])
    order = [m.id for m in selectors.list_members(crew=a.crew)]
    assert order == [c.id, a.id, b.id]
    assert [m.rotation_position for m in selectors.list_members(crew=a.crew)] == [0, 1, 2]


@pytest.mark.parametrize("ids", ["missing_one", "duplicate", "stranger"])
def test_reorder_rotation_requires_every_member_exactly_once(ids):
    a, b, c = _crew_of(3)
    member_ids = {
        "missing_one": [a.id, b.id],
        "duplicate": [a.id, b.id, b.id],
        "stranger": [a.id, b.id, MemberFactory.create().id],
    }[ids]
    with pytest.raises(ValidationFailed):
        services.reorder_rotation(by=a, member_ids=member_ids)


def test_only_admins_reorder_the_rotation():
    a, b = _crew_of(2)
    with pytest.raises(services.NotCrewAdmin):
        services.reorder_rotation(by=b, member_ids=[b.id, a.id])


def test_next_in_rotation_wraps_around():
    a, b, c = _crew_of(3)
    crew = a.crew
    assert selectors.next_in_rotation(crew=crew, after=None) == a
    assert selectors.next_in_rotation(crew=crew, after=a) == b
    assert selectors.next_in_rotation(crew=crew, after=b) == c
    assert selectors.next_in_rotation(crew=crew, after=c) == a


def test_next_in_rotation_follows_the_new_order():
    a, b, c = _crew_of(3)
    services.reorder_rotation(by=a, member_ids=[c.id, b.id, a.id])
    for m in (a, b, c):
        m.refresh_from_db()
    assert selectors.next_in_rotation(crew=a.crew, after=c) == b
    assert selectors.next_in_rotation(crew=a.crew, after=a) == c


def test_next_in_rotation_needs_members():
    with pytest.raises(ValueError, match="no members"):
        selectors.next_in_rotation(crew=CrewFactory.create(), after=None)


def test_a_new_member_joins_at_the_end_of_the_rotation():
    a, b = _crew_of(2)
    invite = services.create_invite(by=a)
    c = services.accept_invite(
        code=invite.code, username="newbie", password=STRONG, display_name="N"
    )
    assert c.rotation_position == 2
    assert selectors.next_in_rotation(crew=a.crew, after=b) == c


# --- selectors -------------------------------------------------------------------------------


def test_active_member_prefers_the_chosen_crew_and_falls_back_to_the_oldest():
    user = UserFactory.create()
    first = MemberFactory.create(user=user)
    second = MemberFactory.create(user=user)
    assert selectors.get_active_member(user=user) == first
    assert selectors.get_active_member(user=user, crew_id=second.crew_id) == second
    assert selectors.get_active_member(user=user, crew_id=CrewFactory.create().id) == first
    assert selectors.get_active_member(user=UserFactory.create()) is None


def test_get_invite():
    invite = InviteFactory.create()
    assert selectors.get_invite(code=f" {invite.code}") == invite
    assert selectors.get_invite(code="missing") is None
    assert Invite.objects.for_crew(invite.crew).count() == 1


# --- joining with an existing account, pending invites, revoking -------------------------------


def test_join_with_account_adds_a_membership_and_uses_up_the_invite():
    elsewhere = MemberFactory.create()
    invite = InviteFactory.create()
    member = services.join_with_account(user=elsewhere.user, code=invite.code, display_name="Eva")
    invite.refresh_from_db()
    assert member.crew == invite.crew
    assert member.user == elsewhere.user
    assert member.display_name == "Eva"
    assert invite.used_by == member
    assert Member.objects.filter(user=elsewhere.user).count() == 2


def test_join_with_account_rejects_members_of_that_crew():
    invite = InviteFactory.create()
    already = MemberFactory.create(crew=invite.crew)
    with pytest.raises(services.AlreadyMember):
        services.join_with_account(user=already.user, code=invite.code, display_name="Again")
    invite.refresh_from_db()
    assert invite.used_at is None


def test_join_with_account_checks_the_invite():
    user = UserFactory.create()
    with pytest.raises(services.InviteNotFound):
        services.join_with_account(user=user, code="nope", display_name="X")
    invite = InviteFactory.create()
    services.join_with_account(user=user, code=invite.code, display_name="X")
    with pytest.raises(services.InviteUsed):
        services.join_with_account(user=UserFactory.create(), code=invite.code, display_name="Y")


def test_invite_expires_exactly_at_expires_at():
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        invite = InviteFactory.create()
    with time_machine.travel(invite.expires_at - timedelta(microseconds=1), tick=False):
        services.check_invite(invite)
    with (
        time_machine.travel(invite.expires_at, tick=False),
        pytest.raises(services.InviteExpired),
    ):
        services.check_invite(invite)


def test_pending_invites_are_unused_unexpired_and_from_this_crew():
    admin = AdminFactory.create()
    with time_machine.travel("2026-11-01 12:00Z", tick=False):
        old = services.create_invite(by=admin)
    with time_machine.travel("2026-11-06 12:00Z", tick=False):
        fresh = services.create_invite(by=admin)
        used = services.create_invite(by=admin)
        services.accept_invite(code=used.code, username="u1x", password=STRONG, display_name="U")
        InviteFactory.create()  # another crew
        assert old in selectors.list_pending_invites(crew=admin.crew)
    with time_machine.travel("2026-11-09 12:00Z", tick=False):
        assert selectors.list_pending_invites(crew=admin.crew) == [fresh]


def test_admin_revokes_an_unused_invite():
    admin = AdminFactory.create()
    invite = services.create_invite(by=admin)
    services.revoke_invite(by=admin, invite_id=invite.id)
    assert not Invite.objects.filter(pk=invite.pk).exists()
    with pytest.raises(services.InviteNotFound):
        services.accept_invite(
            code=invite.code, username="late1", password=STRONG, display_name="L"
        )


def test_revoking_needs_an_admin_of_the_same_crew_and_an_unused_invite():
    admin = AdminFactory.create()
    invite = services.create_invite(by=admin)
    with pytest.raises(services.NotCrewAdmin):
        services.revoke_invite(by=MemberFactory.create(crew=admin.crew), invite_id=invite.id)
    with pytest.raises(services.InviteNotFound):
        services.revoke_invite(by=AdminFactory.create(), invite_id=invite.id)
    services.accept_invite(code=invite.code, username="used1", password=STRONG, display_name="U")
    with pytest.raises(services.InviteUsed):
        services.revoke_invite(by=admin, invite_id=invite.id)
