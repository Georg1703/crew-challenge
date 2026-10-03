import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.core.pagination import CursorPagination
from tests.factories import UserFactory


class UsersByJoinDate(CursorPagination):
    page_size = 2
    ordering = "-date_joined"


def _page(cursor=None):
    params = {"cursor": cursor} if cursor else {}
    request = Request(APIRequestFactory().get("/users", params))
    paginator = UsersByJoinDate()
    items = paginator.paginate_queryset(User.objects.all(), request)
    assert items is not None
    return paginator.get_paginated_response([u.username for u in items]).data


@pytest.mark.django_db
def test_cursor_pages_have_results_and_next():
    UserFactory.create_batch(3)

    first = _page()
    assert len(first["results"]) == 2
    assert isinstance(first["next"], str)

    second = _page(first["next"])
    assert len(second["results"]) == 1
    assert second["next"] is None
    assert set(first["results"]).isdisjoint(second["results"])


def test_schema_shape():
    schema = CursorPagination().get_paginated_response_schema({"type": "array"})
    assert schema["required"] == ["results", "next"]
    assert schema["properties"]["next"]["nullable"] is True
