from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crews import targets
from apps.crews.api.permissions import IsCrewMember, current_user
from apps.crews.models import Member
from apps.notifications import selectors, services
from apps.notifications.models import Notification

from .serializers import (
    NewsOut,
    NewsQueryIn,
    PushKeyOut,
    PushSubscribeIn,
    PushUnsubscribeIn,
)


def _member(request: Request) -> Member:
    return request.member  # type: ignore[attr-defined]


def _out(row: Notification) -> dict:
    return {
        "id": row.pk,
        "kind": row.kind,
        "actor": row.actor,
        "target": {"type": targets.key_for(row.target_type), "id": row.target_id},
        "facts": row.facts,
        "created_at": row.created_at,
        "read_at": row.read_at,
    }


class NewsView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(
        parameters=[NewsQueryIn],
        responses=NewsOut,
        operation_id="notifications_list",
    )
    def get(self, request: Request) -> Response:
        """Your news in this crew, latest first (30 a page), and how many are unread."""
        query = NewsQueryIn(data=request.query_params)
        query.is_valid(raise_exception=True)
        member = _member(request)
        rows = selectors.page(member=member, before=query.validated_data.get("before"))
        return Response(
            NewsOut(
                {
                    "results": [_out(row) for row in rows],
                    "unread": selectors.unread_count(member=member),
                }
            ).data
        )


class ReadView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses={204: None}, operation_id="notifications_read")
    def put(self, request: Request) -> Response:
        """You have seen your news, all of it (the badge clears)."""
        services.mark_read(member=_member(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushKeyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PushKeyOut, operation_id="push_key")
    def get(self, request: Request) -> Response:
        """The key a browser subscribes to push with; empty when push is off on this server."""
        public_key = settings.VAPID_PUBLIC_KEY if settings.PUSH_BACKEND != "off" else ""
        return Response(PushKeyOut({"public_key": public_key}).data)


class PushSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PushSubscribeIn, responses={204: None}, operation_id="push_subscribe")
    def put(self, request: Request) -> Response:
        """This browser gets your news by push (send it again whenever the browser renews it)."""
        data = PushSubscribeIn(data=request.data)
        data.is_valid(raise_exception=True)
        services.subscribe(
            user=current_user(request),
            endpoint=data.validated_data["endpoint"],
            p256dh=data.validated_data["keys"]["p256dh"],
            auth=data.validated_data["keys"]["auth"],
            user_agent=request.headers.get("User-Agent", ""),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[PushUnsubscribeIn], responses={204: None}, operation_id="push_unsubscribe"
    )
    def delete(self, request: Request) -> Response:
        """This browser stops getting push (its endpoint in the query: a DELETE has no body)."""
        data = PushUnsubscribeIn(data=request.query_params)
        data.is_valid(raise_exception=True)
        services.unsubscribe(user=current_user(request), endpoint=data.validated_data["endpoint"])
        return Response(status=status.HTTP_204_NO_CONTENT)
