from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth import login
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services as accounts
from apps.accounts.models import User
from apps.core.errors import Conflict, ValidationFailed
from apps.core.throttling import InvitePreviewRateThrottle, JoinRateThrottle
from apps.crews import selectors, services
from apps.crews.models import Invite, Member

from .permissions import ACTIVE_CREW_SESSION_KEY, IsCrewMember, active_member, current_user
from .serializers import (
    AcceptInviteIn,
    CrewDetailOut,
    CrewOut,
    InviteOut,
    InvitePreviewOut,
    JoinWithAccountIn,
    MemberOut,
    MeOut,
    MePatchIn,
    PendingInviteOut,
    RotationIn,
)


class AlreadySignedIn(Conflict):
    code = "already_signed_in"
    message = "You are already signed in. Log out before joining with a new account."


def me_payload(user: User, member: Member | None) -> dict[str, Any]:
    return MeOut({"user": user, "member": member, "crew": member.crew if member else None}).data


def crew_payload(member: Member) -> dict[str, Any]:
    crew = member.crew
    data = dict(CrewOut(crew).data)
    data["members"] = MemberOut(selectors.list_members(crew=crew), many=True).data
    return data


class MeView(APIView):
    """The logged-in user, their membership and crew (member and crew are null outside a crew)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeOut, operation_id="me_retrieve")
    def get(self, request: Request) -> Response:
        return Response(me_payload(current_user(request), active_member(request)))

    @extend_schema(request=MePatchIn, responses=MeOut, operation_id="me_update")
    def patch(self, request: Request) -> Response:
        data = MePatchIn(data=request.data)
        data.is_valid(raise_exception=True)
        member = active_member(request)
        if "preferred_language" in data.validated_data:
            accounts.set_preferred_language(
                user=current_user(request), language=data.validated_data["preferred_language"]
            )
        if "display_name" in data.validated_data:
            if member is None:
                raise ValidationFailed(fields={"display_name": ["You are not in a crew yet."]})
            services.rename_member(member=member, display_name=data.validated_data["display_name"])
        return Response(me_payload(current_user(request), member))


class CrewView(APIView):
    """The crew the user is acting in, with members in rotation order."""

    permission_classes = [IsCrewMember]

    @extend_schema(responses=CrewDetailOut, operation_id="crew_retrieve")
    def get(self, request: Request) -> Response:
        return Response(crew_payload(request.member))  # type: ignore[attr-defined]


class RotationView(APIView):
    """Admin: set the proposer order. Send every member id once, in the new order."""

    permission_classes = [IsCrewMember]

    @extend_schema(request=RotationIn, responses=CrewDetailOut, operation_id="crew_rotation_update")
    def patch(self, request: Request) -> Response:
        data = RotationIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.reorder_rotation(by=request.member, member_ids=data.validated_data["member_ids"])  # type: ignore[attr-defined]
        return Response(crew_payload(request.member))  # type: ignore[attr-defined]


def _invite_url(invite: Invite) -> str:
    return f"{settings.APP_PUBLIC_URL.rstrip('/')}/join/{invite.code}"


def _invite_body(invite: Invite) -> dict[str, Any]:
    return {"code": invite.code, "url": _invite_url(invite), "expires_at": invite.expires_at}


class InvitesView(APIView):
    """Admin: the crew's pending invites, and creating a single-use invite valid for 7 days."""

    permission_classes = [IsCrewMember]

    @extend_schema(responses=PendingInviteOut(many=True), operation_id="crew_invites_list")
    def get(self, request: Request) -> Response:
        member = request.member  # type: ignore[attr-defined]
        services.require_admin(member)
        invites = selectors.list_pending_invites(crew=member.crew)
        body = [
            {**_invite_body(invite), "id": invite.id, "created_by": invite.created_by}
            for invite in invites
        ]
        return Response(PendingInviteOut(body, many=True).data)

    @extend_schema(request=None, responses={201: InviteOut}, operation_id="crew_invites_create")
    def post(self, request: Request) -> Response:
        invite = services.create_invite(by=request.member)  # type: ignore[attr-defined]
        return Response(InviteOut(_invite_body(invite)).data, status=status.HTTP_201_CREATED)


class InviteDetailView(APIView):
    """Admin: cancel an invite nobody has used yet."""

    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses={204: None}, operation_id="crew_invites_destroy")
    def delete(self, request: Request, invite_id: UUID) -> Response:
        services.revoke_invite(by=request.member, invite_id=invite_id)  # type: ignore[attr-defined]
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitePreviewView(APIView):
    """Public: what the join page shows before the person signs up."""

    permission_classes = [AllowAny]
    throttle_classes = [InvitePreviewRateThrottle]

    @extend_schema(responses=InvitePreviewOut, operation_id="invites_retrieve")
    def get(self, request: Request, code: str) -> Response:
        invite = selectors.get_invite(code=code)
        if invite is None:
            raise services.InviteNotFound()
        try:
            services.check_invite(invite)
            invite_status = "valid"
        except services.InviteUsed:
            invite_status = "used"
        except services.InviteExpired:
            invite_status = "expired"
        valid = invite_status == "valid"
        return Response(
            InvitePreviewOut(
                {
                    "crew_name": invite.crew.name,
                    "status": invite_status,
                    "expires_at": invite.expires_at,
                    # Who is in the crew only shows while the link can still be used.
                    "invited_by": invite.created_by if valid else None,
                    "members": selectors.list_members(crew=invite.crew) if valid else [],
                }
            ).data
        )


class AcceptInviteView(APIView):
    """Public: create an account from an invite, join the crew, and log in."""

    permission_classes = [AllowAny]
    throttle_classes = [JoinRateThrottle]

    @extend_schema(request=AcceptInviteIn, responses={201: MeOut}, operation_id="invites_accept")
    def post(self, request: Request, code: str) -> Response:
        if request.user.is_authenticated:
            raise AlreadySignedIn()
        data = AcceptInviteIn(data=request.data)
        data.is_valid(raise_exception=True)
        member = services.accept_invite(code=code, **data.validated_data)
        login(request, member.user, backend="django.contrib.auth.backends.ModelBackend")
        request.session[ACTIVE_CREW_SESSION_KEY] = str(member.crew_id)
        return Response(me_payload(member.user, member), status=status.HTTP_201_CREATED)


class JoinWithAccountView(APIView):
    """Logged in: join the invite's crew with the account you already have."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [JoinRateThrottle]

    @extend_schema(request=JoinWithAccountIn, responses={201: MeOut}, operation_id="invites_join")
    def post(self, request: Request, code: str) -> Response:
        data = JoinWithAccountIn(data=request.data)
        data.is_valid(raise_exception=True)
        user = current_user(request)
        member = services.join_with_account(user=user, code=code, **data.validated_data)
        request.session[ACTIVE_CREW_SESSION_KEY] = str(member.crew_id)
        return Response(me_payload(user, member), status=status.HTTP_201_CREATED)
