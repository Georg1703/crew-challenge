import pytest

from apps.accounts import services
from apps.accounts.models import User
from apps.core.errors import ValidationFailed
from tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

STRONG = "garden-flame-2026"


def test_create_user_stores_lowercase_username_and_hashed_password():
    user = services.create_user(username="  Ana.M ", password=STRONG)
    assert user.username == "ana.m"
    assert user.check_password(STRONG)
    assert user.password != STRONG


@pytest.mark.parametrize("taken", ["ana", "ANA", " Ana "])
def test_usernames_are_unique_ignoring_case(taken):
    UserFactory.create(username="ana")
    with pytest.raises(services.UsernameTaken) as err:
        services.create_user(username=taken, password=STRONG)
    assert err.value.code == "username_taken"
    assert "username" in err.value.fields


@pytest.mark.parametrize("bad", ["ab", "x" * 31, "has space", "emoji\u2728"])
def test_username_format(bad):
    with pytest.raises(ValidationFailed) as err:
        services.create_user(username=bad, password=STRONG)
    assert "username" in err.value.fields


@pytest.mark.parametrize("weak", ["short", "12345678", "password", "anapopescu1"])
def test_weak_passwords_are_rejected(weak):
    with pytest.raises(ValidationFailed) as err:
        services.create_user(username="anapopescu", password=weak)
    assert err.value.fields["password"]
    assert not User.objects.filter(username="anapopescu").exists()


def test_verify_credentials_ignores_username_case():
    user = UserFactory.create(username="bogdan")
    assert services.verify_credentials(username="Bogdan", password=DEFAULT_PASSWORD) == user


@pytest.mark.parametrize("password", ["wrong", ""])
def test_verify_credentials_rejects_wrong_password(password):
    UserFactory.create(username="bogdan")
    with pytest.raises(services.InvalidCredentials):
        services.verify_credentials(username="bogdan", password=password)


def test_inactive_users_cannot_log_in():
    UserFactory.create(username="gone", is_active=False)
    with pytest.raises(services.InvalidCredentials):
        services.verify_credentials(username="gone", password=DEFAULT_PASSWORD)


def test_set_preferred_language():
    user = UserFactory.create()
    assert services.set_preferred_language(user=user, language="en").preferred_language == "en"
    with pytest.raises(ValidationFailed):
        services.set_preferred_language(user=user, language="fr")


@pytest.mark.parametrize("name", ["\u0430na1", "an\u00e1", "ana\u2603", "ana b"])
def test_usernames_are_plain_ascii(name):
    with pytest.raises(ValidationFailed):
        services.create_user(username=name, password=STRONG)


def test_usernames_are_nfkc_normalized():
    assert services.create_user(username="\uff21NA1", password=STRONG).username == "ana1"


def test_a_lost_race_on_the_username_becomes_username_taken(monkeypatch):
    services.create_user(username="taken", password=STRONG)
    monkeypatch.setattr(services, "validate_new_username", lambda name: name)
    with pytest.raises(services.UsernameTaken):
        services.create_user(username="taken", password=STRONG)


def test_unknown_language_is_rejected():
    with pytest.raises(ValidationFailed):
        services.create_user(username="lang1", password=STRONG, language="xx")
