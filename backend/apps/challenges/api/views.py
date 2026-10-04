from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.challenges import selectors, services
from apps.challenges.models import Challenge, Round
from apps.core import clock
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member

from .serializers import (
    ChallengeDetailOut,
    ChallengeIn,
    ChallengeOut,
    ChallengeRefIn,
    RoundOut,
)


def _person(member: Member | None) -> dict[str, Any] | None:
    if member is None:
        return None
    return {"id": member.pk, "display_name": member.display_name, "avatar_seed": member.avatar_seed}


def challenge_data(challenge: Challenge) -> dict[str, Any]:
    today = clock.crew_today(challenge.crew)
    return {
        "id": challenge.pk,
        "round_id": challenge.round_id,
        "title": challenge.title,
        "rules": challenge.rules,
        "icon": challenge.icon,
        "measure": challenge.measure,
        "unit": challenge.unit,
        "frequency": challenge.frequency,
        "weekdays": [day for day in range(7) if challenge.weekdays & (1 << day)],
        "times": challenge.times,
        "target_scope": challenge.target_scope,
        "target_value": challenge.target_value,
        "proof_kind": challenge.proof_kind,
        "proof_required": challenge.proof_required,
        "state": challenge.state,
        "phase": selectors.phase(challenge, today),
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "created_by": _person(challenge.created_by),
        "created_at": challenge.created_at,
        "revision": challenge.revision,
    }


def round_data(round_: Round, member: Member) -> dict[str, Any]:
    view = selectors.round_view(round_=round_, member=member)
    proposals = []
    for challenge in view.proposals:
        tally = view.tallies.get(challenge.pk, selectors.Tally())
        proposals.append(
            {
                **challenge_data(challenge),
                "vote_count": tally.count,
                "voters": [_person(voter) for voter in tally.voters],
                "mine": challenge.created_by_id == member.pk,
            }
        )
    return RoundOut(
        {
            "id": round_.pk,
            "period_kind": round_.period_kind,
            "period_start": round_.period_start,
            "period_end": round_.period_end,
            "state": round_.state,
            "selection": round_.selection,
            "chosen_id": round_.chosen_id,
            "chosen_by": _person(round_.chosen_by),
            "chosen_at": round_.chosen_at,
            "proposals": proposals,
            "my_vote": view.my_vote,
            "votes_cast": sum(t.count for t in view.tallies.values()),
        }
    ).data


def detail_data(challenge: Challenge, member: Member) -> dict[str, Any]:
    today = clock.crew_today(challenge.crew)
    people = selectors.participants(challenge=challenge)
    mine = next((p for p in people if p.member_id == member.pk), None)
    return ChallengeDetailOut(
        {
            **challenge_data(challenge),
            "participants": [
                {"member": _person(p.member), "joined_on": p.joined_on, "ended_on": p.ended_on}
                for p in people
            ],
            "taking_part": mine is not None and (mine.ended_on is None or mine.ended_on >= today),
        }
    ).data


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


class CurrentRoundView(APIView):
    """The round people propose and vote in now (created on first use)."""

    permission_classes = [IsCrewMember]

    @extend_schema(responses=RoundOut, operation_id="rounds_current")
    def get(self, request: Request) -> Response:
        member = _member(request)
        return Response(round_data(services.open_round(crew=member.crew), member))


class RoundView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=RoundOut, operation_id="rounds_retrieve")
    def get(self, request: Request, round_id: UUID) -> Response:
        member = _member(request)
        round_ = selectors.get_round(crew=member.crew, round_id=round_id)
        if round_ is None:
            raise services.RoundNotFound()
        return Response(round_data(round_, member))


class RoundVoteView(APIView):
    """Vote for a proposal in this round (replaces your vote), or clear your vote."""

    permission_classes = [IsCrewMember]

    @extend_schema(request=ChallengeRefIn, responses=RoundOut, operation_id="rounds_vote")
    def put(self, request: Request, round_id: UUID) -> Response:
        member = _member(request)
        data = ChallengeRefIn(data=request.data)
        data.is_valid(raise_exception=True)
        vote = services.cast_vote(by=member, challenge_id=data.validated_data["challenge_id"])
        if vote.round_id != round_id:
            raise services.ChallengeNotFound()
        return Response(round_data(vote.round, member))

    @extend_schema(request=None, responses=RoundOut, operation_id="rounds_vote_clear")
    def delete(self, request: Request, round_id: UUID) -> Response:
        member = _member(request)
        services.clear_vote(by=member, round_id=round_id)
        round_ = selectors.get_round(crew=member.crew, round_id=round_id)
        assert round_ is not None
        return Response(round_data(round_, member))


class RoundChoiceView(APIView):
    """Admin: choose the round's challenge, or change the choice before it starts."""

    permission_classes = [IsCrewMember]

    @extend_schema(request=ChallengeRefIn, responses=RoundOut, operation_id="rounds_choose")
    def put(self, request: Request, round_id: UUID) -> Response:
        member = _member(request)
        data = ChallengeRefIn(data=request.data)
        data.is_valid(raise_exception=True)
        challenge = selectors.get_challenge(
            crew=member.crew, challenge_id=data.validated_data["challenge_id"]
        )
        if challenge is None or challenge.round_id != round_id:
            raise services.ChallengeNotFound()
        round_ = services.choose_challenge(by=member, challenge_id=challenge.pk)
        return Response(round_data(round_, member))


class ChallengesView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "phase",
                str,
                description="Comma-separated: upcoming, active, finished. Default: all three.",
            )
        ],
        responses=ChallengeOut(many=True),
        operation_id="challenges_list",
    )
    def get(self, request: Request) -> Response:
        """Chosen challenges, by start date."""
        member = _member(request)
        wanted = tuple(
            p for p in request.query_params.get("phase", "").split(",") if p in selectors.PHASES
        )
        chosen = selectors.list_chosen(crew=member.crew, phases=wanted or selectors.PHASES)
        return Response(ChallengeOut([challenge_data(c) for c in chosen], many=True).data)

    @extend_schema(
        request=ChallengeIn, responses={201: ChallengeOut}, operation_id="challenges_create"
    )
    def post(self, request: Request) -> Response:
        """Propose a challenge for the open round."""
        data = ChallengeIn(data=request.data)
        data.is_valid(raise_exception=True)
        challenge = services.propose_challenge(by=_member(request), shape=data.validated_data)
        return Response(
            ChallengeOut(challenge_data(challenge)).data, status=status.HTTP_201_CREATED
        )


class ChallengeView(APIView):
    permission_classes = [IsCrewMember]

    def _get(self, request: Request, challenge_id: UUID) -> Challenge:
        challenge = selectors.get_challenge(crew=_member(request).crew, challenge_id=challenge_id)
        if challenge is None:
            raise services.ChallengeNotFound()
        return challenge

    @extend_schema(responses=ChallengeDetailOut, operation_id="challenges_retrieve")
    def get(self, request: Request, challenge_id: UUID) -> Response:
        return Response(detail_data(self._get(request, challenge_id), _member(request)))

    @extend_schema(request=ChallengeIn, responses=ChallengeOut, operation_id="challenges_update")
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """The creator replaces their proposal while the round is open. Resets its votes."""
        data = ChallengeIn(data=request.data)
        data.is_valid(raise_exception=True)
        challenge = services.edit_proposal(
            by=_member(request), challenge_id=challenge_id, shape=data.validated_data
        )
        return Response(ChallengeOut(challenge_data(challenge)).data)

    @extend_schema(request=None, responses={204: None}, operation_id="challenges_destroy")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """The creator or an admin withdraws a proposal while the round is open."""
        services.withdraw_proposal(by=_member(request), challenge_id=challenge_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReproposeView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses={201: ChallengeOut}, operation_id="challenges_repropose")
    def post(self, request: Request, challenge_id: UUID) -> Response:
        """Propose a challenge that was not chosen again, in the open round."""
        copy = services.repropose(by=_member(request), challenge_id=challenge_id)
        return Response(ChallengeOut(challenge_data(copy)).data, status=status.HTTP_201_CREATED)


class ParticipationView(APIView):
    permission_classes = [IsCrewMember]

    def _detail(self, request: Request, challenge_id: UUID) -> Response:
        member = _member(request)
        challenge = selectors.get_challenge(crew=member.crew, challenge_id=challenge_id)
        assert challenge is not None
        return Response(detail_data(challenge, member))

    @extend_schema(request=None, responses=ChallengeDetailOut, operation_id="challenges_take_part")
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """Take part again (before the start)."""
        services.take_part(by=_member(request), challenge_id=challenge_id)
        return self._detail(request, challenge_id)

    @extend_schema(request=None, responses=ChallengeDetailOut, operation_id="challenges_opt_out")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """Opt out before the start, or leave a running challenge from tomorrow."""
        services.stop_taking_part(by=_member(request), challenge_id=challenge_id)
        return self._detail(request, challenge_id)
