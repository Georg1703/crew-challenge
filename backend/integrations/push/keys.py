"""VAPID keys as the two base64url strings pywebpush and a browser take."""

from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02
from py_vapid.utils import b64urlencode


def make_vapid_keys() -> tuple[str, str]:
    """A fresh (public, private) pair: the public key as the browser's applicationServerKey,
    the private one as pywebpush's `vapid_private_key` string."""
    vapid = Vapid02()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    return b64urlencode(public), b64urlencode(private)
