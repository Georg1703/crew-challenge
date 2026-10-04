"""Crew rules: creating crews, invites, joining, the proposer rotation, member profiles.

Every write goes through here. Functions are keyword-only and raise DomainError subclasses.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Max

from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed

from .models import Crew, Invite, Member

INVITE_TTL = timedelta(days=7)
INVITE_CODE_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"  # no 0/o, 1/l/i: easy to read aloud
INVITE_CODE_LENGTH = 10
DISPLAY_NAME_MAX = 40


class NotCrewAdmin(PermissionDenied):
    code = "not_crew_admin"
    message = "Only a crew admin can do this."


class InviteNotFound(NotFound):
    code = "invite_not_found"
    message = "This invite link does not exist."


class InviteExpired(Conflict):
    code = "invite_expired"
    message = "This invite link has expired. Ask for a new one."


class InviteUsed(Conflict):
    code = "invite_used"
    message = "This invite link has already been used. Ask for a new one."


class AlreadyMember(Conflict):
    code = "already_member"
    message = "You are already in this crew."


class DisplayNameTaken(ValidationFailed):
    code = "display_name_taken"
    message = "Someone in this crew already uses this name."


# --- crews -----------------------------------------------------------------------------------


@transaction.atomic
def create_crew_with_admin(
    *, name: str, admin_user: User, display_name: str, timezone: str | None = None
) -> Member:
    """Create a crew and make `admin_user` its first member and admin."""
    name = name.strip()
    if not name:
        raise ValidationFailed(fields={"name": ["Give the crew a name."]})
    tz = timezone or settings.DEFAULT_CREW_TIMEZONE
    try:
        clock.zone(tz)
    except clock.UnknownTimezone as exc:
        raise ValidationFailed(fields={"timezone": [str(exc)]}) from exc
    crew = Crew.objects.create(name=name, timezone=tz)
    return _add_member(
        crew=crew, user=admin_user, display_name=display_name, role=Member.Role.ADMIN
    )


# --- invites ---------------------------------------------------------------------------------


def create_invite(*, by: Member, ttl: timedelta = INVITE_TTL) -> Invite:
    """An admin creates a single-use invite link for their crew."""
    require_admin(by)
    for _ in range(5):
        try:
            with transaction.atomic():
                return Invite.objects.create(
                    crew=by.crew,
                    created_by=by,
                    code=_new_invite_code(),
                    expires_at=clock.now() + ttl,
                )
        except IntegrityError:  # pragma: no cover - a 10-character code collision is ~impossible
            continue
    raise RuntimeError("Could not generate a unique invite code.")  # pragma: no cover


def check_invite(invite: Invite) -> None:
    """Raise if the invite can no longer be used."""
    if invite.used_at is not None:
        raise InviteUsed()
    if invite.expires_at <= clock.now():
        raise InviteExpired()


@transaction.atomic
def accept_invite(*, code: str, username: str, password: str, display_name: str) -> Member:
    """A new person joins a crew: creates their login and membership, and uses up the invite."""
    invite = _claim_invite(code)
    user = accounts.create_user(username=username, password=password)
    member = _add_member(crew=invite.crew, user=user, display_name=display_name)
    _use_invite(invite, member)
    return member


@transaction.atomic
def join_with_account(*, user: User, code: str, display_name: str) -> Member:
    """Someone who already has an account (in another crew) joins this crew with it."""
    invite = _claim_invite(code)
    if Member.objects.for_crew(invite.crew).filter(user=user).exists():
        raise AlreadyMember()
    member = _add_member(crew=invite.crew, user=user, display_name=display_name)
    _use_invite(invite, member)
    return member


@transaction.atomic
def revoke_invite(*, by: Member, invite_id: UUID) -> None:
    """An admin cancels an invite nobody has used yet. Its link stops working at once."""
    require_admin(by)
    invite = Invite.objects.select_for_update().for_crew(by.crew).filter(pk=invite_id).first()
    if invite is None:
        raise InviteNotFound()
    if invite.used_at is not None:
        raise InviteUsed()
    invite.delete()


def _claim_invite(code: str) -> Invite:
    """Lock a usable invite for this transaction, so two people cannot use the same link."""
    invite = (
        Invite.objects.select_for_update().select_related("crew").filter(code=code.strip()).first()
    )
    if invite is None:
        raise InviteNotFound()
    check_invite(invite)
    return invite


def _use_invite(invite: Invite, member: Member) -> None:
    invite.used_by = member
    invite.used_at = clock.now()
    invite.save(update_fields=["used_by", "used_at", "updated_at"])


# --- rotation --------------------------------------------------------------------------------


@transaction.atomic
def reorder_rotation(*, by: Member, member_ids: Sequence[UUID]) -> list[Member]:
    """An admin sets the proposer order. `member_ids` must list every member exactly once."""
    require_admin(by)
    members = {m.id: m for m in Member.objects.select_for_update().for_crew(by.crew)}
    if len(member_ids) != len(set(member_ids)) or set(member_ids) != set(members):
        raise ValidationFailed(
            fields={"member_ids": ["List every member of the crew exactly once."]}
        )
    ordered = [members[member_id] for member_id in member_ids]
    for position, member in enumerate(ordered):
        member.rotation_position = position
    # The unique (crew, rotation_position) constraint is deferred until commit, so swaps work.
    Member.objects.bulk_update(ordered, ["rotation_position", "updated_at"])
    return ordered


# --- profile ---------------------------------------------------------------------------------


def rename_member(*, member: Member, display_name: str) -> Member:
    member.display_name = _clean_display_name(display_name, crew=member.crew, exclude=member)
    member.save(update_fields=["display_name", "updated_at"])
    return member


# --- internals -------------------------------------------------------------------------------


def _add_member(
    *, crew: Crew, user: User, display_name: str, role: str = Member.Role.MEMBER
) -> Member:
    Crew.objects.select_for_update().filter(pk=crew.pk).first()  # serialize joins per crew
    name = _clean_display_name(display_name, crew=crew)
    last = Member.objects.for_crew(crew).aggregate(last=Max("rotation_position"))["last"]
    return Member.objects.create(
        crew=crew,
        user=user,
        display_name=name,
        role=role,
        avatar_seed=secrets.token_hex(4),
        rotation_position=0 if last is None else last + 1,
    )


def _clean_display_name(display_name: str, *, crew: Crew, exclude: Member | None = None) -> str:
    name = " ".join(display_name.split())
    if not 1 <= len(name) <= DISPLAY_NAME_MAX:
        raise ValidationFailed(fields={"display_name": [f"Use 1-{DISPLAY_NAME_MAX} characters."]})
    taken = Member.objects.for_crew(crew).filter(display_name__iexact=name)
    if exclude is not None:
        taken = taken.exclude(pk=exclude.pk)
    if taken.exists():
        raise DisplayNameTaken(fields={"display_name": [DisplayNameTaken.message]})
    return name


def require_admin(member: Member) -> None:
    """Raise unless the member is an admin. Views call it for admin-only reads."""
    if not member.is_admin:
        raise NotCrewAdmin()


def _new_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
