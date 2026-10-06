import pytest

from tests.factories import DEFAULT_PASSWORD, MemberFactory, UserFactory

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"


def test_csrf_endpoint_sets_the_cookie(api_client):
    response = api_client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    assert response.cookies["crew_csrftoken"].value
    assert response.json()["csrf_token"]


def test_login_without_csrf_token_is_rejected(api_client):
    UserFactory.create(username="ana")
    response = api_client.post(
        LOGIN, {"username": "ana", "password": DEFAULT_PASSWORD}, format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_login_starts_a_session(browser):
    member = MemberFactory.create(user__username="ana")
    response = browser.post(LOGIN, {"username": "Ana", "password": DEFAULT_PASSWORD}, format="json")
    assert response.status_code == 204
    assert response.cookies["crew_session"]["httponly"]
    me = browser.get("/api/v1/me").json()
    assert me["member"]["id"] == str(member.id)


def test_wrong_password(browser):
    UserFactory.create(username="ana")
    response = browser.post(LOGIN, {"username": "ana", "password": "nope"}, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_input_is_validated(browser):
    response = browser.post(LOGIN, {"username": "ana"}, format="json")
    assert response.status_code == 400
    assert "password" in response.json()["error"]["fields"]


def test_login_is_rate_limited_per_ip(browser):
    for _ in range(5):
        browser.post(LOGIN, {"username": "x", "password": "y"}, format="json")
    response = browser.post(LOGIN, {"username": "x", "password": "y"}, format="json")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "throttled"


def test_logout_ends_the_session(browser):
    UserFactory.create(username="ana")
    browser.post(LOGIN, {"username": "ana", "password": DEFAULT_PASSWORD}, format="json")
    # Django rotates the CSRF token on login; the SPA re-reads the cookie.
    browser.credentials(HTTP_X_CSRFTOKEN=browser.cookies["crew_csrftoken"].value)
    assert browser.post("/api/v1/auth/logout").status_code == 204
    assert browser.get("/api/v1/me").status_code == 401


def test_logout_requires_a_session(browser):
    assert browser.post("/api/v1/auth/logout").status_code == 401
