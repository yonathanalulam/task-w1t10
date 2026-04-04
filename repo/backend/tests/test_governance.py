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


def test_org_admin_can_manage_datasets_projects_and_links(client, test_user):
    csrf = login(client, test_user)

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-dataset-main", "description": "catalog", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-project-main",
            "code": "PRJ-001",
            "description": "workspace",
            "status": "active",
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    link = client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert link.status_code == 201

    links = client.get(f"/api/projects/{project_id}/datasets")
    assert links.status_code == 200
    assert links.json()[0]["dataset_id"] == dataset_id


def test_planner_cannot_access_admin_governance_routes(client, planner_user):
    csrf = login(client, planner_user)

    response = client.get("/api/datasets")
    assert response.status_code == 403

    create_response = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-dataset-denied", "description": "nope", "status": "active"},
    )
    assert create_response.status_code == 403

    attractions_response = client.get("/api/datasets/does-not-matter/attractions")
    assert attractions_response.status_code == 403


def test_org_isolation_blocks_cross_org_access(client, test_user, other_org_admin):
    csrf_a = login(client, test_user)

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf_a},
        json={"name": "pytest-dataset-org-a", "description": "A", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf_a},
        json={"name": "pytest-project-org-a", "code": "A-001", "description": "A", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a})

    csrf_b = login(client, other_org_admin)

    get_dataset = client.patch(
        f"/api/datasets/{dataset_id}",
        headers={"X-CSRF-Token": csrf_b},
        json={"name": "should-not-work"},
    )
    assert get_dataset.status_code == 404

    link = client.post(
        f"/api/projects/{project_id}/datasets/{dataset_id}",
        headers={"X-CSRF-Token": csrf_b},
    )
    assert link.status_code == 404


def test_project_membership_management(client, test_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    admin_id = users.json()[0]["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-project-members", "code": "MEM-1", "description": "", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": csrf},
        json={"user_id": admin_id, "role_in_project": "owner", "can_edit": True},
    )
    assert add_member.status_code == 201
    member_id = add_member.json()["id"]

    update_member = client.patch(
        f"/api/projects/{project_id}/members/{member_id}",
        headers={"X-CSRF-Token": csrf},
        json={"role_in_project": "reviewer", "can_edit": False},
    )
    assert update_member.status_code == 200
    assert update_member.json()["can_edit"] is False

    remove_member = client.delete(
        f"/api/projects/{project_id}/members/{member_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert remove_member.status_code == 204

    audit_events = client.get("/api/ops/audit/events?limit=50")
    assert audit_events.status_code == 200
    rows = audit_events.json()

    created = next(row for row in rows if row["action_type"] == "governance.project_member_created")
    assert created["resource_id"] == member_id
    assert created["metadata_json"]["project_id"] == project_id
    assert created["metadata_json"]["user_id"] == admin_id
    assert created["metadata_json"]["role_in_project"] == "owner"
    assert created["metadata_json"]["can_edit"] is True

    updated = next(row for row in rows if row["action_type"] == "governance.project_member_updated")
    assert updated["resource_id"] == member_id
    assert updated["metadata_json"]["role_in_project"] == "reviewer"
    assert updated["metadata_json"]["can_edit"] is False

    deleted = next(row for row in rows if row["action_type"] == "governance.project_member_deleted")
    assert deleted["resource_id"] == member_id
    assert deleted["metadata_json"]["project_id"] == project_id
    assert deleted["metadata_json"]["user_id"] == admin_id
    assert deleted["metadata_json"]["role_in_project"] == "reviewer"
    assert deleted["metadata_json"]["can_edit"] is False


def test_org_admin_can_manage_attractions_duplicates_and_merge(client, test_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-dataset-attractions", "description": "catalog", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    create_primary = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "PyTest Museum",
            "city": "Austin",
            "state": "TX",
            "description": "original",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert create_primary.status_code == 201
    primary_id = create_primary.json()["id"]

    create_duplicate = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "  pytest museum!!!",
            "city": "AUSTIN",
            "state": "tx",
            "description": "duplicate",
            "latitude": 30.268,
            "longitude": -97.742,
            "duration_minutes": 75,
            "status": "active",
        },
    )
    assert create_duplicate.status_code == 201
    duplicate_id = create_duplicate.json()["id"]

    duplicate_groups = client.get(f"/api/datasets/{dataset_id}/attractions/duplicates")
    assert duplicate_groups.status_code == 200
    groups_payload = duplicate_groups.json()
    assert len(groups_payload) == 1
    assert groups_payload[0]["candidate_count"] == 2

    merge = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_attraction_id": duplicate_id,
            "target_attraction_id": primary_id,
            "merge_reason": "deterministic duplicate key match",
        },
    )
    assert merge.status_code == 200

    post_merge_groups = client.get(f"/api/datasets/{dataset_id}/attractions/duplicates")
    assert post_merge_groups.status_code == 200
    assert post_merge_groups.json() == []

    attractions = client.get(f"/api/datasets/{dataset_id}/attractions")
    assert attractions.status_code == 200
    merged_source = next(row for row in attractions.json() if row["id"] == duplicate_id)
    assert merged_source["merged_into_attraction_id"] == primary_id
    assert merged_source["status"] == "merged"


def test_attraction_validation_and_merge_error_paths(client, test_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-dataset-validation", "description": "catalog", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    invalid_duration = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-too-short",
            "city": "Austin",
            "state": "TX",
            "description": "bad",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 4,
            "status": "active",
        },
    )
    assert invalid_duration.status_code == 422

    first = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-park",
            "city": "Austin",
            "state": "TX",
            "description": "first",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 60,
            "status": "active",
        },
    )
    second = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-library",
            "city": "Dallas",
            "state": "TX",
            "description": "second",
            "latitude": 32.7767,
            "longitude": -96.797,
            "duration_minutes": 80,
            "status": "active",
        },
    )
    assert first.status_code == 201
    assert second.status_code == 201
    first_id = first.json()["id"]
    second_id = second.json()["id"]

    same_id_merge = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={"source_attraction_id": first_id, "target_attraction_id": first_id},
    )
    assert same_id_merge.status_code == 422

    mismatch_merge = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={"source_attraction_id": first_id, "target_attraction_id": second_id},
    )
    assert mismatch_merge.status_code == 422


def test_attraction_org_isolation_blocks_cross_org_access(client, test_user, other_org_admin):
    csrf_a = login(client, test_user)

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf_a},
        json={"name": "pytest-dataset-org-attractions", "description": "A", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    attraction = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf_a},
        json={
            "name": "pytest-org-a-attraction",
            "city": "Austin",
            "state": "TX",
            "description": "A",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert attraction.status_code == 201
    attraction_id = attraction.json()["id"]

    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a})
    csrf_b = login(client, other_org_admin)

    list_other_org = client.get(f"/api/datasets/{dataset_id}/attractions")
    assert list_other_org.status_code == 404

    patch_other_org = client.patch(
        f"/api/datasets/{dataset_id}/attractions/{attraction_id}",
        headers={"X-CSRF-Token": csrf_b},
        json={"name": "should-not-work"},
    )
    assert patch_other_org.status_code == 404


def test_project_membership_changes_require_recent_step_up(client, test_user):
    csrf = login(client, test_user)

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    admin_id = users.json()[0]["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-project-members-stepup", "code": "MEM-SU", "description": "", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    add_without_step_up = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": csrf},
        json={"user_id": admin_id, "role_in_project": "owner", "can_edit": True},
    )
    assert add_without_step_up.status_code == 403
    assert "Step-up authentication required" in add_without_step_up.json()["detail"]

    step_up(client, csrf, password=test_user["password"])

    add_with_step_up = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": csrf},
        json={"user_id": admin_id, "role_in_project": "owner", "can_edit": True},
    )
    assert add_with_step_up.status_code == 201
    member_id = add_with_step_up.json()["id"]

    update_with_step_up = client.patch(
        f"/api/projects/{project_id}/members/{member_id}",
        headers={"X-CSRF-Token": csrf},
        json={"can_edit": False},
    )
    assert update_with_step_up.status_code == 200

    remove_with_step_up = client.delete(
        f"/api/projects/{project_id}/members/{member_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert remove_with_step_up.status_code == 204


def test_attraction_merge_requires_recent_step_up(client, test_user):
    csrf = login(client, test_user)

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-dataset-merge-stepup", "description": "catalog", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    create_primary = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "PyTest StepUp Museum",
            "city": "Austin",
            "state": "TX",
            "description": "original",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert create_primary.status_code == 201
    primary_id = create_primary.json()["id"]

    create_duplicate = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest stepup museum",
            "city": "AUSTIN",
            "state": "tx",
            "description": "duplicate",
            "latitude": 30.268,
            "longitude": -97.742,
            "duration_minutes": 75,
            "status": "active",
        },
    )
    assert create_duplicate.status_code == 201
    duplicate_id = create_duplicate.json()["id"]

    merge_without_step_up = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_attraction_id": duplicate_id,
            "target_attraction_id": primary_id,
            "merge_reason": "step-up gate",
        },
    )
    assert merge_without_step_up.status_code == 403
    assert "Step-up authentication required" in merge_without_step_up.json()["detail"]

    step_up(client, csrf, password=test_user["password"])

    merge_with_step_up = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_attraction_id": duplicate_id,
            "target_attraction_id": primary_id,
            "merge_reason": "step-up gate",
        },
    )
    assert merge_with_step_up.status_code == 200
