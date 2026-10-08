"""Proof reads that every subject shares."""

from .models import Proof

SHOWN = (Proof.Status.PROCESSING, Proof.Status.READY)  # proof the crew can see
