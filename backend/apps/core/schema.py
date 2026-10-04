"""OpenAPI (drf-spectacular) extensions. Imported by CoreConfig.ready()."""

from drf_spectacular.authentication import SessionScheme


class CrewSessionScheme(SessionScheme):
    """Documents our SessionAuthentication as the standard cookie session scheme."""

    target_class = "apps.core.authentication.SessionAuthentication"
