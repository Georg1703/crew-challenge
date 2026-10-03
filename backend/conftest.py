"""Fixtures available to every backend test."""

from collections.abc import Iterator

import pytest
from rest_framework.test import APIClient

from integrations.storage import InMemoryObjectStorage, get_object_storage
from tests.factories import UserFactory


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
