from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.challenges import selectors, services
from apps.challenges.models import Challenge, Participant
from apps.core import clock
from apps.crews.api.permissions import IsCrewMember
from apps.crews.models import Member

from .serializers import ChallengeIn, ChallengeOut, ParticipantsIn, PoolOut, ScheduleIn


def _person(member: Member | None) -> dict[str, Any] | None:
    if member is None:
        return None
    return {"id": member.pk, "display_name": member.display_name, "avatar_seed": member.avatar_seed}


def challenge_data(
    challenge: Challenge,
    member: Member,
    tally: selectors.Tally | None = None,
    people: list[Participant] | None = None,
) -> dict[str, Any]:
    """One challenge for `member`. Pass `tally` and `people` when loaded for a whole list."""
    today = clock.crew_today(challenge.crew)
    if tally is None:
        tally = selectors.tallies(challenges=[challenge]).get(challenge.pk, selectors.Tally())
    if people is None:
        people = selectors.participants(challenges=[challenge]).get(challenge.pk, [])
    return {
        "id": challenge.pk,
        "title": challenge.title,
        "rules": challenge.rules,
        "icon": challenge.icon,
        "measure": challenge.measure,
        "unit": challenge.unit,
        "window": challenge.window,
        "on_days": [day for day in range(7) if challenge.on_days & (1 << day)],
        "need_kind": challenge.need_kind,
        "need_value": challenge.need_value,
        "day_min": challenge.day_min,
        "proof_required": challenge.proof_required,
        "state": challenge.state,
        "phase": selectors.phase(challenge, today),
        "period_kind": challenge.period_kind,
        "period_length": challenge.period_length,
        "period_start": challenge.period_start,
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "chosen_by": _person(challenge.chosen_by),
        "chosen_at": challenge.chosen_at,
        "created_by": _person(challenge.created_by),
        "created_at": challenge.created_at,
        "revision": challenge.revision,
        "vote_count": tally.count,
        "voters": [_person(voter) for voter in tally.voters],
        "my_vote": any(voter.pk == member.pk for voter in tally.voters),
        "mine": challenge.created_by_id == member.pk,
        "participants": [{"member": _person(p.member), "left_on": p.left_on} for p in people],
        "taking_part": any(p.member_id == member.pk and p.left_on is None for p in people),
    }


def challenges_data(challenges: list[Challenge], member: Member) -> list[dict[str, Any]]:
    tallies = selectors.tallies(challenges=challenges)
    people = selectors.participants(challenges=challenges)
    return [
        challenge_data(c, member, tallies.get(c.pk, selectors.Tally()), people.get(c.pk, []))
        for c in challenges
    ]


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


class PoolView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(responses=PoolOut, operation_id="proposals_list")
    def get(self, request: Request) -> Response:
        """The crew's pool of proposals, newest first, with votes and how full it is."""
        member = _member(request)
        pool = selectors.pool(member=member)
        return Response(
            PoolOut(
                {
                    "proposals": challenges_data(pool.proposals, member),
                    "size": pool.size,
                    "limit": pool.limit,
                }
            ).data
        )


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
        """Scheduled challenges, by start date."""
        member = _member(request)
        wanted = tuple(
            p for p in request.query_params.get("phase", "").split(",") if p in selectors.PHASES
        )
        chosen = selectors.list_chosen(member=member, phases=wanted or selectors.PHASES)
        return Response(ChallengeOut(challenges_data(chosen, member), many=True).data)

    @extend_schema(
        request=ChallengeIn, responses={201: ChallengeOut}, operation_id="challenges_create"
    )
    def post(self, request: Request) -> Response:
        """Add a proposal to the crew's pool (409 pool_full when it is full)."""
        member = _member(request)
        data = ChallengeIn(data=request.data)
        data.is_valid(raise_exception=True)
        shape = dict(data.validated_data)
        participant_ids = shape.pop("participant_ids")
        challenge = services.propose_challenge(
            by=member, shape=shape, participant_ids=participant_ids
        )
        return Response(
            ChallengeOut(challenge_data(challenge, member)).data, status=status.HTTP_201_CREATED
        )


class ChallengeView(APIView):
    permission_classes = [IsCrewMember]

    def _get(self, request: Request, challenge_id: UUID) -> Challenge:
        challenge = selectors.get_challenge(member=_member(request), challenge_id=challenge_id)
        if challenge is None:
            raise services.ChallengeNotFound()
        return challenge

    @extend_schema(responses=ChallengeOut, operation_id="challenges_retrieve")
    def get(self, request: Request, challenge_id: UUID) -> Response:
        member = _member(request)
        return Response(ChallengeOut(challenge_data(self._get(request, challenge_id), member)).data)

    @extend_schema(request=ChallengeIn, responses=ChallengeOut, operation_id="challenges_update")
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """The creator replaces their proposal while it is in the pool. Resets its votes."""
        member = _member(request)
        data = ChallengeIn(data=request.data)
        data.is_valid(raise_exception=True)
        shape = dict(data.validated_data)
        participant_ids = shape.pop("participant_ids")
        challenge = services.edit_proposal(
            by=member, challenge_id=challenge_id, shape=shape, participant_ids=participant_ids
        )
        return Response(ChallengeOut(challenge_data(challenge, member)).data)

    @extend_schema(request=None, responses={204: None}, operation_id="challenges_destroy")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """The creator or an admin withdraws a proposal from the pool."""
        services.withdraw_proposal(by=_member(request), challenge_id=challenge_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ParticipantsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        request=ParticipantsIn, responses=ChallengeOut, operation_id="challenges_participants"
    )
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """The creator changes who takes part while the challenge is a proposal."""
        member = _member(request)
        data = ParticipantsIn(data=request.data)
        data.is_valid(raise_exception=True)
        challenge = services.set_participants(
            by=member,
            challenge_id=challenge_id,
            participant_ids=data.validated_data["participant_ids"],
        )
        return Response(ChallengeOut(challenge_data(challenge, member)).data)


class VoteView(APIView):
    permission_classes = [IsCrewMember]

    def _challenge(self, request: Request, challenge_id: UUID) -> Response:
        member = _member(request)
        challenge = selectors.get_challenge(member=member, challenge_id=challenge_id)
        assert challenge is not None
        return Response(ChallengeOut(challenge_data(challenge, member)).data)

    @extend_schema(request=None, responses=ChallengeOut, operation_id="challenges_vote")
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """Vote for a proposal (voting twice counts once)."""
        services.cast_vote(by=_member(request), challenge_id=challenge_id)
        return self._challenge(request, challenge_id)

    @extend_schema(request=None, responses=ChallengeOut, operation_id="challenges_vote_clear")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """Take your vote back."""
        services.clear_vote(by=_member(request), challenge_id=challenge_id)
        return self._challenge(request, challenge_id)


class ScheduleView(APIView):
    permission_classes = [IsCrewMember]

    def _detail(self, request: Request, challenge_id: UUID) -> Response:
        member = _member(request)
        challenge = selectors.get_challenge(member=member, challenge_id=challenge_id)
        assert challenge is not None
        return Response(ChallengeOut(challenge_data(challenge, member)).data)

    @extend_schema(request=ScheduleIn, responses=ChallengeOut, operation_id="challenges_schedule")
    def put(self, request: Request, challenge_id: UUID) -> Response:
        """Admin: schedule a proposal for a period, or move it before it starts."""
        data = ScheduleIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.schedule_challenge(
            by=_member(request), challenge_id=challenge_id, **data.validated_data
        )
        return self._detail(request, challenge_id)

    @extend_schema(request=None, responses=ChallengeOut, operation_id="challenges_unschedule")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """Admin: put a scheduled challenge back in the pool before it starts."""
        services.unschedule_challenge(by=_member(request), challenge_id=challenge_id)
        return self._detail(request, challenge_id)


class ParticipationView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses={204: None}, operation_id="challenges_leave")
    def delete(self, request: Request, challenge_id: UUID) -> Response:
        """Opt out before the start, or leave a running challenge (today still counts).

        Either way the challenge is gone for the member afterwards (an admin still sees it).
        """
        services.stop_taking_part(by=_member(request), challenge_id=challenge_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
