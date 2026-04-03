from __future__ import annotations

import io
import json
import zipfile

from openpyxl import Workbook


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


def create_project_dataset_catalog(client, csrf: str, *, suffix: str) -> tuple[str, str, str, str]:
    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-dataset-{suffix}", "description": "planner", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-project-{suffix}", "code": f"PP-{suffix}", "description": "planner", "status": "active"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    link = client.post(f"/api/projects/{project_id}/datasets/{dataset_id}", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 201

    attraction_a = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-attraction-a-{suffix}",
            "city": "Austin",
            "state": "TX",
            "description": "A",
            "latitude": 30.2672,
            "longitude": -97.7431,
            "duration_minutes": 90,
            "status": "active",
        },
    )
    assert attraction_a.status_code == 201

    attraction_b = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-attraction-b-{suffix}",
            "city": "San Antonio",
            "state": "TX",
            "description": "B",
            "latitude": 29.4241,
            "longitude": -98.4936,
            "duration_minutes": 120,
            "status": "active",
        },
    )
    assert attraction_b.status_code == 201

    return project_id, dataset_id, attraction_a.json()["id"], attraction_b.json()["id"]


def test_planner_core_workflow_with_versions_and_warnings(client, test_user, planner_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    project_id, _, attraction_a_id, attraction_b_id = create_project_dataset_catalog(client, admin_csrf, suffix="planner-core")

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": admin_csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": True},
    )
    assert add_member.status_code == 201

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "name": "pytest-itinerary-core",
            "description": "initial",
            "status": "draft",
            "assigned_planner_user_id": planner_id,
            "urban_speed_mph_override": 20,
        },
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]
    assert itinerary.json()["version_counter"] == 1

    day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": admin_csrf},
        json={"day_number": 1, "title": "Day 1"},
    )
    assert day.status_code == 200
    day_id = day.json()["days"][0]["id"]

    stop_a = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "attraction_id": attraction_a_id,
            "start_minute_of_day": 540,
            "duration_minutes": 120,
            "notes": "Morning",
        },
    )
    assert stop_a.status_code == 200

    stop_b = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "attraction_id": attraction_b_id,
            "start_minute_of_day": 720,
            "duration_minutes": 180,
            "notes": "Afternoon",
        },
    )
    assert stop_b.status_code == 200
    stops_payload = stop_b.json()["days"][0]["stops"]
    assert len(stops_payload) == 2

    reorder = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder",
        headers={"X-CSRF-Token": admin_csrf},
        json={"ordered_stop_ids": [stops_payload[1]["id"], stops_payload[0]["id"]]},
    )
    assert reorder.status_code == 200
    reordered_stops = reorder.json()["days"][0]["stops"]
    assert reordered_stops[0]["attraction_id"] == attraction_b_id
    assert reorder.json()["days"][0]["travel_distance_miles"] > 0
    assert reorder.json()["days"][0]["travel_time_minutes"] > 0

    overlap_update = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{reordered_stops[1]['id']}",
        headers={"X-CSRF-Token": admin_csrf},
        json={"start_minute_of_day": 560},
    )
    assert overlap_update.status_code == 200
    warning_codes = {warning["code"] for warning in overlap_update.json()["days"][0]["warnings"]}
    assert "overlap_15m" in warning_codes

    long_day_update = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{reordered_stops[1]['id']}",
        headers={"X-CSRF-Token": admin_csrf},
        json={"duration_minutes": 650},
    )
    assert long_day_update.status_code == 200
    warning_codes = {warning["code"] for warning in long_day_update.json()["days"][0]["warnings"]}
    assert "activity_exceeds_12h" in warning_codes

    versions = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}/versions")
    assert versions.status_code == 200
    assert len(versions.json()) >= 6


def test_planner_project_scoping_and_assignment_guards(client, test_user, planner_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])
    users = client.get("/api/admin/users")
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, admin_csrf, suffix="planner-scope")

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": admin_csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": True},
    )
    assert add_member.status_code == 201

    second_project = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": admin_csrf},
        json={"name": "pytest-project-unscoped", "code": "PP-UNSC", "description": "", "status": "active"},
    )
    assert second_project.status_code == 201
    second_project_id = second_project.json()["id"]

    planner_csrf = login(client, planner_user)

    planner_projects = client.get("/api/planner/projects")
    assert planner_projects.status_code == 200
    planner_project_ids = {row["id"] for row in planner_projects.json()}
    assert project_id in planner_project_ids
    assert second_project_id not in planner_project_ids

    create_unscoped = client.post(
        f"/api/projects/{second_project_id}/itineraries",
        headers={"X-CSRF-Token": planner_csrf},
        json={"name": "pytest-itinerary-unscoped", "status": "draft"},
    )
    assert create_unscoped.status_code == 404

    create_scoped = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": planner_csrf},
        json={
            "name": "pytest-itinerary-scoped",
            "status": "draft",
            "assigned_planner_user_id": planner_id,
        },
    )
    assert create_scoped.status_code == 201
    itinerary_id = create_scoped.json()["id"]

    day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": planner_csrf},
        json={"day_number": 1},
    )
    day_id = day.json()["days"][0]["id"]

    stop = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": planner_csrf},
        json={"attraction_id": attraction_a_id, "start_minute_of_day": 480, "duration_minutes": 60},
    )
    assert stop.status_code == 200


def test_planner_cross_org_isolation(client, test_user, other_org_admin):
    csrf_a = login(client, test_user)
    project_id, _, _, _ = create_project_dataset_catalog(client, csrf_a, suffix="planner-org-a")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf_a},
        json={"name": "pytest-itinerary-org-a", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a})

    csrf_b = login(client, other_org_admin)

    get_cross_org = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}")
    assert get_cross_org.status_code == 404

    mutate_cross_org = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}",
        headers={"X-CSRF-Token": csrf_b},
        json={"name": "should-not-work"},
    )
    assert mutate_cross_org.status_code == 404


def test_planner_export_csv_and_xlsx(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, csrf, suffix="planner-export")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-itinerary-export", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": csrf},
        json={"day_number": 1, "title": "Export Day"},
    )
    day_id = day.json()["days"][0]["id"]

    stop = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": csrf},
        json={"attraction_id": attraction_a_id, "start_minute_of_day": 540, "duration_minutes": 90},
    )
    assert stop.status_code == 200

    export_csv = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]
    assert "day_number" in export_csv.text
    assert "attraction_id" in export_csv.text

    export_xlsx = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}/export?format=xlsx")
    assert export_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in export_xlsx.headers["content-type"]
    assert export_xlsx.content.startswith(b"PK")


def test_planner_import_csv_receipt_with_mixed_valid_invalid_rows(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, csrf, suffix="planner-import-csv")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-itinerary-import-csv", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    csv_payload = "\n".join(
        [
            "day_number,day_title,day_notes,day_urban_speed_mph_override,day_highway_speed_mph_override,stop_order,attraction_id,attraction_name,attraction_city,attraction_state,start_time,duration_minutes,stop_notes",
            f"1,Imported Day,,25,55,1,{attraction_a_id},Example,Austin,TX,09:00,90,Valid row",
            "1,Imported Day,,25,55,2,not-a-real-attraction,Example,Austin,TX,10:45,90,Invalid attraction",
        ]
    )

    import_response = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/import",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("planner-import.csv", csv_payload, "text/csv")},
    )
    assert import_response.status_code == 200
    receipt = import_response.json()
    assert receipt["applied"] is True
    assert receipt["accepted_row_count"] == 1
    assert receipt["rejected_row_count"] == 1
    assert receipt["accepted_rows"][0]["attraction_id"] == attraction_a_id
    assert "active catalog" in receipt["rejected_rows"][0]["errors"][0]
    assert receipt["rejected_rows"][0]["correction_hints"]

    itinerary_after = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}")
    assert itinerary_after.status_code == 200
    assert len(itinerary_after.json()["days"]) == 1
    assert len(itinerary_after.json()["days"][0]["stops"]) == 1
    assert itinerary_after.json()["days"][0]["stops"][0]["attraction_id"] == attraction_a_id

    versions = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}/versions")
    assert versions.status_code == 200
    assert "import applied" in versions.json()[0]["change_summary"].lower()


def test_planner_import_xlsx_receipt(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, csrf, suffix="planner-import-xlsx")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-itinerary-import-xlsx", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "day_number",
            "day_title",
            "day_notes",
            "day_urban_speed_mph_override",
            "day_highway_speed_mph_override",
            "stop_order",
            "attraction_id",
            "attraction_name",
            "attraction_city",
            "attraction_state",
            "start_time",
            "duration_minutes",
            "stop_notes",
        ]
    )
    sheet.append([1, "XLSX Day", "", 25, 55, 1, attraction_a_id, "Example", "Austin", "TX", "08:30", 120, "xlsx"])

    payload = io.BytesIO()
    workbook.save(payload)

    import_response = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/import",
        headers={"X-CSRF-Token": csrf},
        files={
            "file": (
                "planner-import.xlsx",
                payload.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert import_response.status_code == 200
    receipt = import_response.json()
    assert receipt["applied"] is True
    assert receipt["accepted_row_count"] == 1
    assert receipt["rejected_row_count"] == 0


def test_planner_import_requires_edit_permission_while_export_allows_read(client, test_user, planner_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])
    users = client.get("/api/admin/users")
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, admin_csrf, suffix="planner-import-guard")

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": admin_csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": False},
    )
    assert add_member.status_code == 201

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": admin_csrf},
        json={"name": "pytest-itinerary-import-guard", "status": "draft", "assigned_planner_user_id": planner_id},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    planner_csrf = login(client, planner_user)

    export_response = client.get(f"/api/projects/{project_id}/itineraries/{itinerary_id}/export?format=csv")
    assert export_response.status_code == 200

    csv_payload = "\n".join(
        [
            "day_number,day_title,day_notes,day_urban_speed_mph_override,day_highway_speed_mph_override,stop_order,attraction_id,attraction_name,attraction_city,attraction_state,start_time,duration_minutes,stop_notes",
            f"1,Guard Day,,25,55,1,{attraction_a_id},Example,Austin,TX,09:00,60,Guard",
        ]
    )

    import_response = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/import",
        headers={"X-CSRF-Token": planner_csrf},
        files={"file": ("guard.csv", csv_payload, "text/csv")},
    )
    assert import_response.status_code == 403


def test_sync_package_export_import_and_conflict_policy(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, csrf, suffix="sync-package")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-sync-itinerary", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": csrf},
        json={"day_number": 1, "title": "Day 1"},
    )
    assert day.status_code == 200
    day_id = day.json()["days"][0]["id"]

    stop = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": csrf},
        json={"attraction_id": attraction_a_id, "start_minute_of_day": 540, "duration_minutes": 90},
    )
    assert stop.status_code == 200

    export_response = client.get(f"/api/projects/{project_id}/sync-package/export")
    assert export_response.status_code == 200
    assert export_response.content.startswith(b"PK")

    import_ok = client.post(
        f"/api/projects/{project_id}/sync-package/import",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("planner-sync.zip", export_response.content, "application/zip")},
    )
    assert import_ok.status_code == 200
    receipt_ok = import_ok.json()
    assert receipt_ok["integrity_validated"] is True
    assert receipt_ok["updated_record_count"] == 1
    assert receipt_ok["conflict_count"] == 0

    mutate = client.patch(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}",
        headers={"X-CSRF-Token": csrf},
        json={"description": "destination changed"},
    )
    assert mutate.status_code == 200

    import_conflict = client.post(
        f"/api/projects/{project_id}/sync-package/import",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("planner-sync.zip", export_response.content, "application/zip")},
    )
    assert import_conflict.status_code == 200
    receipt_conflict = import_conflict.json()
    assert receipt_conflict["conflict_count"] == 1
    assert receipt_conflict["updated_record_count"] == 0
    assert receipt_conflict["record_results"][0]["action"] == "conflict"


def test_sync_package_import_integrity_checksum_validation(client, test_user):
    csrf = login(client, test_user)
    project_id, _, attraction_a_id, _ = create_project_dataset_catalog(client, csrf, suffix="sync-checksum")

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-sync-checksum", "status": "draft"},
    )
    itinerary_id = itinerary.json()["id"]

    day = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days",
        headers={"X-CSRF-Token": csrf},
        json={"day_number": 1},
    )
    day_id = day.json()["days"][0]["id"]
    client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops",
        headers={"X-CSRF-Token": csrf},
        json={"attraction_id": attraction_a_id, "start_minute_of_day": 500, "duration_minutes": 60},
    )

    export_response = client.get(f"/api/projects/{project_id}/sync-package/export")
    assert export_response.status_code == 200

    with zipfile.ZipFile(io.BytesIO(export_response.content), mode="r") as original:
        entries = {info.filename: original.read(info.filename) for info in original.infolist() if not info.is_dir()}

    data = json.loads(entries["data/itineraries.json"].decode("utf-8"))
    data["records"][0]["payload"]["name"] = "tampered-name"
    entries["data/itineraries.json"] = json.dumps(data).encode("utf-8")

    tampered_buffer = io.BytesIO()
    with zipfile.ZipFile(tampered_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as tampered:
        for path, payload in entries.items():
            tampered.writestr(path, payload)

    import_response = client.post(
        f"/api/projects/{project_id}/sync-package/import",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("tampered-sync.zip", tampered_buffer.getvalue(), "application/zip")},
    )
    assert import_response.status_code == 200
    receipt = import_response.json()
    assert receipt["integrity_validated"] is False
    assert any("Checksum mismatch" in message for message in receipt["file_errors"])


def test_sync_package_endpoints_support_api_token_auth(client, test_user):
    csrf = login(client, test_user)
    project_id, _, _, _ = create_project_dataset_catalog(client, csrf, suffix="sync-token")

    token_create = client.post(
        "/api/auth/tokens",
        headers={"X-CSRF-Token": csrf},
        json={"label": "sync-package-token", "expires_in_days": 3},
    )
    assert token_create.status_code == 201
    raw_token = token_create.json()["token"]

    export_response = client.get(
        f"/api/projects/{project_id}/sync-package/export",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert export_response.status_code == 200
    assert "application/zip" in export_response.headers["content-type"]

    import_response = client.post(
        f"/api/projects/{project_id}/sync-package/import",
        headers={"Authorization": f"Bearer {raw_token}"},
        files={"file": ("token-sync.zip", export_response.content, "application/zip")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["integrity_validated"] is True
