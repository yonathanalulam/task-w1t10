from __future__ import annotations

import io
import zipfile

import pytest


def _empty_sync_zip() -> bytes:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("placeholder.txt", b"placeholder")
    return payload.getvalue()


PROTECTED_MUTATIONS = [
    (
        "post",
        "/api/projects",
        {"json": {"name": "pytest-project-unauth", "code": "UA-1", "description": "auth", "status": "active"}},
    ),
    (
        "post",
        "/api/projects/project-123/datasets/dataset-123",
        {},
    ),
    (
        "post",
        "/api/projects/project-123/itineraries",
        {"json": {"name": "pytest-itinerary-unauth", "status": "draft"}},
    ),
    (
        "post",
        "/api/projects/project-123/sync-package/import",
        {"files": {"file": ("sync.zip", _empty_sync_zip(), "application/zip")}},
    ),
]


def _assert_unauthorized_body(response) -> None:
    assert response.headers["content-type"].startswith("application/json"), (
        f"unauthorized responses must be JSON, got {response.headers.get('content-type')!r}"
    )
    payload = response.json()
    assert isinstance(payload, dict), f"expected dict body, got {type(payload).__name__}"
    assert "detail" in payload, f"401 body missing `detail` field: {payload!r}"
    assert isinstance(payload["detail"], str) and payload["detail"], "detail must be a non-empty string"


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_without_authentication(client, method: str, path: str, kwargs: dict):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401
    _assert_unauthorized_body(response)
    # No session/csrf cookie should be issued on an unauthenticated failure.
    assert client.cookies.get("trailforge_session") is None
    assert client.cookies.get("trailforge_csrf") is None


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_with_invalid_session_cookie(client, method: str, path: str, kwargs: dict):
    client.cookies.update({"trailforge_session": "invalid-session-token", "trailforge_csrf": "invalid-csrf-token"})
    headers = {"X-CSRF-Token": "invalid-csrf-token"}
    response = getattr(client, method)(path, headers=headers, **kwargs)
    assert response.status_code == 401
    _assert_unauthorized_body(response)


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_with_invalid_bearer_token(client, method: str, path: str, kwargs: dict):
    response = getattr(client, method)(path, headers={"Authorization": "Bearer invalid-token"}, **kwargs)
    assert response.status_code == 401
    _assert_unauthorized_body(response)


def test_login_rejects_wrong_password_with_invalid_credentials_detail(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "org_slug": test_user["org_slug"],
            "username": test_user["username"],
            "password": "wrong-password-9999",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body == {"detail": "Invalid credentials"}, (
        f"login failure must not leak which field was wrong; got {body!r}"
    )
    # Failed login must not establish a session or CSRF cookie.
    assert client.cookies.get("trailforge_session") is None
    assert client.cookies.get("trailforge_csrf") is None


def test_login_rejects_missing_fields_with_422_and_field_errors(client):
    response = client.post("/api/auth/login", json={"org_slug": "default-org", "username": "admin"})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)
    missing_fields = {entry["loc"][-1] for entry in body["detail"] if entry.get("type") == "missing"}
    assert "password" in missing_fields


def test_me_without_session_returns_401_json(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    _assert_unauthorized_body(response)
