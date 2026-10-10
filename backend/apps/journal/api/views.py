import base64
import binascii
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.errors import ValidationFailed
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.journal import selectors
from apps.journal.models import JournalEntry
from apps.journal.selectors import Cursor
from apps.proofs import selectors as proofs
from apps.proofs.api.serializers import proof_data
from apps.reactions import selectors as reactions

from .serializers import JournalPageOut

PAGE_SIZE = 30


def _encode(cursor: Cursor | None) -> str | None:
    if cursor is None:
        return None
    at, pk = cursor
    return base64.urlsafe_b64encode(f"{at.isoformat()}|{pk}".encode()).decode()


def _decode(raw: str | None) -> Cursor | None:
    if not raw:
        return None
    try:
        at, pk = base64.urlsafe_b64decode(raw.encode()).decode().split("|")
        return datetime.fromisoformat(at), UUID(pk)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationFailed(
            fields={"cursor": ["Use the `next` value of the last page."]}
        ) from exc


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


WITH_PROOFS = (JournalEntry.Kind.CHECK_IN, JournalEntry.Kind.SERVED)  # their subject is the post


class JournalView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("cursor", str, description="`next` of the last page.")],
        responses=JournalPageOut,
        operation_id="journal_list",
    )
    def get(self, request: Request) -> Response:
        """The crew's journal: one card per post, latest first, each as it was posted, with its
        photos and videos, its reactions, and the counts of each day on the page."""
        member = _member(request)
        cards, cursor = selectors.page(
            member=member, cursor=_decode(request.query_params.get("cursor")), size=PAGE_SIZE
        )
        shown = proofs.posted(post_ids=[c.subject_id for c in cards if c.kind in WITH_PROOFS])
        reacted = reactions.summaries(member=member, target="entry", ids=[c.pk for c in cards])
        counts = selectors.day_counts(member=member, days={c.day for c in cards})
        results = [
            {
                "id": card.pk,
                "kind": card.kind,
                "at": card.created_at,
                "day": card.day,
                "member": card.member,
                "challenge": card.challenge,
                "proofs": [
                    proof_data(p)
                    for p in shown.get(card.subject_id, [])
                    if card.kind in WITH_PROOFS
                ],
                "reactions": asdict(reacted[card.pk]),
                **{k.value: card.facts if card.kind == k else None for k in JournalEntry.Kind},
            }
            for card in cards
        ]
        days = [
            {"day": day, "check_ins": check_ins, "proofs": files}
            for day, (check_ins, files) in sorted(counts.items(), reverse=True)
        ]
        return Response(
            JournalPageOut({"results": results, "days": days, "next": _encode(cursor)}).data
        )
