from datetime import timedelta

import factory

from apps.core import clock
from apps.crews.models import Crew, Invite, Member

from .accounts import UserFactory


class CrewFactory(factory.django.DjangoModelFactory[Crew]):
    class Meta:
        model = Crew

    name = factory.Sequence(lambda n: f"Crew {n}")
    timezone = "Europe/Chisinau"


class MemberFactory(factory.django.DjangoModelFactory[Member]):
    class Meta:
        model = Member

    crew = factory.SubFactory(CrewFactory)
    user = factory.SubFactory(UserFactory)
    display_name = factory.Sequence(lambda n: f"Member {n}")
    avatar_seed = factory.Sequence(lambda n: f"{n:08x}")
    role = Member.Role.MEMBER
    rotation_position = factory.LazyAttribute(lambda m: Member.objects.filter(crew=m.crew).count())


class AdminFactory(MemberFactory):
    role = Member.Role.ADMIN


class InviteFactory(factory.django.DjangoModelFactory[Invite]):
    class Meta:
        model = Invite

    created_by = factory.SubFactory(AdminFactory)
    crew = factory.SelfAttribute("created_by.crew")
    code = factory.Sequence(lambda n: f"code{n:06d}")
    expires_at = factory.LazyFunction(lambda: clock.now() + timedelta(days=7))
