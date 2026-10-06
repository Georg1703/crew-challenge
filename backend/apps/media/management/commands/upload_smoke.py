"""Check the S3 adapter against the real dev bucket: `make upload-smoke`.

Does what the browser does: one presigned PUT of a small file (read back with a presigned GET),
then a two-part multipart upload, sending the app's Origin so the bucket's CORS must expose
`ETag`. Checks each object and deletes everything it made. Uses the AWS profile and bucket from
`.env`; tests never run it.
"""

import uuid
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from integrations.storage import MIN_PART_SIZE, UploadedPart, UploadNotFound, get_object_storage


def put(url: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """PUT like the browser and return the ETag S3 lets the page read."""
    origin = settings.APP_PUBLIC_URL
    request = Request(
        url, data=data, method="PUT", headers={"Origin": origin, "Content-Type": content_type}
    )
    try:
        with urlopen(request, timeout=60) as response:
            if "etag" not in response.headers.get("Access-Control-Expose-Headers", "").lower():
                raise CommandError(f"Bucket CORS does not expose ETag to {origin}; see infra/aws/.")
            return str(response.headers["ETag"])
    except HTTPError as exc:
        raise CommandError(f"PUT refused: {exc.code} {exc.read()[:300]!r}") from exc


class Command(BaseCommand):
    help = "Upload a small and a multipart file to the media bucket, check them, delete them."

    def handle(self, *args: Any, **options: Any) -> None:
        storage = get_object_storage()
        prefix = f"smoke/{uuid.uuid4()}"
        small, big, dropped = f"{prefix}/small.txt", f"{prefix}/big.bin", f"{prefix}/dropped.bin"
        self.stdout.write(f"Bucket {settings.MEDIA_BUCKET}, objects under {prefix}/")
        try:
            put(storage.presign_put(key=small, content_type="text/plain"), b"hello", "text/plain")
            info = storage.head(key=small)
            if info is None or (info.size, info.content_type) != (5, "text/plain"):
                raise CommandError(f"Single PUT stored {info!r}")
            with urlopen(storage.presign_get(key=small), timeout=60) as response:
                if response.read() != b"hello":
                    raise CommandError("Presigned GET returned other bytes")
            self.stdout.write(self.style.SUCCESS("OK: single presigned PUT, presigned GET"))

            upload_id = storage.create_multipart(key=big, content_type="video/mp4")
            parts = []
            for number, data in ((1, b"a" * MIN_PART_SIZE), (2, b"b" * 1024)):
                url = storage.presign_part(key=big, upload_id=upload_id, part_number=number)
                parts.append(UploadedPart(part_number=number, etag=put(url, data)))
            if [p.part_number for p in storage.list_parts(key=big, upload_id=upload_id)] != [1, 2]:
                raise CommandError("list_parts does not show both parts")
            info = storage.complete_multipart(key=big, upload_id=upload_id, parts=parts)
            if info.size != MIN_PART_SIZE + 1024:
                raise CommandError(f"Multipart upload stored {info!r}")
            self.stdout.write(self.style.SUCCESS("OK: multipart upload, ETags exposed by CORS"))

            upload_id = storage.create_multipart(key=dropped, content_type="video/mp4")
            storage.abort_multipart(key=dropped, upload_id=upload_id)
            storage.abort_multipart(key=dropped, upload_id=upload_id)
            try:
                storage.list_parts(key=dropped, upload_id=upload_id)
                raise CommandError("An aborted upload still lists parts")
            except UploadNotFound:
                self.stdout.write(self.style.SUCCESS("OK: abort, twice"))
        finally:
            storage.delete(key=small)
            storage.delete_prefix(prefix=f"{prefix}/")
        if storage.list_keys(prefix=f"{prefix}/"):
            raise CommandError("Delete left objects behind")
        self.stdout.write(self.style.SUCCESS("OK: delete, list and delete by prefix"))
