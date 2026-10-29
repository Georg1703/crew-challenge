"""`@Name` in what members write (a comment): who is pointed at. The text stays plain; a
mention is `@` followed by a crew member's display name as it is written, or `@all` for the
whole crew. `docs/plans/mentions.md`."""

import re
from dataclasses import dataclass
from uuid import UUID

from .models import Member

ALL = "all"  # `@all`: everyone in the crew
# An `@` that starts a word: at the start, or after a space or punctuation (not inside an email).
AT = re.compile(r"(?<!\w)@")


@dataclass(frozen=True)
class Mentions:
    members: list[Member]  # each once, in the order they appear
    everyone: bool  # `@all` was there


def find(text: str, *, crew_id: UUID) -> Mentions:
    """The crew members `text` mentions. Names are tried longest first and matched regardless
    of case; a name must end where the text ends or before a character that cannot continue a
    name. An `@` that names nobody is left alone."""
    people = sorted(
        Member.objects.filter(crew_id=crew_id), key=lambda m: len(m.display_name), reverse=True
    )
    folded = text.casefold()
    found: dict[UUID, Member] = {}
    everyone = False
    for hit in AT.finditer(text):
        rest = folded[hit.end() :]
        if _starts(rest, ALL):
            everyone = True
            continue
        for member in people:
            if _starts(rest, member.display_name.casefold()):
                found.setdefault(member.pk, member)
                break
    return Mentions(members=list(found.values()), everyone=everyone)


def _starts(rest: str, name: str) -> bool:
    return rest.startswith(name) and (len(rest) == len(name) or not rest[len(name)].isalnum())
