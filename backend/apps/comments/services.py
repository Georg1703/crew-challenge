from datetime import timedelta
from typing import Any
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core import clock
from apps.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from apps.crews import targets
from apps.crews.models import Member
from apps.notifications import services as notifications
from apps.proofs import services as proofs
from apps.proofs.models import Proof

from . import selectors
from .models import MAX_LENGTH, Comment, CommentRead

DELETE_WINDOW = timedelta(minutes=1)
DRAFT_LIFE = timedelta(days=1)  # a photo picked for a comment and never sent goes after this


class CommentNotFound(NotFound):
    code = "comment_not_found"
    message = "This comment is not here any more."


class NotYourComment(PermissionDenied):
    code = "not_your_comment"
    message = "Only its writer can delete a comment."


class CommentHasReplies(Conflict):
    code = "comment_has_replies"
    message = "Someone has replied to this comment: it stays."


class CommentTooOld(Conflict):
    code = "comment_too_old"
    message = "A comment can be deleted only in its first minute."


def _locked(member: Member, target: str, target_id: UUID) -> Any:
    """The target, its row locked: one start or send at a time counts my draft photos right."""
    found = targets.find(target, member, target_id, comments=True)
    return type(found).objects.select_for_update().get(pk=found.pk)


def start_image(
    *, member: Member, target: str, target_id: UUID, kind: str, **upload: Any
) -> proofs.ProofUpload:
    """A photo or GIF picked for my next comment on a target: a draft file (mine only) until the
    comment is sent, up to 5. Then send the file straight to storage."""
    if kind != Proof.Kind.PHOTO:
        raise ValidationFailed(fields={"kind": ["A comment takes photos and GIFs."]})
    with transaction.atomic():
        return proofs.start_proof(
            member=member,
            subject=_locked(member, target, target_id),
            kind=kind,
            expires_at=clock.now() + DRAFT_LIFE,
            **upload,
        )


def add(
    *, member: Member, target: str, target_id: UUID, text: str, parent_id: UUID | None = None
) -> Comment:
    """Comment on a target I can see that takes comments, or answer a comment on it, with my
    uploaded draft photos (refused while one still uploads). The text may be empty when there is
    a photo."""
    text = text.strip()
    if len(text) > MAX_LENGTH:
        raise ValidationFailed(fields={"text": [f"Write at most {MAX_LENGTH} characters."]})
    with transaction.atomic():
        found = _locked(member, target, target_id)
        files = proofs.uploaded_drafts(subject=found, member=member)
        if not text and not files:
            raise ValidationFailed(fields={"text": ["Write something or add a photo."]})
        on = {"target_type": ContentType.objects.get_for_model(found), "target_id": found.pk}
        parent = None
        if parent_id is not None:
            # Locked: a delete of the parent waits for this reply, or this reply finds it gone.
            parent = Comment.objects.select_for_update().filter(pk=parent_id, **on).first()
            if parent is None:
                raise CommentNotFound()
        comment = Comment.objects.create(
            crew_id=found.crew_id,
            member=member,
            parent=parent,
            text=text,
            **on,
        )
        proofs.publish(subject=found, post_id=comment.pk, member=member)
        _tell(comment, found, parent)
        return comment


def _tell(comment: Comment, found: Any, parent: Comment | None) -> None:
    """News: whoever the text mentions hears of a mention; the target's owner and everyone else
    who commented on it hear of a comment; the writer of the comment answered hears of a reply
    instead (one line each: the first that applies)."""
    facts = {"text": comment.text}
    notifications.mention(actor=comment.member, source=comment, target=found, text=comment.text)
    answered = parent.member_id if parent is not None else None
    notifications.notify(
        kind=notifications.Notification.Kind.REPLY,
        actor=comment.member,
        source=comment,
        target=found,
        recipients=[answered],
        facts=facts,
    )
    writers = Comment.objects.filter(
        target_type=comment.target_type, target_id=comment.target_id
    ).values_list("member_id", flat=True)
    notifications.notify(
        kind=notifications.Notification.Kind.COMMENT,
        actor=comment.member,
        source=comment,
        target=found,
        recipients=[m for m in {targets.owner_id_of(found), *writers} if m != answered],
        facts=facts,
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
        notifications.retract(source=comment)


def mark_read(*, member: Member, target: str, target_id: UUID) -> None:
    """The member has seen the target's comments, up to now."""
    found = targets.find(target, member, target_id, comments=True)
    CommentRead.objects.update_or_create(
        member=member,
        target_type=ContentType.objects.get_for_model(found),
        target_id=found.pk,
        defaults={"read_at": clock.now(), "crew_id": found.crew_id},
    )
    notifications.mark_read(member=member, target=found)
