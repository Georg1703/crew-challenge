from datetime import date

import factory

from apps.challenges.models import Challenge, PeriodKind, Round

from .crews import MemberFactory


class RoundFactory(factory.django.DjangoModelFactory[Round]):
    class Meta:
        model = Round

    crew = factory.SubFactory("tests.factories.crews.CrewFactory")
    period_kind = PeriodKind.MONTH
    period_start = date(2026, 11, 1)
    period_end = date(2026, 11, 30)


class ChallengeFactory(factory.django.DjangoModelFactory[Challenge]):
    """A proposal. Prefer services.propose_challenge in tests of rules."""

    class Meta:
        model = Challenge

    created_by = factory.SubFactory(MemberFactory)
    crew = factory.SelfAttribute("created_by.crew")
    round = factory.SubFactory(RoundFactory, crew=factory.SelfAttribute("..created_by.crew"))
    title = factory.Sequence(lambda n: f"Challenge {n}")
