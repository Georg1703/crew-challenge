"""What members can react to. Domain apps register their models here; reactions never import them.

A target is any crew-scoped model with a UUID key. To make one reactable:
1. give the model `reactions = GenericRelation("reactions.Reaction",
   content_type_field="target_type", object_id_field="target_id")` (deleting it deletes them);
2. call `register(Target(...))` from its app's `AppConfig.ready()`;
3. show `<Reactions target="<key>" ...>` where the frontend shows it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ImproperlyConfigured

from apps.crews.models import CrewScopedModel, Member


@dataclass(frozen=True)
class Target:
    key: str  # the public name in the API: "check_in"
    model: type[CrewScopedModel]
    # The object if this member may see it and react to it now, else None.
    find: Callable[[Member, UUID], CrewScopedModel | None]


_registry: dict[str, Target] = {}


def register(target: Target) -> None:
    existing = _registry.get(target.key)
    if existing is not None and existing.model is not target.model:
        raise ImproperlyConfigured(f"Reaction target {target.key!r} is already registered.")
    _registry[target.key] = target


def unregister(key: str) -> None:
    """For tests that register a target of their own."""
    _registry.pop(key, None)


def get(key: str) -> Target | None:
    return _registry.get(key)


def all_targets() -> list[Target]:
    return sorted(_registry.values(), key=lambda t: t.key)
