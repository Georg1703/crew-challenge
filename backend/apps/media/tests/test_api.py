import pytest

from tests.factories import MemberFactory

pytestmark = pytest.mark.django_db


def test_media_session_sets_cookies_only_with_a_cdn(browser, cdn):
    member = MemberFactory.create()
    browser.force_login(member.user)

    response = browser.post("/api/v1/media/session")

    assert response.status_code == 200
    assert response.json()["expires_at"]
    cookie = response.cookies["CloudFront-Signature"]
    assert (cookie["domain"], cookie["secure"], cookie["httponly"], cookie["samesite"]) == (
        "crew.example",
        True,
        True,
        "Lax",
    )


def test_media_session_is_a_no_op_locally(browser):
    browser.force_login(MemberFactory.create().user)
    response = browser.post("/api/v1/media/session")
    assert response.json() == {"expires_at": None}
    assert not response.cookies.get("CloudFront-Policy")


def test_media_session_needs_a_login(browser):
    assert browser.post("/api/v1/media/session").status_code == 401
