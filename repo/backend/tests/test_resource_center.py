from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.models.resource_center import ResourceAsset
from app.services.resource_center import run_cleanup_eligible_assets


def login(client, creds: dict[str, str]) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "org_slug": creds["org_slug"],
            "username": creds["username"],
            "password": creds["password"],
        },
    )
    assert response.status_code == 200
    csrf_token = client.cookies.get("trailforge_csrf")
    assert csrf_token
    return csrf_token


def step_up(client, csrf: str, *, password: str) -> None:
    response = client.post("/api/auth/step-up", headers={"X-CSRF-Token": csrf}, json={"password": password})
    assert response.status_code == 200


def create_project_dataset_attraction(client, csrf: str, *, suffix: str) -> tuple[str, str, str]:
    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-media-dataset-{suffix}", "description": "resource", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-media-project-{suffix}", "code": f"PM-{suffix}", "description": "resource", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    link = client.post(f"/api/projects/{project_id}/datasets/{dataset_id}", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 201

    attraction = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-media-attraction-{suffix}",
            "city": "Austin",
            "state": "TX",
            "description": "resource",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert attraction.status_code == 201
    return project_id, dataset_id, attraction.json()["id"]


def create_itinerary(client, csrf: str, *, project_id: str, suffix: str) -> str:
    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-media-itinerary-{suffix}", "status": "draft"},
    )
    assert itinerary.status_code == 201
    return itinerary.json()["id"]


def test_resource_center_upload_list_download_and_unreference(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_id = create_project_dataset_attraction(client, csrf, suffix="full")
    itinerary_id = create_itinerary(client, csrf, project_id=project_id, suffix="full")

    png_payload = b"\x89PNG\r\n\x1a\n" + b"png-bytes"
    upload_attraction = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("attraction-map.png", png_payload, "image/png")},
    )
    assert upload_attraction.status_code == 201
    attraction_asset = upload_attraction.json()["asset"]
    assert attraction_asset["preview_kind"] == "image"
    assert attraction_asset["detected_mime_type"] == "image/png"
    assert len(attraction_asset["sha256_checksum"]) == 64
    assert upload_attraction.json()["validation"]["signature_valid"] is True

    list_attraction_assets = client.get(f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets")
    assert list_attraction_assets.status_code == 200
    assert len(list_attraction_assets.json()) == 1

    download_attraction = client.get(f"/api/projects/{project_id}/resources/assets/{attraction_asset['id']}/download")
    assert download_attraction.status_code == 200
    assert download_attraction.content == png_payload
    assert download_attraction.headers["content-disposition"].startswith("inline")

    pdf_payload = b"%PDF-1.7\nresource-center\n"
    upload_itinerary = client.post(
        f"/api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("brief.pdf", pdf_payload, "application/pdf")},
    )
    assert upload_itinerary.status_code == 201
    itinerary_asset = upload_itinerary.json()["asset"]
    assert itinerary_asset["preview_kind"] == "document"

    list_itinerary_assets = client.get(f"/api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets")
    assert list_itinerary_assets.status_code == 200
    assert len(list_itinerary_assets.json()) == 1

    unreference = client.delete(
        f"/api/projects/{project_id}/resources/assets/{itinerary_asset['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert unreference.status_code == 200
    assert unreference.json()["itinerary_id"] is None
    assert unreference.json()["cleanup_eligible_at"] is not None


def test_resource_center_rejects_signature_extension_mismatch(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_id = create_project_dataset_attraction(client, csrf, suffix="mismatch")

    png_payload = b"\x89PNG\r\n\x1a\n" + b"bad-mismatch"
    upload = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("looks-like-pdf.pdf", png_payload, "application/pdf")},
    )
    assert upload.status_code == 422
    assert "does not match detected" in upload.json()["detail"]


def test_resource_center_rejects_oversized_upload(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_id = create_project_dataset_attraction(client, csrf, suffix="oversized")
    max_bytes = get_settings().asset_upload_max_bytes

    oversized_jpeg = b"\xff\xd8\xff" + (b"a" * (max_bytes + 1))
    upload = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("too-large.jpg", oversized_jpeg, "image/jpeg")},
    )
    assert upload.status_code == 422
    assert "exceeds max allowed size" in upload.json()["detail"]


def test_resource_center_read_only_planner_can_view_but_not_upload(client, test_user, planner_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])
    users = client.get("/api/admin/users")
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    project_id, _, attraction_id = create_project_dataset_attraction(client, admin_csrf, suffix="readonly")
    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": admin_csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": False},
    )
    assert add_member.status_code == 201

    seed_upload = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": admin_csrf},
        files={"file": ("seed.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert seed_upload.status_code == 201

    planner_csrf = login(client, planner_user)
    list_assets = client.get(f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets")
    assert list_assets.status_code == 200
    assert len(list_assets.json()) == 1

    forbidden_upload = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": planner_csrf},
        files={"file": ("blocked.csv", b"a,b\n5,6\n", "text/csv")},
    )
    assert forbidden_upload.status_code == 403


def test_resource_center_cleanup_deletes_only_eligible_unreferenced_assets(client, db, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_id = create_project_dataset_attraction(client, csrf, suffix="cleanup")
    itinerary_id = create_itinerary(client, csrf, project_id=project_id, suffix="cleanup")

    upload_unreferenced = client.post(
        f"/api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("cleanup.pdf", b"%PDF-1.7\ncleanup\n", "application/pdf")},
    )
    assert upload_unreferenced.status_code == 201
    unreferenced_asset = upload_unreferenced.json()["asset"]

    upload_referenced = client.post(
        f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("keep.png", b"\x89PNG\r\n\x1a\nkeep", "image/png")},
    )
    assert upload_referenced.status_code == 201
    referenced_asset = upload_referenced.json()["asset"]

    unreference_response = client.delete(
        f"/api/projects/{project_id}/resources/assets/{unreferenced_asset['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert unreference_response.status_code == 200

    unreferenced_row = db.get(ResourceAsset, unreferenced_asset["id"])
    assert unreferenced_row is not None
    unreferenced_row.cleanup_eligible_at = unreferenced_row.created_at

    referenced_row = db.get(ResourceAsset, referenced_asset["id"])
    assert referenced_row is not None
    referenced_row.cleanup_eligible_at = referenced_row.created_at
    db.add(unreferenced_row)
    db.add(referenced_row)
    db.commit()

    storage_root = Path(get_settings().asset_storage_root)
    delete_target_path = storage_root / unreferenced_row.storage_key
    keep_target_path = storage_root / referenced_row.storage_key
    assert delete_target_path.exists()
    assert keep_target_path.exists()

    deleted_count = run_cleanup_eligible_assets(db, max_delete=20)
    assert deleted_count == 1

    assert db.get(ResourceAsset, unreferenced_asset["id"]) is None
    assert db.get(ResourceAsset, referenced_asset["id"]) is not None
    assert not delete_target_path.exists()
    assert keep_target_path.exists()
