"""Proof reads that every subject shares."""

from django.db.models import Q

from .models import Proof

SHOWN = (Proof.Status.PROCESSING, Proof.Status.READY)  # uploaded: its files are there
# What the crew can see: uploaded and posted. A draft file is seen by its owner only.
VISIBLE = Q(status__in=SHOWN, post_id__isnull=False)
