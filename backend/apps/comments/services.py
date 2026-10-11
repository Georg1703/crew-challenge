from datetime import timedelta
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from apps.crews import targets
from apps.crews.models import Member

from . import selectors
from .models import MAX_LENGTH, MAX_LEVEL, Comment, CommentRead

DELETE_WINDOW = timedelta(minutes=1)


class CommentNotFound(NotFound):
    code = "comment_not_found"
    message = "This comment is not here any more."


class NotYourComment(PermissionDenied):
    code = "not_your_comment"
    message = "Only its writer can delete a comment."


class ReplyTooDeep(Conflict):
    code = "reply_too_deep"
    message = f"Replies go {MAX_LEVEL} levels deep at most."


class CommentHasReplies(Conflict):
    code = "comment_has_replies"
    message = "Someone has replied to this comment: it stays."


class CommentTooOld(Conflict):
    code = "comment_too_old"
    message = "A comment can be deleted only in its first minute."


def add(
    *, member: Member, target: str, target_id: UUID, text: str, parent_id: UUID | None = None
) -> Comment:
    """Comment on a target I can see that takes comments, or answer a comment on it."""
    found = targets.find(target, member, target_id, comments=True)
    text = text.strip()
    if not text or len(text) > MAX_LENGTH:
        raise ValidationFailed(fields={"text": [f"Write 1 to {MAX_LENGTH} characters."]})
    on = {"target_type": ContentType.objects.get_for_model(found), "target_id": found.pk}
    with transaction.atomic():
        parent = None
        if parent_id is not None:
            # Locked: a delete of the parent waits for this reply, or this reply finds it gone.
            parent = Comment.objects.select_for_update().filter(pk=parent_id, **on).first()
            if parent is None:
                raise CommentNotFound()
            if parent.level >= MAX_LEVEL:
                raise ReplyTooDeep()
        return Comment.objects.create(
            crew_id=found.crew_id,
            member=member,
            parent=parent,
            level=parent.level + 1 if parent is not None else 1,
            text=text,
            **on,
        )


def delete(*, member: Member, comment_id: UUID) -> None:
    """Delete my comment (soft) in its first minute, while nobody has replied to it."""
    with transaction.atomic():
        comment = selectors.visible(member).select_for_update().filter(pk=comment_id).first()
        if comment is None:
            raise CommentNotFound()
        if comment.member_id != member.pk:
            raise NotYourComment()
        if clock.now() - comment.created_at > DELETE_WINDOW:
            raise CommentTooOld()
        if Comment.objects.filter(parent=comment).exists():
            raise CommentHasReplies()
        comment.delete()


def mark_read(*, member: Member, target: str, target_id: UUID) -> None:
    """The member has seen the target's comments, up to now."""
    found = targets.find(target, member, target_id, comments=True)
    CommentRead.objects.update_or_create(
        member=member,
        target_type=ContentType.objects.get_for_model(found),
        target_id=found.pk,
        defaults={"read_at": clock.now(), "crew_id": found.crew_id},
    )
