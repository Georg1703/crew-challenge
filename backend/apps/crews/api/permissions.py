from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.crews import selectors
from apps.crews.models import Member

# Session key for the crew the user is acting in (for users who belong to several crews).
ACTIVE_CREW_SESSION_KEY = "active_crew_id"


def current_user(request: Request) -> User:
    """The logged-in user. Call only behind IsAuthenticated or IsCrewMember."""
    if not request.user.is_authenticated:  # pragma: no cover - guarded by permissions
        raise RuntimeError("current_user() called for an anonymous request.")
    return request.user


def active_member(request: Request) -> Member | None:
    """The member the logged-in user acts as, or None."""
    if not request.user.is_authenticated:
        return None
    return selectors.get_active_member(
        user=current_user(request), crew_id=request.session.get(ACTIVE_CREW_SESSION_KEY)
    )


class IsCrewMember(BasePermission):
    """Logged in and a member of a crew. Sets `request.member` for the view.

    Admin-only actions are checked in services (NotCrewAdmin), so the rule lives in one place.
    """

    message = "You are not a member of a crew yet."
    code = "not_crew_member"

    def has_permission(self, request: Request, view: APIView) -> bool:
        member = active_member(request)
        if member is None:
            return False
        request.member = member  # type: ignore[attr-defined]
        return True
