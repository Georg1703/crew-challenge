import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from py_vapid import Vapid02

from integrations.push import WebPushSender, get_push_sender, make_vapid_keys


def test_the_keys_fit_py_vapid_and_the_env_file(capsys):
    public, private = make_vapid_keys()
    vapid = Vapid02.from_string(private)
    assert vapid.public_key is not None
    assert len(public) == 87  # an uncompressed P-256 point, base64url without padding
    call_command("vapid_keys")
    lines = capsys.readouterr().out.splitlines()
    assert [line.split("=")[0] for line in lines] == ["VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY"]


def test_the_factory_follows_settings(settings):
    for backend, keys in (("webpush", True), ("webpush", False), ("off", False), ("nope", False)):
        settings.PUSH_BACKEND = backend
        settings.VAPID_PUBLIC_KEY = settings.VAPID_PRIVATE_KEY = "k" if keys else ""
        get_push_sender.cache_clear()
        if backend == "webpush" and keys:
            assert isinstance(get_push_sender(), WebPushSender)
        elif backend == "off":
            assert get_push_sender() is None
        else:
            with pytest.raises(ImproperlyConfigured):
                get_push_sender()
    get_push_sender.cache_clear()
