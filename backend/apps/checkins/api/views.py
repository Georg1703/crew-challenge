from datetime import date
from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins import selectors, services
from apps.core import clock
from apps.core.errors import ValidationFailed
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member

from .serializers import BoardOut, CheckInIn, TodayChallengeOut, TodayOut


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _person(member: Member) -> dict[str, Any]:
    return {"id": member.pk, "display_name": member.display_name, "avatar_seed": member.avatar_seed}


def card_data(card: selectors.Card) -> dict[str, Any]:
    c = card.challenge
    return {
        "id": c.pk,
        "title": c.title,
        "icon": c.icon,
        "measure": c.measure,
        "unit": c.unit,
        "frequency": c.frequency,
        "times": c.times,
        "target_scope": c.target_scope,
        "target_value": c.target_value,
        "proof_kind": c.proof_kind,
        "proof_required": c.proof_required,
        "end_date": c.end_date,
        "state": card.state,
        "total": card.total,
        "streak": card.streak,
        "week": [{"day": d, "state": s} for d, s in card.week],
        "progress": card.progress.__dict__ if card.progress else None,
        "settled": card.settled,
    }


class TodayView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=TodayOut, operation_id="today_retrieve")
    def get(self, request: Request) -> Response:
        """My challenges today with their state, and the crew's progress."""
        today = selectors.today(member=_member(request))
        return Response(
            TodayOut(
                {
                    "day": today.day,
                    "deadline": today.deadline,
                    "challenges": [card_data(c) for c in today.cards],
                    "crew": [
                        {"member": _person(r.member), "done": r.done, "needed": r.needed}
                        for r in today.crew
                    ],
                }
            ).data
        )


def _card_response(request: Request, challenge_id: UUID) -> Response:
    card = selectors.card(member=_member(request), challenge_id=challenge_id)
    assert card is not None
    return Response(TodayChallengeOut(card_data(card)).data)


class CheckInsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        request=CheckInIn, responses=TodayChallengeOut, operation_id="challenges_check_in"
    )
    def post(self, request: Request, challenge_id: UUID) -> Response:
        """Check in for today (numbers add up). Returns the challenge as on today's card."""
        data = CheckInIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.check_in(by=_member(request), challenge_id=challenge_id, **data.validated_data)
        return _card_response(request, challenge_id)


class UndoView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses=TodayChallengeOut, operation_id="challenges_undo")
    def delete(self, request: Request, challenge_id: UUID, day: str) -> Response:
        """Undo today's last entry (`day` is today, YYYY-MM-DD)."""
        try:
            parsed = date.fromisoformat(day)
        except ValueError as exc:
            raise ValidationFailed(fields={"day": ["Use YYYY-MM-DD."]}) from exc
        services.undo_last(by=_member(request), challenge_id=challenge_id, day=parsed)
        return _card_response(request, challenge_id)


class BoardView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("month", str, description="YYYY-MM; default this month.")],
        responses=BoardOut,
        operation_id="challenges_board",
    )
    def get(self, request: Request, challenge_id: UUID) -> Response:
        """Every participant's month, one state per day."""
        member = _member(request)
        raw = request.query_params.get("month")
        try:
            month = date.fromisoformat(f"{raw}-01") if raw else clock.crew_today(member.crew)
        except ValueError as exc:
            raise ValidationFailed(fields={"month": ["Use YYYY-MM."]}) from exc
        board = selectors.board(member=member, challenge_id=challenge_id, month=month)
        if board is None:
            raise services.ChallengeNotFound()
        return Response(
            BoardOut(
                {
                    "days": board.days,
                    "rows": [
                        {"member": _person(r.member), "states": r.states, "streak": r.streak}
                        for r in board.rows
                    ],
                }
            ).data
        )
