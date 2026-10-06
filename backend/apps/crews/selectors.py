"""Crew reads. Views and other apps read crew data through these functions."""

from __future__ import annotations

from uuid import UUID

from django.db.models import F

from apps.accounts.models import User
from apps.core import clock

from .models import Crew, Invite, Member


def get_active_member(*, user: User, crew_id: UUID | str | None = None) -> Member | None:
    """The membership the user is acting as.

    With `crew_id` (the crew chosen in this session) that crew's membership; otherwise the crew
    the user chose most recently (on any device), then their oldest. None outside every crew.
    """
    memberships = Member.objects.select_related("crew", "user").filter(user=user)
    if crew_id is not None:
        chosen = memberships.filter(crew_id=crew_id).first()
        if chosen is not None:
            return chosen
    return memberships.order_by(F("last_active_at").desc(nulls_last=True), "created_at").first()


def list_memberships(*, user: User) -> list[Member]:
    """Every crew the user belongs to, by crew name."""
    return list(
        Member.objects.select_related("crew").filter(user=user).order_by("crew__name", "crew_id")
    )


def list_members(*, crew: Crew) -> list[Member]:
    """Members in the order they joined."""
    return list(Member.objects.for_crew(crew).select_related("user").order_by("created_at", "id"))


def get_member(*, crew: Crew, member_id: UUID) -> Member | None:
    """One member of this crew, or None (also for another crew's member)."""
    return Member.objects.for_crew(crew).filter(pk=member_id).first()


def get_invite(*, code: str) -> Invite | None:
    return (
        Invite.objects.select_related("crew", "created_by")
        .filter(code=code.strip().lower())
        .first()
    )


def list_pending_invites(*, crew: Crew) -> list[Invite]:
    """Invites of the crew that nobody has used and that have not expired, newest first."""
    return list(
        Invite.objects.for_crew(crew)
        .select_related("created_by")
        .filter(used_at__isnull=True, expires_at__gt=clock.now())
        .order_by("-created_at")
    )
