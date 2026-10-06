"""Fixtures available to every backend test."""

import sys
from collections.abc import Iterator

import psycopg
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from integrations.cdn import CloudFront, get_cdn
from integrations.storage import InMemoryObjectStorage, get_object_storage
from integrations.transcoding import InMemoryTranscoder, get_transcoder
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


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    """Rate-limit counters live in the cache; start every test from zero."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client() -> APIClient:
    """An anonymous client that enforces CSRF like a browser does."""
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def browser(api_client: APIClient) -> APIClient:
    """Like the SPA: fetched /auth/csrf once and sends X-CSRFToken on every request."""
    token = api_client.get("/api/v1/auth/csrf").json()["csrf_token"]
    api_client.credentials(HTTP_X_CSRFTOKEN=token)
    return api_client


@pytest.fixture
def user(db):
    return UserFactory.create()


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


@pytest.fixture(autouse=True)
def transcoder() -> Iterator[InMemoryTranscoder]:
    """Fresh in-memory transcoder for every test: jobs run until the test finishes them."""
    get_transcoder.cache_clear()
    fake = get_transcoder()
    assert isinstance(fake, InMemoryTranscoder)
    yield fake
    get_transcoder.cache_clear()


@pytest.fixture(scope="session")
def cloudfront_key() -> rsa.RSAPrivateKey:
    """One RSA key for every test that signs CloudFront cookies (2048-bit keys are slow to make)."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def cdn(tmp_path, cloudfront_key) -> Iterator[CloudFront]:
    """Media through CloudFront at media.crew.example, as in production."""
    path = tmp_path / "cloudfront.pem"
    path.write_bytes(
        cloudfront_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    get_cdn.cache_clear()
    with override_settings(
        MEDIA_CDN_DOMAIN="media.crew.example",
        CLOUDFRONT_KEY_PAIR_ID="K2ABC",
        CLOUDFRONT_PRIVATE_KEY_PATH=str(path),
    ):
        cloudfront = get_cdn()
        assert cloudfront is not None
        yield cloudfront
    get_cdn.cache_clear()
