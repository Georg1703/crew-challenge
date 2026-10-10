"""Proof reads that every subject shares."""

from collections import defaultdict
from collections.abc import Iterable
from uuid import UUID

from django.db.models import Q

from .models import Proof

SHOWN = (Proof.Status.PROCESSING, Proof.Status.READY)  # uploaded: its files are there
# What the crew can see: uploaded and posted. A draft file is seen by its owner only.
VISIBLE = Q(status__in=SHOWN, post_id__isnull=False)


def posted(*, post_ids: Iterable[UUID]) -> dict[UUID, list[Proof]]:
    """The proofs the crew can see of each post (a journal page's), oldest first, in one query."""
    result: dict[UUID, list[Proof]] = defaultdict(list)
    rows = (
        Proof.objects.filter(VISIBLE, post_id__in=list(post_ids))
        .select_related("original__transcode", "thumb")
        .order_by("created_at")
    )
    for proof in rows:
        assert proof.post_id is not None
        result[proof.post_id].append(proof)
    return dict(result)
