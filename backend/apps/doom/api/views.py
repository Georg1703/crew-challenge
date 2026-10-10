from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.challenges import selectors as challenges
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.doom import selectors, services
from apps.proofs.api.serializers import ProofStartIn, ProofUploadOut, upload_data

from .serializers import OwedOut, SpinOut, spin_data


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _spin_response(member: Member, spin_id: UUID) -> Response:
    spin = selectors.mine(member=member, spin_id=spin_id)
    if spin is None:
        raise services.SpinNotFound()
    punishments = challenges.punishments(challenges=[spin.challenge]).get(spin.challenge_id, [])
    return Response(SpinOut(spin_data(spin, punishments)).data)


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
        """Serve my drawn punishment: with its uploaded photos or videos when it needs proof,
        at once when it needs none. Safe to repeat."""
        services.serve(by=_member(request), spin_id=spin_id)
        return _spin_response(_member(request), spin_id)


class SpinProofsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        request=ProofStartIn, responses={201: ProofUploadOut}, operation_id="spins_proofs_start"
    )
    def post(self, request: Request, spin_id: UUID) -> Response:
        """Upload a photo or video as a draft file of a drawn punishment that needs proof;
        serving posts it."""
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
