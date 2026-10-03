"""Fixtures available to every backend test."""

import sys
from collections.abc import Iterator

import psycopg
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from integrations.storage import InMemoryObjectStorage, get_object_storage
from tests.factories import UserFactory


def pytest_sessionstart(session: pytest.Session) -> None:
    """Stop at once with a clear message when the test database server is unreachable."""
    db = settings.DATABASES["default"]
    try:
        psycopg.connect(
            host=db["HOST"],
            port=db["PORT"] or 5432,
            user=db["USER"],
            password=db["PASSWORD"],
            dbname="postgres",
            connect_timeout=3,
        ).close()
    except psycopg.OperationalError as exc:
        lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
        reason = lines[0].removeprefix("connection failed: ") if lines else "unknown error"
        sys.stderr.write(
            "\nCannot connect to the test Postgres server at "
            f"{db['USER']}@{db['HOST']}:{db['PORT'] or 5432}\n"
            f"  reason: {reason}\n\n"
            "Tests need Postgres. Start one with:\n"
            "  docker run -d --name cc-db -p 5432:5432 -e POSTGRES_USER=crew \\\n"
            "    -e POSTGRES_PASSWORD=crew-local-password \\\n"
            "    -e POSTGRES_DB=crew_challenges postgres:17\n"
            "or set TEST_DATABASE_URL (in .env) to a server where that user can create\n"
            "databases.\n\n"
        )
        pytest.exit("test database unreachable", returncode=3)


@pytest.fixture
def api_client() -> APIClient:
    """An anonymous client that enforces CSRF like a browser does."""
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user) -> APIClient:
    """A logged-in client (session auth, CSRF not enforced)."""
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def object_storage() -> Iterator[InMemoryObjectStorage]:
    """Fresh in-memory storage for every test (tests never reach AWS)."""
    get_object_storage.cache_clear()
    storage = get_object_storage()
    assert isinstance(storage, InMemoryObjectStorage)
    yield storage
    get_object_storage.cache_clear()
