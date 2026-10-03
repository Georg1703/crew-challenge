"""Cursor pagination with the response shape from docs/architecture/api-conventions.md:

{"results": [...], "next": "<cursor or null>"}
"""

from typing import Any
from urllib.parse import parse_qs, urlparse

from rest_framework import pagination
from rest_framework.response import Response


class CursorPagination(pagination.CursorPagination):
    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"
    ordering = "-created_at"

    def get_paginated_response(self, data: Any) -> Response:
        return Response({"results": data, "next": self.get_next_cursor()})

    def get_next_cursor(self) -> str | None:
        """The raw cursor value, so the client sends `?cursor=<next>` without parsing a URL."""
        link = self.get_next_link()
        if link is None:
            return None
        values = parse_qs(urlparse(link).query).get(self.cursor_query_param)
        return values[0] if values else None

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["results", "next"],
            "properties": {
                "results": schema,
                "next": {"type": "string", "nullable": True},
            },
        }
