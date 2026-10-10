from typing import Any

from rest_framework import serializers

from apps.media import selectors as media
from apps.media.models import Upload
from apps.proofs.models import Proof
from apps.proofs.services import ProofUpload


class ProofOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=Proof.Kind.choices)
    status = serializers.ChoiceField(choices=Proof.Status.choices)
    url = serializers.CharField(allow_null=True, help_text="The file, once fully uploaded.")
    hls_url = serializers.CharField(
        allow_null=True,
        help_text="A video's HLS playlist once transcoded (production only); else play `url`.",
    )
    thumb_url = serializers.CharField(
        allow_null=True,
        help_text="A video's poster once ready, else a small JPEG from the phone; else show `url`.",
    )
    phone_thumb_url = serializers.CharField(
        allow_null=True,
        help_text="The phone's own small JPEG, if it made one: show it when `thumb_url` fails.",
    )
    created_at = serializers.DateTimeField()
    duration = serializers.IntegerField(
        allow_null=True, help_text="A video's length in seconds, when the phone could read it."
    )
    posted = serializers.BooleanField(
        help_text="Posted (the crew sees it); else a draft file its owner can still remove."
    )


def proof_data(proof: Proof) -> dict[str, Any]:
    hls_url, poster_url = media.renditions(proof.original)
    return {
        "id": proof.pk,
        "kind": proof.kind,
        "status": proof.status,
        "url": media.url(proof.original),
        "hls_url": hls_url,
        # A video's poster beats the phone's frame, which some phones (iOS) draw black.
        "thumb_url": poster_url or media.url(proof.thumb),
        "phone_thumb_url": media.url(proof.thumb),
        "created_at": proof.created_at,
        "duration": proof.duration,
        "posted": proof.post_id is not None,
    }


class ProofStartIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=Proof.Kind.choices)
    duration = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="A video's length in whole seconds, from the file's metadata.",
    )
    content_type = serializers.CharField(
        max_length=100, help_text="The file's type, e.g. video/mp4."
    )
    size = serializers.IntegerField(min_value=1, help_text="Bytes.")
    fingerprint = serializers.CharField(
        max_length=300,
        required=False,
        default="",
        allow_blank=True,
        help_text="name|size|lastModified of the picked video, to resume it later.",
    )
    thumb_size = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True,
        default=None,
        help_text="Bytes of the JPEG thumbnail made on the phone, if any.",
    )


class PartOut(serializers.Serializer):
    number = serializers.IntegerField()
    etag = serializers.CharField()


class ProofUploadOut(serializers.Serializer):
    """A proof being uploaded and how to send its files straight to storage."""

    proof = ProofOut()
    mode = serializers.ChoiceField(choices=Upload.Mode.choices)
    content_type = serializers.CharField(help_text="Send this Content-Type with the original.")
    put_url = serializers.CharField(
        allow_null=True, help_text="Single mode (photos): PUT the whole file here."
    )
    part_size = serializers.IntegerField(
        allow_null=True, help_text="Multipart (videos): bytes per part; the last one is smaller."
    )
    part_count = serializers.IntegerField(allow_null=True)
    parts = PartOut(many=True, help_text="Parts already uploaded: skip them when resuming.")
    thumb_put_url = serializers.CharField(
        allow_null=True, help_text="PUT the thumbnail here, Content-Type image/jpeg."
    )


def upload_data(plan: ProofUpload) -> dict[str, Any]:
    proof, original = plan.proof, plan.proof.original
    multipart = original.mode == Upload.Mode.MULTIPART
    return {
        "proof": proof_data(proof),
        "mode": original.mode,
        "content_type": original.content_type,
        "put_url": plan.put_url,
        "part_size": original.part_size if multipart else None,
        "part_count": original.part_count if multipart else None,
        "parts": [{"number": n, "etag": etag} for n, etag in sorted(plan.parts.items())],
        "thumb_put_url": plan.thumb_put_url,
    }


class PartsIn(serializers.Serializer):
    numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=1000
    )


class PartUrlOut(serializers.Serializer):
    number = serializers.IntegerField()
    url = serializers.CharField()


class PartsOut(serializers.Serializer):
    parts = PartUrlOut(many=True)


class PartIn(serializers.Serializer):
    etag = serializers.CharField(max_length=100, help_text="The ETag header S3 answered with.")
