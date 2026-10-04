from datetime import datetime

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core import health
from apps.core.tasks import ping


def _ok():
    return None


def _fail():
    raise ConnectionError("down")


def test_run_checks_reports_each_check():
    ok, results = health.run_checks({"database": _ok, "redis": _fail})
    assert ok is False
    assert results == {"database": "ok", "redis": "error"}


@pytest.mark.django_db
def test_database_check_runs_a_real_query():
    health.check_database()


def test_redis_check_pings_and_closes(monkeypatch):
    calls = []

    class FakeRedis:
        def ping(self):
            calls.append("ping")

        def close(self):
            calls.append("close")

    monkeypatch.setattr(health.redis.Redis, "from_url", lambda *a, **kw: FakeRedis())
    health.check_redis()
    assert calls == ["ping", "close"]


def test_health_endpoint_ok(api_client, monkeypatch):
    monkeypatch.setattr(health, "CHECKS", {"database": _ok, "redis": _ok})
    response = api_client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_health_endpoint_reports_failure(api_client, monkeypatch):
    monkeypatch.setattr(health, "CHECKS", {"database": _ok, "redis": _fail})
    response = api_client.get(reverse("health"))
    assert response.status_code == 503
    assert response.json()["checks"]["redis"] == "error"


def test_ping_task():
    assert ping.delay().get(timeout=1) == "pong"


@pytest.mark.django_db
def test_saving_a_naive_datetime_fails_the_test_suite():
    """Guardrail: Django only warns about naive datetimes; our pytest config makes it an error."""
    with pytest.raises(RuntimeWarning, match="naive datetime"):
        User.objects.create(username="naive", date_joined=datetime(2026, 1, 1, 12, 0))
