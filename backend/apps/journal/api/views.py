import base64
import binascii
from datetime import datetime
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins import selectors as checkins
from apps.checkins.api.views import feed_items
from apps.core.errors import ValidationFailed
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.doom.api.views import journal_day, spin_items
from apps.journal import selectors
from apps.journal.selectors import CHECK_IN, SERVED, SPIN, Cursor

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


class JournalView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("cursor", str, description="`next` of the last page.")],
        responses=JournalPageOut,
        operation_id="journal_list",
    )
    def get(self, request: Request) -> Response:
        """The crew's check-ins, drawn spins and served ones, with their proofs, latest first."""
        member = _member(request)
        entries, cursor = selectors.page(
            member=member, cursor=_decode(request.query_params.get("cursor")), size=PAGE_SIZE
        )
        check_ins = [e.item for e in entries if e.kind == CHECK_IN]
        spins = [e.item for e in entries if e.kind == SPIN]
        served = [e.item for e in entries if e.kind == SERVED]
        on = {c.day for c in check_ins} | {journal_day(s) for s in spins + served}
        summaries = checkins.day_summaries(member=member, on=on)
        data = {
            **{(CHECK_IN, d["id"]): d for d in feed_items(member, check_ins, summaries)},
            **{(SPIN, d["id"]): d for d in spin_items(member, spins, summaries, served=False)},
            **{(SERVED, d["id"]): d for d in spin_items(member, served, summaries, served=True)},
        }
        results = [
            {
                "kind": e.kind,
                "activity_at": e.activity_at,
                "check_in": data[(e.kind, e.item.pk)] if e.kind == CHECK_IN else None,
                "spin": data[(e.kind, e.item.pk)] if e.kind != CHECK_IN else None,
            }
            for e in entries
        ]
        return Response(JournalPageOut({"results": results, "next": _encode(cursor)}).data)
