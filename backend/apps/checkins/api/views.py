from datetime import date
from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins import selectors, services
from apps.checkins.models import Proof
from apps.core import clock
from apps.core.errors import ValidationFailed
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.media import selectors as media
from apps.media.models import Upload

from .serializers import (
    BoardOut,
    CheckInIn,
    PartIn,
    PartsIn,
    PartsOut,
    ProofOut,
    ProofStartIn,
    ProofUploadOut,
    TodayChallengeOut,
    TodayOut,
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _day(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationFailed(fields={"day": ["Use YYYY-MM-DD."]}) from exc


def proof_data(proof: Proof) -> dict[str, Any]:
    hls_url, poster_url = media.renditions(proof.original)
    return {
        "id": proof.pk,
        "kind": proof.kind,
        "status": proof.status,
        "url": media.url(proof.original),
        "hls_url": hls_url,
        "thumb_url": media.url(proof.thumb) or poster_url,
        "created_at": proof.created_at,
    }


def upload_data(plan: services.ProofUpload) -> dict[str, Any]:
    proof, original = plan.proof, plan.proof.original
    multipart = original.mode == Upload.Mode.MULTIPART
    return {
        "proof": proof_data(proof),
        "challenge_id": proof.check_in.challenge_id,
        "day": proof.check_in.day,
        "mode": original.mode,
        "content_type": original.content_type,
        "put_url": plan.put_url,
        "part_size": original.part_size if multipart else None,
        "part_count": original.part_count if multipart else None,
        "parts": [{"number": n, "etag": etag} for n, etag in sorted(plan.parts.items())],
        "thumb_put_url": plan.thumb_put_url,
    }


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
        "proofs": [proof_data(p) for p in card.proofs],
        "proof_days": card.proof_days,
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
        """Undo today's last entry (`day` is today, YYYY-MM-DD). The last one takes its proofs."""
        services.undo_last(by=_member(request), challenge_id=challenge_id, day=_day(day))
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
                        {
                            "member": _person(r.member),
                            "states": r.states,
                            "streak": r.streak,
                            "proof_days": r.proof_days,
                        }
                        for r in board.rows
                    ],
                }
            ).data
        )


class ProofsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        request=ProofStartIn, responses={201: ProofUploadOut}, operation_id="proofs_start"
    )
    def post(self, request: Request, challenge_id: UUID, day: str) -> Response:
        """Add a photo or video to today's check-in. Then send the file straight to storage."""
        data = ProofStartIn(data=request.data)
        data.is_valid(raise_exception=True)
        plan = services.start_proof(
            by=_member(request), challenge_id=challenge_id, day=_day(day), **data.validated_data
        )
        return Response(ProofUploadOut(upload_data(plan)).data, status=201)


class ResumeProofView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("fingerprint", str, required=True)],
        responses=ProofUploadOut,
        operation_id="proofs_resume",
    )
    def get(self, request: Request) -> Response:
        """My unfinished video upload for this file (name|size|lastModified), or 404."""
        plan = services.resume_proof(
            by=_member(request), fingerprint=request.query_params.get("fingerprint", "")
        )
        return Response(ProofUploadOut(upload_data(plan)).data)


class PartsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=PartsIn, responses=PartsOut, operation_id="proofs_sign_parts")
    def post(self, request: Request, proof_id: UUID) -> Response:
        """Fresh URLs to PUT these parts to (also when earlier ones expired)."""
        data = PartsIn(data=request.data)
        data.is_valid(raise_exception=True)
        urls = services.sign_parts(
            by=_member(request), proof_id=proof_id, numbers=data.validated_data["numbers"]
        )
        return Response(
            PartsOut({"parts": [{"number": n, "url": u} for n, u in urls.items()]}).data
        )


class PartView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=PartIn, responses={204: None}, operation_id="proofs_record_part")
    def put(self, request: Request, proof_id: UUID, number: int) -> Response:
        """Report a finished part and its ETag, so a later resume skips it."""
        data = PartIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.record_part(
            by=_member(request), proof_id=proof_id, number=number, etag=data.validated_data["etag"]
        )
        return Response(status=204)


class CompleteProofView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses=ProofOut, operation_id="proofs_complete")
    def post(self, request: Request, proof_id: UUID) -> Response:
        """The file is uploaded: check it and show the proof. Safe to repeat."""
        proof = services.complete_proof(by=_member(request), proof_id=proof_id)
        return Response(ProofOut(proof_data(proof)).data)


class ProofView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses={204: None}, operation_id="proofs_delete")
    def delete(self, request: Request, proof_id: UUID) -> Response:
        """Remove my proof and its files (only on its own day)."""
        services.delete_proof(by=_member(request), proof_id=proof_id)
        return Response(status=204)
