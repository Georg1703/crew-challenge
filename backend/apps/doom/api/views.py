from dataclasses import asdict
from datetime import date
from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.challenges import selectors as challenges
from apps.checkins.selectors import DaySummary
from apps.core import clock
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.doom import selectors, services
from apps.doom.models import Spin
from apps.proofs.api.serializers import ProofStartIn, ProofUploadOut, proof_data, upload_data
from apps.reactions import selectors as reactions

from .serializers import OwedOut, SpinOut, punishment_data, spin_data


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _spin_response(member: Member, spin_id: UUID) -> Response:
    spin = selectors.mine(member=member, spin_id=spin_id)
    if spin is None:
        raise services.SpinNotFound()
    punishments = challenges.punishments(challenges=[spin.challenge]).get(spin.challenge_id, [])
    return Response(SpinOut(spin_data(spin, punishments)).data)


def journal_day(spin: Spin) -> date:
    """The crew-local day of a spin's journal card: drawn or served (its `activity_at`)."""
    return clock.local_date(spin.activity_at, spin.challenge.crew.timezone)  # type: ignore[attr-defined]


def spin_items(
    member: Member, spins: list[Spin], summaries: dict[date, DaySummary], *, served: bool
) -> list[dict[str, Any]]:
    """Journal items for a page of drawn spins, or of served ones with their proofs (see
    SpinItemOut), in a few queries. Reactions are the spin's; the drawn card shows them."""
    counts = challenges.punishments(challenges=list({s.challenge for s in spins}))
    shown = selectors.shown_proofs(spins) if served else {}
    reacted = reactions.summaries(member=member, target="spin", ids=[s.pk for s in spins])
    return [
        {
            "id": spin.pk,
            "member": spin.member,
            "challenge": spin.challenge,
            "day": journal_day(spin),
            "window_first": spin.window_first,
            "window_last": spin.window_last,
            "need_kind": spin.challenge.need_kind,
            "need": spin.need,
            "done": spin.done,
            "punishment": punishment_data(spin.punishment),
            "punishment_count": len(counts.get(spin.challenge_id, [])),
            "state": selectors.state(spin),
            "serve_by": spin.serve_by,
            "late": selectors.late(spin),
            "proofs": [proof_data(p) for p in shown.get(spin.pk, [])],
            "reactions": asdict(reacted[spin.pk]),
            "day_summary": vars(summaries[journal_day(spin)]),
        }
        for spin in spins
    ]


class OwedView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=OwedOut, operation_id="spins_list")
    def get(self, request: Request) -> Response:
        """My spins not served yet, oldest first, with how many to spin and to serve."""
        member = _member(request)
        owed = selectors.owed(member=member)
        punishments = challenges.punishments(challenges=list({s.challenge for s in owed.spins}))
        return Response(
            OwedOut(
                {
                    "to_spin": owed.to_spin,
                    "to_serve": owed.to_serve,
                    "spins": [
                        spin_data(s, punishments.get(s.challenge_id, [])) for s in owed.spins
                    ],
                }
            ).data
        )


class DrawView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses=SpinOut, operation_id="spins_draw")
    def post(self, request: Request, spin_id: UUID) -> Response:
        """Spin: the server draws the punishment (the dial then turns to it). Safe to repeat."""
        services.draw(by=_member(request), spin_id=spin_id)
        return _spin_response(_member(request), spin_id)


class DoneView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses=SpinOut, operation_id="spins_done")
    def post(self, request: Request, spin_id: UUID) -> Response:
        """Serve a drawn punishment that needs no proof."""
        services.mark_done(by=_member(request), spin_id=spin_id)
        return _spin_response(_member(request), spin_id)


class SpinProofsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        request=ProofStartIn, responses={201: ProofUploadOut}, operation_id="spins_proofs_start"
    )
    def post(self, request: Request, spin_id: UUID) -> Response:
        """Add a photo or video to a drawn punishment that needs proof."""
        data = ProofStartIn(data=request.data)
        data.is_valid(raise_exception=True)
        plan = services.start_proof(by=_member(request), spin_id=spin_id, **data.validated_data)
        return Response(ProofUploadOut(upload_data(plan)).data, status=201)


class SpinProofResumeView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[OpenApiParameter("fingerprint", str, required=True)],
        responses=ProofUploadOut,
        operation_id="spins_proofs_resume",
    )
    def get(self, request: Request, spin_id: UUID) -> Response:
        """My unfinished video upload of this file on this spin, or 404."""
        plan = services.resume_proof(
            by=_member(request),
            spin_id=spin_id,
            fingerprint=request.query_params.get("fingerprint", ""),
        )
        return Response(ProofUploadOut(upload_data(plan)).data)
