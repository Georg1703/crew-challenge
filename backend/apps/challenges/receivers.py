"""Reactions to events from other apps. Connected in ChallengesConfig.ready()."""

from typing import Any

from django.dispatch import receiver

from apps.crews.models import Member
from apps.crews.signals import member_joined

from . import services


@receiver(member_joined, dispatch_uid="challenges.add_new_member")
def add_new_member(sender: Any, member: Member, **kwargs: Any) -> None:
    services.add_to_running_challenges(member=member)
