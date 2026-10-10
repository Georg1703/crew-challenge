from dataclasses import asdict
from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comments import selectors, services
from apps.comments.models import Comment
from apps.crews import targets
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.reactions import selectors as reactions

from .serializers import CommentIn, CommentOut, ThreadOut

TARGET = OpenApiParameter(
    "target",
    str,
    OpenApiParameter.PATH,
    enum=[t.key for t in targets.all_targets() if t.comments],
    description="What kind of thing the id is.",
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _data(comment: Comment, reacted: reactions.Summary) -> dict[str, Any]:
    return {
        "id": comment.pk,
        "member_id": comment.member_id,
        "parent_id": comment.parent_id,
        "level": comment.level,
        "text": comment.text,
        "created_at": comment.created_at,
        "reactions": asdict(reacted),
    }


class ThreadView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(parameters=[TARGET], responses=ThreadOut, operation_id="comments_list")
    def get(self, request: Request, target: str, target_id: UUID) -> Response:
        """A target's comments and replies, oldest first, each with its reactions."""
        member = _member(request)
        comments = selectors.thread(member=member, target=target, target_id=target_id)
        reacted = reactions.summaries(member=member, target="comment", ids=[c.pk for c in comments])
        return Response(ThreadOut({"results": [_data(c, reacted[c.pk]) for c in comments]}).data)

    @extend_schema(
        parameters=[TARGET],
        request=CommentIn,
        responses={201: CommentOut},
        operation_id="comments_add",
    )
    def post(self, request: Request, target: str, target_id: UUID) -> Response:
        """Comment, or reply to a comment (`parent_id`; a level 5 comment takes no reply)."""
        data = CommentIn(data=request.data)
        data.is_valid(raise_exception=True)
        comment = services.add(
            member=_member(request),
            target=target,
            target_id=target_id,
            text=data.validated_data["text"],
            parent_id=data.validated_data.get("parent_id"),
        )
        return Response(
            CommentOut(_data(comment, reactions.Summary())).data, status=status.HTTP_201_CREATED
        )


class CommentView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses={204: None}, operation_id="comments_delete")
    def delete(self, request: Request, comment_id: UUID) -> Response:
        """Delete your comment in its first minute, while nobody has replied to it."""
        services.delete(member=_member(request), comment_id=comment_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
