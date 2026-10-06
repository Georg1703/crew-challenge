"""S3 stand-in for the browser while OBJECT_STORAGE_BACKEND = "memory" and DEBUG (make e2e).

Takes the PUTs of files and parts at the URLs InMemoryObjectStorage signs, and serves the files
back. Mounted by config/urls.py only in that setup; nothing is checked, like a presigned URL.
"""

from __future__ import annotations

from django.http import Http404, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .base import StorageError
from .factory import get_object_storage
from .memory import InMemoryObjectStorage


@csrf_exempt
def memory_bucket(request: HttpRequest, key: str) -> HttpResponse:
    storage = get_object_storage()
    if not isinstance(storage, InMemoryObjectStorage):
        raise Http404
    if request.method == "PUT":
        data = request.read()  # not request.body: parts are bigger than its 2.5 MB limit
        upload_id = request.GET.get("uploadId")
        try:
            etag = (
                storage.upload_part(
                    key=key,
                    upload_id=upload_id,
                    part_number=int(request.GET.get("partNumber", 0)),
                    data=data,
                )
                if upload_id
                else storage.put_object(
                    key=key,
                    data=data,
                    content_type=request.META.get("CONTENT_TYPE", "application/octet-stream"),
                )
            )
        except StorageError:  # an unknown upload or a bad part number
            return HttpResponse(status=400)
        response = HttpResponse()
        response["ETag"] = etag
        # Like S3; Uppy reads it, else builds it with `new URL()`, which fails on a relative URL.
        response["Location"] = request.build_absolute_uri(request.path)
        return response
    stored = storage.objects.get(key)
    if stored is None:
        raise Http404
    return HttpResponse(stored.data, content_type=stored.content_type)
