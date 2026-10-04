"""Crew reads. Views and other apps read crew data through these functions."""

from __future__ import annotations

from uuid import UUID

from apps.accounts.models import User
from apps.core import clock

from .models import Crew, Invite, Member


def get_active_member(*, user: User, crew_id: UUID | str | None = None) -> Member | None:
    """The membership the user is acting as.

    With `crew_id` (the crew chosen in this session) that crew's membership; otherwise the user's
    oldest membership. None when the user belongs to no crew.
    """
    memberships = Member.objects.select_related("crew", "user").filter(user=user)
    if crew_id is not None:
        chosen = memberships.filter(crew_id=crew_id).first()
        if chosen is not None:
            return chosen
    return memberships.order_by("created_at").first()


def list_members(*, crew: Crew) -> list[Member]:
    """Members in rotation order."""
    return list(Member.objects.for_crew(crew).select_related("user").order_by("rotation_position"))


def get_invite(*, code: str) -> Invite | None:
    return Invite.objects.select_related("crew", "created_by").filter(code=code.strip()).first()


def list_pending_invites(*, crew: Crew) -> list[Invite]:
    """Invites of the crew that nobody has used and that have not expired, newest first."""
    return list(
        Invite.objects.for_crew(crew)
        .select_related("created_by")
        .filter(used_at__isnull=True, expires_at__gt=clock.now())
        .order_by("-created_at")
    )


def next_in_rotation(*, crew: Crew, after: Member | None) -> Member:
    """The member who proposes after `after`, wrapping around to the first.

    With `after=None` (nobody has proposed yet) it is the first member in the rotation.
    """
    members = list_members(crew=crew)
    if not members:
        raise ValueError(f"Crew {crew.pk} has no members.")
    if after is None:
        return members[0]
    later = [m for m in members if m.rotation_position > after.rotation_position]
    return later[0] if later else members[0]
