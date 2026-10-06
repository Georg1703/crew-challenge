import base64
import json
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from integrations.cdn import CloudFront, get_cdn


def unb64(value: str):
    return base64.b64decode(value.translate(str.maketrans("-_~", "+=/")))


def test_signed_cookies_open_one_folder_until_they_expire(cdn, cloudfront_key):
    expires_at = datetime(2026, 11, 11, 8, tzinfo=UTC)

    cookies = cdn.cookies(prefix="crews/c1/", expires_at=expires_at)

    policy = unb64(cookies["CloudFront-Policy"])
    assert json.loads(policy) == {
        "Statement": [
            {
                "Resource": "https://media.crew.example/crews/c1/*",
                "Condition": {"DateLessThan": {"AWS:EpochTime": int(expires_at.timestamp())}},
            }
        ]
    }
    cloudfront_key.public_key().verify(  # raises if the signature is wrong
        unb64(cookies["CloudFront-Signature"]), policy, padding.PKCS1v15(), hashes.SHA1()
    )
    assert cookies["CloudFront-Key-Pair-Id"] == "K2ABC"
    assert not set("+=/") & set(cookies["CloudFront-Signature"])
    assert cdn.cookie_domain == "crew.example"
    assert cdn.url("crews/c1/a.jpg") == "https://media.crew.example/crews/c1/a.jpg"


def test_only_rsa_keys_sign():
    pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with pytest.raises(ValueError, match="RSA"):
        CloudFront(domain="m.x", key_pair_id="K", private_key_pem=pem)


def test_no_cdn_locally_and_a_half_setup_is_refused():
    try:
        get_cdn.cache_clear()
        assert get_cdn() is None  # tests and local development
        get_cdn.cache_clear()
        with (
            override_settings(MEDIA_CDN_DOMAIN="media.crew.example", CLOUDFRONT_KEY_PAIR_ID=""),
            pytest.raises(ImproperlyConfigured),
        ):
            get_cdn()
    finally:
        get_cdn.cache_clear()
