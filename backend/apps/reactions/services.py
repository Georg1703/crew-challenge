import unicodedata
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core.errors import NotFound, ValidationFailed
from apps.crews.models import CrewScopedModel, Member

from . import targets
from .models import Reaction

MAX_EMOJI_LENGTH = 32  # code points: a family with skin tones joined by ZWJ fits easily
KEYCAP = chr(0x20E3)  # combining enclosing keycap (chr: the repo keeps sources ASCII)
# Symbols, modifiers (skin tones), combining marks (VS16, keycap), format (ZWJ, tags), digits
# and "#*" before a keycap. Letters, spaces, punctuation and markup are refused.
ALLOWED_CATEGORIES = {"So", "Sk", "Mn", "Me", "Cf", "Nd"}


class TargetNotFound(NotFound):
    code = "target_not_found"
    message = "There is nothing to react to here."


class InvalidEmoji(ValidationFailed):
    code = "invalid_emoji"
    message = "A reaction is one emoji."


def check_emoji(value: str) -> str:
    """One emoji (with its skin tone, ZWJ parts or keycap), else InvalidEmoji."""
    ok = (
        0 < len(value) <= MAX_EMOJI_LENGTH
        and all(unicodedata.category(c) in ALLOWED_CATEGORIES or c in "#*" for c in value)
        and any(unicodedata.category(c) == "So" or c == KEYCAP for c in value)
    )
    if not ok:
        raise InvalidEmoji(fields={"emoji": ["Pick one emoji."]})
    return value


def _find(member: Member, target: str, target_id: UUID) -> CrewScopedModel:
    found = targets.get(target)
    obj = found.find(member, target_id) if found is not None else None
    if obj is None or obj.crew_id != member.crew_id:
        raise TargetNotFound()
    return obj


def react(*, member: Member, target: str, target_id: UUID, emoji: str) -> None:
    """Set the member's reaction on a target, replacing another one; the same twice is a no-op."""
    obj = _find(member, target, target_id)
    emoji = check_emoji(emoji)
    key = {
        "target_type": ContentType.objects.get_for_model(obj),
        "target_id": obj.pk,
        "member": member,
    }
    with transaction.atomic():
        # A new emoji is a new row, so its group counts as first used now.
        Reaction.objects.filter(**key).exclude(emoji=emoji).delete()
        Reaction.objects.get_or_create(**key, defaults={"emoji": emoji, "crew_id": obj.crew_id})


def unreact(*, member: Member, target: str, target_id: UUID) -> None:
    """Remove the member's reaction from a target; without one, nothing happens."""
    obj = _find(member, target, target_id)
    Reaction.objects.filter(
        target_type=ContentType.objects.get_for_model(obj), target_id=obj.pk, member=member
    ).delete()
