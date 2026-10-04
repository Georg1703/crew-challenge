"""Signals other apps listen to, so crews never imports them (challenges builds on crews)."""

from django.dispatch import Signal

# Sent inside the joining transaction with `member=` the new Member.
member_joined = Signal()
