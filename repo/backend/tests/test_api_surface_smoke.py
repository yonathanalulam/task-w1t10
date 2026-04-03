from __future__ import annotations


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


def test_additional_route_surface_smoke(client, test_user, planner_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    planner_users = client.get("/api/planner/users")
    assert planner_users.status_code == 200

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-surface-dataset", "description": "surface", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-surface-project", "code": "SURFACE", "description": "surface", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    link_dataset = client.post(f"/api/projects/{project_id}/datasets/{dataset_id}", headers={"X-CSRF-Token": csrf})
    assert link_dataset.status_code == 201

    list_project_datasets = client.get(f"/api/projects/{project_id}/datasets")
    assert list_project_datasets.status_code == 200
    assert list_project_datasets.json()[0]["dataset_id"] == dataset_id

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": True},
    )
    assert add_member.status_code == 201

    list_members = client.get(f"/api/projects/{project_id}/members")
    assert list_members.status_code == 200
    assert any(member["user_id"] == planner_id for member in list_members.json())

    attraction = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-surface-attraction",
            "city": "Austin",
            "state": "TX",
            "description": "surface",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert attraction.status_code == 201
    attraction_id = attraction.json()["id"]

    catalog = client.get(f"/api/projects/{project_id}/catalog/attractions")
    assert catalog.status_code == 200
    assert any(row["id"] == attraction_id for row in catalog.json())

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-surface-itinerary", "status": "draft", "assigned_planner_user_id": planner_id},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    itinerary_list = client.get(f"/api/projects/{project_id}/itineraries")
    assert itinerary_list.status_code == 200
    assert any(row["id"] == itinerary_id for row in itinerary_list.json())

    itinerary_get = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}")
    assert itinerary_get.status_code == 200

    itinerary_patch = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}",
        headers={"X-CSRF-Token": csrf},
        json={"description": "surface-updated"},
    )
    assert itinerary_patch.status_code == 200

    add_day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": csrf},
        json={"day_number": 1, "title": "Surface Day"},
    )
    assert add_day.status_code == 200
    day_id = add_day.json()["days"][0]["id"]

    patch_day = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}",
        headers={"X-CSRF-Token": csrf},
        json={"title": "Surface Day Updated"},
    )
    assert patch_day.status_code == 200

    add_stop = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": csrf},
        json={"attraction_id": attraction_id, "start_minute_of_day": 540, "duration_minutes": 90},
    )
    assert add_stop.status_code == 200
    stop_id = add_stop.json()["days"][0]["stops"][0]["id"]

    patch_stop = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}",
        headers={"X-CSRF-Token": csrf},
        json={"duration_minutes": 95},
    )
    assert patch_stop.status_code == 200

    delete_stop = client.delete(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_stop.status_code == 200

    delete_day = client.delete(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_day.status_code == 200

    delete_itinerary = client.delete(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert delete_itinerary.status_code == 204

    unlink_dataset = client.delete(f"/api/projects/{project_id}/datasets/{dataset_id}", headers={"X-CSRF-Token": csrf})
    assert unlink_dataset.status_code == 204

    retention_run = client.post("/api/ops/retention/run", headers={"X-CSRF-Token": csrf})
    assert retention_run.status_code == 200

    retention_runs = client.get("/api/ops/retention/runs?limit=10")
    assert retention_runs.status_code == 200
    assert any(row["id"] == retention_run.json()["id"] for row in retention_runs.json())
