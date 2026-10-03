from rest_framework import authentication
from rest_framework.request import Request


class SessionAuthentication(authentication.SessionAuthentication):
    """Session auth that answers 401 (not 403) when nobody is logged in.

    DRF returns 403 for unauthenticated requests unless the first authentication class provides
    a WWW-Authenticate header. The SPA relies on 401 to know it must show the login screen.
    """

    def authenticate_header(self, request: Request) -> str:
        return "Session"
