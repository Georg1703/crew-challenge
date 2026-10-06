"""CloudFront in front of the private media bucket: media URLs, and the signed cookies that let
the browser read one crew's folder (photos, posters and every HLS segment) with one cookie set.

Signed with the private key whose public half is in the distribution's trusted key group.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class CloudFront:
    def __init__(self, *, domain: str, key_pair_id: str, private_key_pem: bytes) -> None:
        key = serialization.load_pem_private_key(private_key_pem, password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise ValueError("CloudFront signs with an RSA private key.")
        self.domain = domain
        self.key_pair_id = key_pair_id
        self._key = key

    @property
    def cookie_domain(self) -> str:
        """The app's host: media.<host> is its subdomain, so the cookies reach both."""
        return self.domain.split(".", 1)[1]

    def url(self, key: str) -> str:
        return f"https://{self.domain}/{key}"

    def cookies(self, *, prefix: str, expires_at: datetime) -> dict[str, str]:
        """Signed cookies opening every object under `prefix` until `expires_at`."""
        policy = json.dumps(
            {
                "Statement": [
                    {
                        "Resource": f"https://{self.domain}/{prefix}*",
                        "Condition": {
                            "DateLessThan": {"AWS:EpochTime": int(expires_at.timestamp())}
                        },
                    }
                ]
            },
            separators=(",", ":"),  # CloudFront wants the policy without whitespace
        ).encode()
        # CloudFront verifies RSA-SHA1 signatures for signed cookies.
        signature = self._key.sign(policy, padding.PKCS1v15(), hashes.SHA1())
        return {
            "CloudFront-Policy": _b64(policy),
            "CloudFront-Signature": _b64(signature),
            "CloudFront-Key-Pair-Id": self.key_pair_id,
        }


def _b64(data: bytes) -> str:
    """CloudFront's URL-safe base64: '+' -> '-', '=' -> '_', '/' -> '~'."""
    return base64.b64encode(data).decode().translate(str.maketrans("+=/", "-_~"))
