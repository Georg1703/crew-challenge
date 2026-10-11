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
from apps.proofs import selectors as proofs
from apps.proofs.api.serializers import ProofStartIn, ProofUploadOut, proof_data, upload_data
from apps.proofs.models import Proof
from apps.reactions import selectors as reactions

from .serializers import CommentIn, CommentOut, ThreadOut, UnreadOut

TARGET = OpenApiParameter(
    "target",
    str,
    OpenApiParameter.PATH,
    enum=[t.key for t in targets.all_targets() if t.comments],
    description="What kind of thing the id is.",
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _data(comment: Comment, reacted: reactions.Summary, files: list[Proof]) -> dict[str, Any]:
    return {
        "id": comment.pk,
        "member_id": comment.member_id,
        "parent_id": comment.parent_id,
        "text": comment.text,
        "created_at": comment.created_at,
        "reactions": asdict(reacted),
        "proofs": [proof_data(p) for p in files],
    }


class ThreadView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(parameters=[TARGET], responses=ThreadOut, operation_id="comments_list")
    def get(self, request: Request, target: str, target_id: UUID) -> Response:
        """A target's comments and replies, oldest first, each with its reactions and photos; and
        my photos picked for my next comment."""
        member = _member(request)
        comments = selectors.thread(member=member, target=target, target_id=target_id)
        ids = [c.pk for c in comments]
        reacted = reactions.summaries(member=member, target="comment", ids=ids)
        files = proofs.posted(post_ids=ids)
        drafts = selectors.my_drafts(member=member, target=target, target_id=target_id)
        return Response(
            ThreadOut(
                {
                    "results": [_data(c, reacted[c.pk], files.get(c.pk, [])) for c in comments],
                    "drafts": [proof_data(p) for p in drafts],
                }
            ).data
        )

    @extend_schema(
        parameters=[TARGET],
        request=CommentIn,
        responses={201: CommentOut},
        operation_id="comments_add",
    )
    def post(self, request: Request, target: str, target_id: UUID) -> Response:
        """Comment, or reply to a comment on the same target (`parent_id`), with my uploaded
        draft photos (refused while one uploads); the text may be empty when one goes."""
        data = CommentIn(data=request.data)
        data.is_valid(raise_exception=True)
        comment = services.add(
            member=_member(request),
            target=target,
            target_id=target_id,
            text=data.validated_data["text"],
            parent_id=data.validated_data.get("parent_id"),
        )
        files = proofs.posted(post_ids=[comment.pk]).get(comment.pk, [])
        return Response(
            CommentOut(_data(comment, reactions.Summary(), files)).data,
            status=status.HTTP_201_CREATED,
        )


class CommentView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses={204: None}, operation_id="comments_delete")
    def delete(self, request: Request, comment_id: UUID) -> Response:
        """Delete your comment in its first minute, while nobody has replied to it."""
        services.delete(member=_member(request), comment_id=comment_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReadView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[TARGET], request=None, responses={204: None}, operation_id="comments_read"
    )
    def put(self, request: Request, target: str, target_id: UUID) -> Response:
        """You have seen this target's comments, up to now (its card's dot and the badge clear)."""
        services.mark_read(member=_member(request), target=target, target_id=target_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UnreadView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=UnreadOut, operation_id="comments_unread")
    def get(self, request: Request) -> Response:
        """How many of the others' comments you have not seen, for the Crew tab's badge."""
        return Response(UnreadOut({"count": selectors.unread_count(member=_member(request))}).data)


class ImagesView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[TARGET],
        request=ProofStartIn,
        responses={201: ProofUploadOut},
        operation_id="comments_image",
    )
    def post(self, request: Request, target: str, target_id: UUID) -> Response:
        """A photo or GIF for my next comment here (up to 5): a draft file only I see, until the
        comment is sent. Then send the file straight to storage."""
        data = ProofStartIn(data=request.data)
        data.is_valid(raise_exception=True)
        plan = services.start_image(
            member=_member(request), target=target, target_id=target_id, **data.validated_data
        )
        return Response(ProofUploadOut(upload_data(plan)).data, status=status.HTTP_201_CREATED)
