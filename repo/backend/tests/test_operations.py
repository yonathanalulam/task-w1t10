from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy import text

from app.core.config import get_settings
from app.models.operations import BackupRun
from app.models.organization import Organization
from app.services.operations import run_nightly_backups_for_all_orgs


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


def create_project(client, csrf: str, *, suffix: str) -> str:
    response = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-ops-project-{suffix}",
            "code": f"POPS-{suffix}",
            "description": "ops",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_dataset(client, csrf: str, *, suffix: str) -> str:
    response = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-ops-dataset-{suffix}",
            "description": "ops",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def step_up(client, csrf: str, *, password: str) -> None:
    response = client.post("/api/auth/step-up", headers={"X-CSRF-Token": csrf}, json={"password": password})
    assert response.status_code == 200


def test_ops_retention_backup_restore_and_audit(client, test_user):
    csrf = login(client, test_user)

    policy_before = client.get("/api/ops/retention-policy")
    assert policy_before.status_code == 200
    assert policy_before.json()["itinerary_retention_days"] == 1095

    update_without_stepup = client.patch(
        "/api/ops/retention-policy",
        headers={"X-CSRF-Token": csrf},
        json={"itinerary_retention_days": 1200},
    )
    assert update_without_stepup.status_code == 403

    step_up(client, csrf, password=test_user["password"])

    update_policy = client.patch(
        "/api/ops/retention-policy",
        headers={"X-CSRF-Token": csrf},
        json={"itinerary_retention_days": 1200},
    )
    assert update_policy.status_code == 200
    assert update_policy.json()["itinerary_retention_days"] == 1200

    run_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": csrf})
    assert run_backup.status_code == 200
    backup_file_name = run_backup.json()["backup_file_name"]
    assert backup_file_name

    audits_after_backup = client.get("/api/ops/audit/events?limit=50")
    assert audits_after_backup.status_code == 200
    assert "operations.backup_run" in {row["action_type"] for row in audits_after_backup.json()}

    project_before_restore_id = create_project(client, csrf, suffix="backup-1")
    create_project(client, csrf, suffix="backup-2")

    run_restore = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf},
        json={"backup_file_name": backup_file_name},
    )
    assert run_restore.status_code == 200, run_restore.text
    assert run_restore.json()["status"] == "succeeded"

    projects = client.get("/api/projects")
    assert projects.status_code == 200
    project_ids = {row["id"] for row in projects.json()}
    assert project_before_restore_id not in project_ids

    audits = client.get("/api/ops/audit/events?limit=50")
    assert audits.status_code == 200
    action_types = {row["action_type"] for row in audits.json()}
    assert "operations.retention_policy_updated" in action_types
    assert "operations.restore_run" in action_types


def test_ops_restore_requires_step_up(client, test_user):
    csrf = login(client, test_user)

    run_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": csrf})
    assert run_backup.status_code == 200
    backup_file_name = run_backup.json()["backup_file_name"]
    assert backup_file_name

    restore_without_step_up = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf},
        json={"backup_file_name": backup_file_name},
    )
    assert restore_without_step_up.status_code == 403
    assert "Step-up authentication required" in restore_without_step_up.json()["detail"]


def test_ops_restore_failure_records_for_wrong_key_and_corrupt_payload(client, test_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    settings = get_settings()
    backup_root = Path(settings.backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    wrong_key_file = backup_root / "pytest-wrong-key.tfbak"
    corrupt_payload_file = backup_root / "pytest-corrupt-payload.tfbak"

    payload = {
        "format_version": "trailforge-backup-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "tables": [],
    }

    wrong_cipher = Fernet(Fernet.generate_key())
    wrong_key_file.write_bytes(wrong_cipher.encrypt(gzip.compress(json.dumps(payload).encode("utf-8"))))

    current_key = Path(settings.backup_encryption_key_path).read_bytes().strip()
    current_cipher = Fernet(current_key)
    corrupt_payload_file.write_bytes(current_cipher.encrypt(b"not-a-gzip-payload"))

    wrong_key_restore = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf},
        json={"backup_file_name": wrong_key_file.name},
    )
    assert wrong_key_restore.status_code == 422
    assert "could not be decrypted" in wrong_key_restore.json()["detail"]

    corrupt_payload_restore = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf},
        json={"backup_file_name": corrupt_payload_file.name},
    )
    assert corrupt_payload_restore.status_code == 422
    assert "invalid or corrupted" in corrupt_payload_restore.json()["detail"]

    restore_runs = client.get("/api/ops/restore/runs?limit=20")
    assert restore_runs.status_code == 200
    rows = restore_runs.json()
    wrong_key_row = next((row for row in rows if row["backup_file_name"] == wrong_key_file.name), None)
    corrupt_payload_row = next((row for row in rows if row["backup_file_name"] == corrupt_payload_file.name), None)
    assert wrong_key_row
    assert wrong_key_row["status"] == "failed"
    assert "could not be decrypted" in (wrong_key_row["summary"] or "")
    assert corrupt_payload_row
    assert corrupt_payload_row["status"] == "failed"
    assert "invalid or corrupted" in (corrupt_payload_row["summary"] or "")


def test_ops_backup_rotation_deletes_old_files(client, test_user):
    csrf = login(client, test_user)
    settings = get_settings()
    backup_root = Path(settings.backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    stale_file = backup_root / "pytest-stale-backup.tfbak"
    stale_file.write_bytes(b"stale")
    stale_time = (datetime.now(UTC) - timedelta(days=settings.backup_rotation_days + 10)).timestamp()
    os.utime(stale_file, (stale_time, stale_time))

    run_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": csrf})
    assert run_backup.status_code == 200
    assert run_backup.json()["rotated_file_count"] >= 1
    assert not stale_file.exists()


def test_nightly_backup_cycle_covers_all_orgs_and_deduplicates(db, other_org_admin):
    del other_org_admin  # fixture ensures second org exists

    org_count = db.execute(select(func.count()).select_from(Organization)).scalar_one()
    created_first = run_nightly_backups_for_all_orgs(db)
    assert created_first == org_count

    created_second = run_nightly_backups_for_all_orgs(db)
    assert created_second == 0

    nightly_success_count = db.execute(
        select(func.count())
        .select_from(BackupRun)
        .where(BackupRun.trigger_kind == "nightly", BackupRun.status == "succeeded")
    ).scalar_one()
    assert nightly_success_count == org_count


def test_ops_lineage_visibility_and_immutable_tables(client, db, test_user):
    csrf = login(client, test_user)
    step_up(client, csrf, password=test_user["password"])

    dataset = client.post(
        "/api/datasets",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-ops-lineage-dataset", "description": "lineage", "status": "active"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["id"]

    attraction_a = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-ops-lineage-spot",
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
    source_id = attraction_a.json()["id"]

    attraction_b = client.post(
        f"/api/datasets/{dataset_id}/attractions",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-ops-lineage-spot",
            "city": "Austin",
            "state": "TX",
            "description": "B",
            "latitude": 30.268,
            "longitude": -97.744,
            "duration_minutes": 120,
            "status": "active",
        },
    )
    assert attraction_b.status_code == 201
    target_id = attraction_b.json()["id"]

    merge = client.post(
        f"/api/datasets/{dataset_id}/attractions/merge",
        headers={"X-CSRF-Token": csrf},
        json={"source_attraction_id": source_id, "target_attraction_id": target_id, "merge_reason": "pytest lineage"},
    )
    assert merge.status_code == 200

    project_id = create_project(client, csrf, suffix="lineage")
    link = client.post(f"/api/projects/{project_id}/datasets/{dataset_id}", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 201

    itinerary = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": "pytest-ops-lineage-itinerary", "status": "draft"},
    )
    assert itinerary.status_code == 201
    itinerary_id = itinerary.json()["id"]

    import_csv = "\n".join(
        [
            "day_number,day_title,day_notes,day_urban_speed_mph_override,day_highway_speed_mph_override,stop_order,attraction_id,attraction_name,attraction_city,attraction_state,start_time,duration_minutes,stop_notes",
            f"1,Lineage Day,,25,55,1,{target_id},Example,Austin,TX,09:00,60,lineage import",
        ]
    )
    imported = client.post(
        f"/api/projects/{project_id}/itineraries/{itinerary_id}/import",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("lineage.csv", import_csv, "text/csv")},
    )
    assert imported.status_code == 200

    sync_export = client.get(f"/api/projects/{project_id}/sync-package/export")
    assert sync_export.status_code == 200

    lineage_rows = client.get("/api/ops/lineage/events?limit=100")
    assert lineage_rows.status_code == 200
    event_types = {row["event_type"] for row in lineage_rows.json()}
    assert "governance.attraction_merge" in event_types
    assert "planner.itinerary_import" in event_types
    assert "planner.sync_package_export" in event_types

    audit_rows = client.get("/api/ops/audit/events?limit=100")
    assert audit_rows.status_code == 200
    assert audit_rows.json()
    audit_id = audit_rows.json()[0]["id"]

    with pytest.raises(Exception):
        db.execute(text("UPDATE audit_events SET action_type = 'tampered' WHERE id = :event_id"), {"event_id": audit_id})
        db.commit()
    db.rollback()

    assert lineage_rows.json()
    lineage_id = lineage_rows.json()[0]["id"]
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM lineage_events WHERE id = :event_id"), {"event_id": lineage_id})
        db.commit()
    db.rollback()


def test_auditor_can_read_ops_history_but_cannot_mutate(client, test_user, auditor_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])

    backup_run = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": admin_csrf})
    assert backup_run.status_code == 200

    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": admin_csrf})
    assert logout.status_code == 204

    auditor_csrf = login(client, auditor_user)

    retention_policy = client.get("/api/ops/retention-policy")
    assert retention_policy.status_code == 200

    backup_runs = client.get("/api/ops/backups/runs?limit=10")
    assert backup_runs.status_code == 200

    restore_runs = client.get("/api/ops/restore/runs?limit=10")
    assert restore_runs.status_code == 200

    audit_events = client.get("/api/ops/audit/events?limit=10")
    assert audit_events.status_code == 200

    lineage_events = client.get("/api/ops/lineage/events?limit=10")
    assert lineage_events.status_code == 200

    denied_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": auditor_csrf})
    assert denied_backup.status_code == 403


def test_non_auditor_non_admin_cannot_read_ops_history(client, planner_user):
    planner_csrf = login(client, planner_user)

    audit_events = client.get("/api/ops/audit/events?limit=10")
    assert audit_events.status_code == 403

    lineage_events = client.get("/api/ops/lineage/events?limit=10")
    assert lineage_events.status_code == 403

    retention_policy = client.get("/api/ops/retention-policy")
    assert retention_policy.status_code == 403

    denied_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": planner_csrf})
    assert denied_backup.status_code == 403


def test_backup_restore_remains_tenant_scoped(client, test_user, other_org_admin):
    csrf_a = login(client, test_user)
    dataset_a_before = create_dataset(client, csrf_a, suffix="org-a-before")

    run_backup = client.post("/api/ops/backups/run", headers={"X-CSRF-Token": csrf_a})
    assert run_backup.status_code == 200
    backup_file_name = run_backup.json()["backup_file_name"]
    assert backup_file_name

    dataset_a_after = create_dataset(client, csrf_a, suffix="org-a-after")

    logout_a = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a})
    assert logout_a.status_code == 204

    csrf_b = login(client, other_org_admin)
    step_up(client, csrf_b, password=other_org_admin["password"])
    dataset_b = create_dataset(client, csrf_b, suffix="org-b")

    cross_org_restore = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf_b},
        json={"backup_file_name": backup_file_name},
    )
    assert cross_org_restore.status_code == 422
    assert "scope does not match target organization" in cross_org_restore.json()["detail"]

    org_b_datasets = client.get("/api/datasets")
    assert org_b_datasets.status_code == 200
    org_b_dataset_ids = {row["id"] for row in org_b_datasets.json()}
    assert dataset_b in org_b_dataset_ids

    logout_b = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_b})
    assert logout_b.status_code == 204

    csrf_a_restore = login(client, test_user)
    step_up(client, csrf_a_restore, password=test_user["password"])
    restore_org_a = client.post(
        "/api/ops/restore",
        headers={"X-CSRF-Token": csrf_a_restore},
        json={"backup_file_name": backup_file_name},
    )
    assert restore_org_a.status_code == 200, restore_org_a.text

    org_a_datasets = client.get("/api/datasets")
    assert org_a_datasets.status_code == 200
    org_a_dataset_ids = {row["id"] for row in org_a_datasets.json()}
    assert dataset_a_before in org_a_dataset_ids
    assert dataset_a_after not in org_a_dataset_ids

    logout_a_restore = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_a_restore})
    assert logout_a_restore.status_code == 204

    csrf_b_verify = login(client, other_org_admin)
    org_b_datasets_after = client.get("/api/datasets")
    assert org_b_datasets_after.status_code == 200
    org_b_dataset_ids_after = {row["id"] for row in org_b_datasets_after.json()}
    assert dataset_b in org_b_dataset_ids_after
