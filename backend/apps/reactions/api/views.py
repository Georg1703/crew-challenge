from dataclasses import asdict
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.reactions import selectors, services, targets

from .serializers import ReactionIn, ReactionSummaryOut

TARGET = OpenApiParameter(
    "target",
    str,
    OpenApiParameter.PATH,
    enum=[t.key for t in targets.all_targets()],
    description="What kind of thing the id is.",
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _summary(request: Request, target: str, target_id: UUID) -> Response:
    found = selectors.summary(member=_member(request), target=target, target_id=target_id)
    return Response(ReactionSummaryOut(asdict(found)).data)


class ReactionView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[TARGET],
        request=ReactionIn,
        responses=ReactionSummaryOut,
        operation_id="reactions_set",
    )
    def put(self, request: Request, target: str, target_id: UUID) -> Response:
        """React with one emoji; another one replaces yours. Returns the target's reactions."""
        data = ReactionIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.react(
            member=_member(request),
            target=target,
            target_id=target_id,
            emoji=data.validated_data["emoji"],
        )
        return _summary(request, target, target_id)

    @extend_schema(
        parameters=[TARGET], responses=ReactionSummaryOut, operation_id="reactions_clear"
    )
    def delete(self, request: Request, target: str, target_id: UUID) -> Response:
        """Take your reaction back. Returns the target's reactions."""
        services.unreact(member=_member(request), target=target, target_id=target_id)
        return _summary(request, target, target_id)
