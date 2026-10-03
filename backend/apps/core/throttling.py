"""Rate limits per client IP for sensitive anonymous endpoints (login, joining a crew).

Counts live in the shared cache (Redis), so limits hold across gunicorn workers. Behind Caddy,
the client IP comes from X-Forwarded-For; REST_FRAMEWORK["NUM_PROXIES"] says how many proxies
to trust.
"""

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class IPRateThrottle(SimpleRateThrottle):
    """Subclass and set `scope`; the rate comes from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]."""

    def get_cache_key(self, request: Request, view: APIView) -> str:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginRateThrottle(IPRateThrottle):
    scope = "login"


class JoinRateThrottle(IPRateThrottle):
    scope = "join"
