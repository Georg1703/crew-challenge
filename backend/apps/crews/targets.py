"""What members act on: react to (`apps.reactions`), comment on (`apps.comments`) and are told
about (`apps.notifications`). Domain apps register their models here; those apps never import
them.

A target is any crew-owned model with a UUID key. To make one reactable (and commentable):
1. give the model `reactions = GenericRelation("reactions.Reaction",
   content_type_field="target_type", object_id_field="target_id")`, and the same to
   `comments.Comment` when it takes comments (deleting it deletes them);
2. call `register(Target(...))` from its app's `AppConfig.ready()`;
3. show `<Reactions target="<key>" ...>` (and its comments) where the frontend shows it.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from apps.core.errors import NotFound

from .models import Member


class TargetNotFound(NotFound):
    code = "target_not_found"
    message = "This is not here any more."


@dataclass(frozen=True)
class Target:
    key: str  # the public name in the API: "entry"
    model: type[models.Model]
    # The targets this member may see and act on now; one by its id, or a page's worth.
    visible: Callable[[Member], models.QuerySet[Any]]
    comments: bool = False  # it takes comments too, not only reactions
    # The field naming the member who made it ("member", or "pk" when the target is a member):
    # reactions and comments on it are news to them.
    owner: str | None = None
    # The registered target whose page shows it, as (key, id): a comment is shown on its card.
    # None: its own page.
    page: Callable[[Any], tuple[str, UUID]] | None = None


_registry: dict[str, Target] = {}


def register(target: Target) -> None:
    existing = _registry.get(target.key)
    if existing is not None and existing.model is not target.model:
        raise ImproperlyConfigured(f"Target {target.key!r} is already registered.")
    _registry[target.key] = target


def unregister(key: str) -> None:
    """For tests that register a target of their own."""
    _registry.pop(key, None)


def get(key: str) -> Target | None:
    return _registry.get(key)


def all_targets() -> list[Target]:
    return sorted(_registry.values(), key=lambda t: t.key)


def of(obj: Any) -> Target:
    """The target a registered model's row is; ImproperlyConfigured for anything else."""
    for target in _registry.values():
        if isinstance(obj, target.model):
            return target
    raise ImproperlyConfigured(f"{type(obj).__name__} is not a registered target.")


def key_for(content_type: ContentType) -> str:
    """The public key of a registered model, from its content type (a stored generic key)."""
    model = content_type.model_class()
    for target in _registry.values():
        if target.model is model:
            return target.key
    raise ImproperlyConfigured(f"{content_type} is not a registered target.")


def owner_id_of(obj: Any) -> UUID | None:
    """The id of the member who made a target, or None when it has no owner."""
    owner = of(obj).owner
    if owner is None:
        return None
    return getattr(obj, f"{owner}_id", None) or getattr(obj, owner)


def page_of(obj: Any) -> tuple[str, UUID]:
    """Where a target is shown, as (key, id) of a registered target: itself, or its page."""
    target = of(obj)
    return target.page(obj) if target.page is not None else (target.key, obj.pk)


def find(key: str, member: Member, target_id: UUID, *, comments: bool = False) -> Any:
    """The `key` target with this id if the member may see it now (and, with `comments`, if it
    takes comments), else TargetNotFound."""
    target = _registry.get(key)
    found = (
        target.visible(member).filter(pk=target_id).first()
        if target is not None and (target.comments or not comments)
        else None
    )
    if found is None or found.crew_id != member.crew_id:
        raise TargetNotFound()
    return found
