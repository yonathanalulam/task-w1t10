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


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_without_authentication(client, method: str, path: str, kwargs: dict):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_with_invalid_session_cookie(client, method: str, path: str, kwargs: dict):
    client.cookies.update({"trailforge_session": "invalid-session-token", "trailforge_csrf": "invalid-csrf-token"})
    headers = {"X-CSRF-Token": "invalid-csrf-token"}
    response = getattr(client, method)(path, headers=headers, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "kwargs"), PROTECTED_MUTATIONS)
def test_protected_mutations_return_401_with_invalid_bearer_token(client, method: str, path: str, kwargs: dict):
    response = getattr(client, method)(path, headers={"Authorization": "Bearer invalid-token"}, **kwargs)
    assert response.status_code == 401
