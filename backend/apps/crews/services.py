"""Crew rules: creating crews, invites, joining, switching crews, member profiles.

Every write goes through here. Functions are keyword-only and raise DomainError subclasses.
"""

from __future__ import annotations

import secrets
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Lower

from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed

from .models import Crew, Invite, Member
from .signals import member_joined

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


class CrewNotFound(NotFound):
    code = "crew_not_found"
    message = "You are not a member of this crew."


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
def accept_invite(
    *, code: str, username: str, password: str, display_name: str, language: str | None = None
) -> Member:
    """A new person joins a crew: creates their login and membership, and uses up the invite."""
    invite = _claim_invite(code)
    user = accounts.create_user(username=username, password=password, language=language)
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
        Invite.objects.select_for_update()
        .select_related("crew")
        .filter(code=normalize_invite_code(code))
        .first()
    )
    if invite is None:
        raise InviteNotFound()
    check_invite(invite)
    return invite


def _use_invite(invite: Invite, member: Member) -> None:
    invite.used_by = member
    invite.used_at = clock.now()
    invite.save(update_fields=["used_by", "used_at", "updated_at"])


def normalize_invite_code(code: str) -> str:
    """Codes are lowercase; people may type them as shown in capitals or with spaces."""
    return code.strip().lower()


# --- switching crews -------------------------------------------------------------------------


def switch_crew(*, user: User, crew_id: UUID) -> Member:
    """The user picks which of their crews to act in; it also opens first after their next login."""
    member = (
        Member.objects.select_related("crew", "user").filter(user=user, crew_id=crew_id).first()
    )
    if member is None:
        raise CrewNotFound()
    member.last_active_at = clock.now()
    member.save(update_fields=["last_active_at", "updated_at"])
    return member


# --- profile ---------------------------------------------------------------------------------


@transaction.atomic
def rename_member(*, member: Member, display_name: str) -> Member:
    Crew.objects.select_for_update().filter(pk=member.crew_id).first()  # same lock as joins
    member.display_name = _clean_display_name(display_name, crew=member.crew, exclude=member)
    with _translate_member_conflicts():
        member.save(update_fields=["display_name", "updated_at"])
    return member


# --- internals -------------------------------------------------------------------------------


def _add_member(
    *, crew: Crew, user: User, display_name: str, role: str = Member.Role.MEMBER
) -> Member:
    Crew.objects.select_for_update().filter(pk=crew.pk).first()  # serialize joins per crew
    name = _clean_display_name(display_name, crew=crew)
    with _translate_member_conflicts():
        member = Member.objects.create(
            crew=crew,
            user=user,
            display_name=name,
            role=role,
            avatar_seed=secrets.token_hex(4),
            last_active_at=clock.now(),
        )
    member_joined.send(sender=Member, member=member)
    return member


@contextmanager
def _translate_member_conflicts() -> Iterator[None]:
    """Turn a lost race on a unique member constraint into the error the checks would give."""
    try:
        with transaction.atomic():
            yield
    except IntegrityError as exc:
        if "member_unique_display_name_per_crew" in str(exc):
            raise DisplayNameTaken(fields={"display_name": [DisplayNameTaken.message]}) from exc
        if "member_unique_user_per_crew" in str(exc):
            raise AlreadyMember() from exc
        raise


# Invisible characters: controls, format characters (zero-width spaces, direction overrides),
# private use, unassigned code points and line or paragraph separators.
_INVISIBLE = {"Cc", "Cf", "Co", "Cs", "Cn", "Zl", "Zp"}
_ALPHABETS = ("LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "GEORGIAN", "HEBREW", "ARABIC")


def normalize_display_name(display_name: str) -> str:
    """NFKC, no invisible characters, single spaces. "Ana\u200b" and "Ana" become the same."""
    text = unicodedata.normalize("NFKC", display_name)
    text = "".join(ch for ch in text if unicodedata.category(ch) not in _INVISIBLE)
    return " ".join(text.split())


def _alphabets(name: str) -> set[str]:
    found = set()
    for ch in name:
        if ch.isalpha():
            char_name = unicodedata.name(ch, "")
            found |= {alphabet for alphabet in _ALPHABETS if char_name.startswith(alphabet)}
    return found


def _clean_display_name(display_name: str, *, crew: Crew, exclude: Member | None = None) -> str:
    name = normalize_display_name(display_name)
    if not 1 <= len(name) <= DISPLAY_NAME_MAX or not any(ch.isalnum() for ch in name):
        raise ValidationFailed(fields={"display_name": [f"Use 1-{DISPLAY_NAME_MAX} characters."]})
    if len(_alphabets(name)) > 1:
        # Mixed alphabets (a Cyrillic A inside a Latin name) are how names get faked.
        raise ValidationFailed(fields={"display_name": ["Use letters from one alphabet."]})
    # Compare the way the database constraint does (LOWER), so the check and the rule agree.
    taken = (
        Member.objects.for_crew(crew)
        .annotate(lower_name=Lower("display_name"))
        .filter(lower_name=Lower(models.Value(name)))
    )
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
