"""Sending a proof's files, whatever it backs. Starting one belongs to its subject's app."""

from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member
from apps.proofs import services

from .serializers import PartIn, PartsIn, PartsOut, ProofOut, proof_data


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


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
        """Remove my proof and its files (only on the day it was added)."""
        services.delete_proof(by=_member(request), proof_id=proof_id)
        return Response(status=204)
