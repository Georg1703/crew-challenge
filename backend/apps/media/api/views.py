from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crews.api.permissions import IsCrewMember
from apps.media import selectors

from .serializers import MediaSessionOut


class MediaSessionView(APIView):
    permission_classes = [IsCrewMember]

    @extend_schema(request=None, responses=MediaSessionOut, operation_id="media_session")
    def post(self, request: Request) -> Response:
        """Set the cookies that let this browser load the crew's photos and videos.

        Call it when the app starts, after switching crews, and before `expires_at`.
        """
        session = selectors.media_session(crew=request.member.crew)  # type: ignore[attr-defined]
        expires_at = session.expires_at if session else None
        response = Response(MediaSessionOut({"expires_at": expires_at}).data)
        if session is not None:
            for name, value in session.cookies.items():
                response.set_cookie(
                    name,
                    value,
                    expires=session.expires_at,
                    domain=session.domain,
                    secure=True,
                    httponly=True,
                    samesite="Lax",
                )
        return response
