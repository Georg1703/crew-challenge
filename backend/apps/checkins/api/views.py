from dataclasses import asdict
from datetime import date
from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins import days, selectors, services
from apps.checkins.models import Proof
from apps.core import clock
from apps.core.errors import ValidationFailed
from apps.core.pagination import CursorPagination
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.media import selectors as media
from apps.media.models import Upload
from apps.reactions import selectors as reactions

from .serializers import (
    BoardOut,
    CheckInIn,
    DaySheetRowOut,
    FeedItemOut,
    MemberProgressOut,
    PartIn,
    PartsIn,
    PartsOut,
    ProofOut,
    ProofStartIn,
    ProofUploadOut,
    TodayChallengeOut,
    TodayOut,
    WindowOut,
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _day(raw: str, name: str = "day") -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationFailed(fields={name: ["Use YYYY-MM-DD."]}) from exc


def _optional_day(request: Request, name: str) -> date | None:
    raw = request.query_params.get(name)
    return _day(raw, name) if raw else None


def window_data(judged: days.Judged) -> dict[str, Any]:
    w, verdict = judged.window, judged.verdict
    return {
        "first": w.first,
        "last": w.last,
        "need": w.need,
        "full_need": w.full_need,
        "done": verdict.done if verdict else None,
        "state": verdict.state if verdict else None,
    }


def proof_data(proof: Proof) -> dict[str, Any]:
    hls_url, poster_url = media.renditions(proof.original)
    return {
        "id": proof.pk,
        "kind": proof.kind,
        "status": proof.status,
        "url": media.url(proof.original),
        "hls_url": hls_url,
        # A video's poster beats the phone's frame, which some phones (iOS) draw black.
        "thumb_url": poster_url or media.url(proof.thumb),
        "created_at": proof.created_at,
        "duration": proof.duration,
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


def card_data(card: selectors.Card) -> dict[str, Any]:
    c = card.challenge
    return {
        "id": c.pk,
        "title": c.title,
        "icon": c.icon,
        "measure": c.measure,
        "unit": c.unit,
        "window": c.window,
        "need_kind": c.need_kind,
        "need_value": c.need_value,
        "day_min": c.day_min,
        "proof_required": c.proof_required,
        "end_date": c.end_date,
        "state": card.state,
        "total": card.total,
        "streak": card.streak,
        "week": [{"day": d, "state": s} for d, s in card.week],
        "current": window_data(card.current) if card.current else None,
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
                        {
                            "member": r.member,
                            "done": r.done,
                            "needed": r.needed,
                            "challenges": [
                                {"challenge_id": c, "state": state} for c, state in r.challenges
                            ],
                        }
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


def _month(request: Request, member: Member) -> date:
    raw = request.query_params.get("month")
    try:
        return date.fromisoformat(f"{raw}-01") if raw else clock.crew_today(member.crew)
    except ValueError as exc:
        raise ValidationFailed(fields={"month": ["Use YYYY-MM."]}) from exc


class WindowsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "start", str, description="YYYY-MM-DD: as if scheduled from that day (no verdicts)."
            ),
            OpenApiParameter("until", str, description="YYYY-MM-DD: as if you left that day."),
        ],
        responses=WindowOut(many=True),
        operation_id="challenges_windows",
    )
    def get(self, request: Request, challenge_id: UUID) -> Response:
        """The challenge's weeks, months or whole period: what each asks for and how yours stand."""
        found = selectors.challenge_windows(
            member=_member(request),
            challenge_id=challenge_id,
            start=_optional_day(request, "start"),
            until=_optional_day(request, "until"),
        )
        if found is None:
            raise services.ChallengeNotFound()
        return Response(WindowOut([window_data(j) for j in found], many=True).data)


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
        board = selectors.board(
            member=member, challenge_id=challenge_id, month=_month(request, member)
        )
        if board is None:
            raise services.ChallengeNotFound()
        return Response(
            BoardOut(
                {
                    "days": board.days,
                    "rows": [
                        {
                            "member": r.member,
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


class DaySheetView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=DaySheetRowOut(many=True), operation_id="challenges_day_sheet")
    def get(self, request: Request, challenge_id: UUID, day: str) -> Response:
        """Everyone's state, total and proofs on one day (`day` is YYYY-MM-DD), in join order."""
        member = _member(request)
        rows = selectors.day_sheet(member=member, challenge_id=challenge_id, day=_day(day))
        if rows is None:
            raise services.ChallengeNotFound()
        data = [
            {
                "member": r.member,
                "state": r.state,
                "total": r.total,
                "proofs": [proof_data(p) for p in r.proofs],
            }
            for r in rows
        ]
        return Response(DaySheetRowOut(data, many=True).data)


def feed_detail_data(d: selectors.FeedDetail) -> dict[str, Any]:
    return {
        "streak": d.streak,
        "day_index": d.day_index,
        "day_count": d.day_count,
        "week": [{"day": day, "state": state} for day, state in d.week],
        "last_amount": d.last_amount,
        "target": d.target,
        "milestone": {"kind": "streak", "n": d.milestone} if d.milestone else None,
    }


class FeedPagination(CursorPagination):
    page_size = 30
    ordering = "-activity_at"


class FeedView(APIView):
    permission_classes = [IsCrewMember]
    pagination_class = FeedPagination  # also gives the schema its {results, next} and cursor

    @extend_schema(responses=FeedItemOut(many=True), operation_id="feed_list")
    def get(self, request: Request) -> Response:
        """The crew's check-ins with their proofs, latest activity first."""
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(selectors.feed(member=_member(request)), request, self)
        assert page is not None  # always paginated
        member = _member(request)
        details = selectors.feed_details(page)
        summaries = selectors.day_summaries(member=member, on={c.day for c in page})
        reacted = reactions.summaries(member=member, target="check_in", ids=[c.pk for c in page])
        items = [
            {
                "id": c.pk,
                "member": c.member,
                "challenge": c.challenge,
                "day": c.day,
                "status": c.status,
                "total": c.amount,
                "activity_at": c.activity_at,  # type: ignore[attr-defined]
                "proofs": [proof_data(p) for p in c.shown_proofs],  # type: ignore[attr-defined]
                **feed_detail_data(details[c.pk]),
                "day_summary": vars(summaries[c.day]),
                "reactions": asdict(reacted[c.pk]),
            }
            for c in page
        ]
        return paginator.get_paginated_response(FeedItemOut(items, many=True).data)


class MemberProgressView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("month", str, description="YYYY-MM; default this month.")],
        responses=MemberProgressOut,
        operation_id="members_progress",
    )
    def get(self, request: Request, member_id: UUID) -> Response:
        """A member's month: streaks, each challenge's days and their proofs by day."""
        viewer = _member(request)
        found = selectors.member_progress(
            viewer=viewer, member_id=member_id, month=_month(request, viewer)
        )
        if found is None:
            raise services.MemberNotFound()
        return Response(
            MemberProgressOut(
                {
                    "member": found.member,
                    "days": found.days,
                    "streak": found.streak,
                    "longest_streak": found.longest_streak,
                    "month_done": found.month_done,
                    "month_due": found.month_due,
                    "challenges": [
                        {
                            "challenge": c.challenge,
                            "states": c.states,
                            "proof_days": c.proof_days,
                            "streak": c.streak,
                            "today": c.today,
                        }
                        for c in found.challenges
                    ],
                    "proof_days": [
                        {
                            "day": p.day,
                            "challenge": p.challenge,
                            "proofs": [proof_data(proof) for proof in p.proofs],
                        }
                        for p in found.proof_days
                    ],
                }
            ).data
        )
