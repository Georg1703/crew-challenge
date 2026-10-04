import factory

from apps.accounts.models import User

DEFAULT_PASSWORD = "correct-horse-battery"


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda u: f"{u.username}@example.com")
    preferred_language = User.Language.ROMANIAN
    password = factory.django.Password(DEFAULT_PASSWORD)
