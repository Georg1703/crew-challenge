import factory

from apps.challenges.models import Challenge

from .crews import MemberFactory


class ChallengeFactory(factory.django.DjangoModelFactory[Challenge]):
    """A proposal in the pool. Prefer services.propose_challenge in tests of rules."""

    class Meta:
        model = Challenge

    created_by = factory.SubFactory(MemberFactory)
    crew = factory.SelfAttribute("created_by.crew")
    title = factory.Sequence(lambda n: f"Challenge {n}")
