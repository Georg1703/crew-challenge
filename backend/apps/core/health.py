"""Liveness checks used by /api/health (Caddy, deploy script, monitoring)."""

from collections.abc import Callable

import redis
from django.conf import settings
from django.db import connection

Check = Callable[[], None]


def check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_redis() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1, socket_connect_timeout=1)
    try:
        client.ping()
    finally:
        client.close()


CHECKS: dict[str, Check] = {"database": check_database, "redis": check_redis}


def run_checks(checks: dict[str, Check] | None = None) -> tuple[bool, dict[str, str]]:
    """Run every check. Returns (all_ok, {name: "ok" | "error"})."""
    results: dict[str, str] = {}
    for name, check in (checks or CHECKS).items():
        try:
            check()
        except Exception:
            results[name] = "error"
        else:
            results[name] = "ok"
    return all(value == "ok" for value in results.values()), results
