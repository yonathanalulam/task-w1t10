from __future__ import annotations

import base64
import gzip
import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import DateTime, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import utcnow
from app.models.base import Base
from app.models.governance import Project
from app.models.organization import Organization
from app.models.operations import AuditEvent, BackupRun, LineageEvent, RestoreRun, RetentionPolicy, RetentionRun
from app.models.planner import Itinerary, ItineraryDay
from app.models.rbac import Role
from app.models.user import User
from app.services.resource_center import mark_orphaned_assets_cleanup_eligible, run_cleanup_eligible_assets

BACKUP_FORMAT_VERSION = "trailforge-org-backup-v2"
IMMUTABLE_EVENT_TABLES = ("audit_events", "lineage_events")
ORG_BACKUP_EXCLUDED_TABLES = {
    "organizations",
    "permissions",
    "sessions",
    "api_tokens",
}


class OperationsValidationError(Exception):
    """Raised when an operator operation payload is invalid."""


def _backup_root() -> Path:
    root = Path(get_settings().backup_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_backup_cipher() -> Fernet:
    key_path = Path(get_settings().backup_encryption_key_path).expanduser()
    if not key_path.exists():
        raise OperationsValidationError(f"Backup key file is missing: {key_path}")
    mode = key_path.stat().st_mode & 0o777
    if mode & 0o077:
        raise OperationsValidationError(
            "Backup key file permissions are too open; require owner-only access (for example 0600)"
        )
    key = key_path.read_bytes().strip()
    if not key:
        raise OperationsValidationError("Backup key file is empty")
    try:
        return Fernet(key)
    except Exception as exc:  # pragma: no cover - defensive branch
        raise OperationsValidationError("Backup key is invalid for Fernet encryption") from exc


def _serialize_value(value):
    if isinstance(value, datetime):
        return {"__kind": "datetime", "value": value.astimezone(UTC).isoformat()}
    if isinstance(value, bytes):
        return {"__kind": "bytes", "value": base64.b64encode(value).decode("utf-8")}
    return value


def _deserialize_value(value, *, column_type):
    if isinstance(value, dict) and value.get("__kind") == "datetime":
        return datetime.fromisoformat(value["value"])
    if isinstance(value, dict) and value.get("__kind") == "bytes":
        return base64.b64decode(value["value"])
    if isinstance(column_type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _drop_sqlite_immutable_triggers(db: Session) -> None:
    db.execute(text("DROP TRIGGER IF EXISTS trg_audit_events_immutable_update"))
    db.execute(text("DROP TRIGGER IF EXISTS trg_audit_events_immutable_delete"))
    db.execute(text("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_update"))
    db.execute(text("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_delete"))


def _create_sqlite_immutable_triggers(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TRIGGER trg_audit_events_immutable_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table audit_events cannot be UPDATE');
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER trg_audit_events_immutable_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table audit_events cannot be DELETE');
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER trg_lineage_events_immutable_update
            BEFORE UPDATE ON lineage_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be UPDATE');
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER trg_lineage_events_immutable_delete
            BEFORE DELETE ON lineage_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be DELETE');
            END;
            """
        )
    )


def _set_postgresql_immutable_triggers_enabled(db: Session, *, table_names: tuple[str, ...], enabled: bool) -> None:
    action = "ENABLE" if enabled else "DISABLE"
    # USER avoids superuser-only internal trigger toggles while still suspending the immutable user triggers.
    for table_name in table_names:
        db.execute(text(f'ALTER TABLE "{table_name}" {action} TRIGGER USER'))


def _immutable_event_tables(table_names: list[str] | tuple[str, ...] | set[str]) -> tuple[str, ...]:
    table_name_set = set(table_names)
    return tuple(name for name in IMMUTABLE_EVENT_TABLES if name in table_name_set)


@contextmanager
def _suspend_immutable_event_guards(db: Session, *, table_names: list[str] | tuple[str, ...] | set[str]) -> Iterator[None]:
    immutable_table_names = _immutable_event_tables(table_names)
    if not immutable_table_names:
        yield
        return

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name == "sqlite":
        _drop_sqlite_immutable_triggers(db)
    elif dialect_name == "postgresql":
        _set_postgresql_immutable_triggers_enabled(db, table_names=immutable_table_names, enabled=False)

    try:
        yield
    finally:
        if dialect_name == "sqlite":
            _create_sqlite_immutable_triggers(db)
        elif dialect_name == "postgresql":
            _set_postgresql_immutable_triggers_enabled(db, table_names=immutable_table_names, enabled=True)


def _org_scope_filter_expression(table, *, org_id: str):
    if table.name in ORG_BACKUP_EXCLUDED_TABLES:
        raise OperationsValidationError(f"Table {table.name} is not org-scoped and cannot be included in org backup")

    if "org_id" in table.c:
        return table.c.org_id == org_id

    org_project_ids = select(Project.id).where(Project.org_id == org_id)
    org_user_ids = select(User.id).where(User.org_id == org_id)
    org_role_ids = select(Role.id).where(Role.org_id == org_id)
    org_itinerary_ids = select(Itinerary.id).where(Itinerary.org_id == org_id)
    org_itinerary_day_ids = (
        select(ItineraryDay.id)
        .join(Itinerary, ItineraryDay.itinerary_id == Itinerary.id)
        .where(Itinerary.org_id == org_id)
    )

    if table.name == "project_datasets":
        return table.c.project_id.in_(org_project_ids)
    if table.name == "project_members":
        return table.c.project_id.in_(org_project_ids)
    if table.name == "sessions":
        return table.c.user_id.in_(org_user_ids)
    if table.name == "user_roles":
        return table.c.user_id.in_(org_user_ids)
    if table.name == "role_permissions":
        return table.c.role_id.in_(org_role_ids)
    if table.name == "itinerary_days":
        return table.c.itinerary_id.in_(org_itinerary_ids)
    if table.name == "itinerary_stops":
        return table.c.itinerary_day_id.in_(org_itinerary_day_ids)

    raise OperationsValidationError(
        f"Table {table.name} has no supported org scope filter for tenant-safe backup/restore"
    )


def _normalized_row_for_compare(table, row: dict) -> dict:
    return {column.name: _serialize_value(row.get(column.name)) for column in table.columns}


def _restore_immutable_rows(db: Session, *, table, rows: list[dict], org_scope_filter) -> None:
    if not rows:
        return
    if "id" not in table.c:
        raise OperationsValidationError(f"Immutable table {table.name} must expose an id column for restore")

    requested_ids = [row["id"] for row in rows if row.get("id") is not None]
    existing_rows_by_id = {
        row["id"]: dict(row)
        for row in db.execute(select(table).where(org_scope_filter, table.c.id.in_(requested_ids))).mappings().all()
    }

    rows_to_insert = []
    for row in rows:
        row_id = row.get("id")
        existing = existing_rows_by_id.get(row_id)
        if existing is None:
            rows_to_insert.append(row)
            continue
        if _normalized_row_for_compare(table, existing) != _normalized_row_for_compare(table, row):
            raise OperationsValidationError(
                f"Immutable table {table.name} contains conflicting history for row id {row_id}"
            )

    if rows_to_insert:
        db.execute(table.insert(), rows_to_insert)


def _serialize_database_snapshot(db: Session, *, org_id: str) -> dict:
    table_payload = []
    for table in Base.metadata.sorted_tables:
        if table.name in ORG_BACKUP_EXCLUDED_TABLES:
            continue

        org_scope_filter = _org_scope_filter_expression(table, org_id=org_id)
        rows = [
            dict(row)
            for row in db.execute(
                select(table).where(org_scope_filter).execution_options(populate_existing=True)
            )
            .mappings()
            .all()
        ]
        serialized_rows = []
        for row in rows:
            serialized_rows.append({key: _serialize_value(value) for key, value in row.items()})

        table_payload.append(
            {
                "table_name": table.name,
                "columns": [column.name for column in table.columns],
                "rows": serialized_rows,
            }
        )

    return {
        "format_version": BACKUP_FORMAT_VERSION,
        "scope": {"kind": "organization", "org_id": org_id},
        "created_at": utcnow().astimezone(UTC).isoformat(),
        "tables": table_payload,
    }


def _restore_database_snapshot(db: Session, *, payload: dict, org_id: str) -> int:
    if payload.get("format_version") != BACKUP_FORMAT_VERSION:
        raise OperationsValidationError("Unsupported backup format version")

    scope = payload.get("scope") or {}
    if scope.get("kind") != "organization" or scope.get("org_id") != org_id:
        raise OperationsValidationError("Backup scope does not match target organization")

    table_map = {
        table.name: table
        for table in Base.metadata.sorted_tables
        if table.name not in ORG_BACKUP_EXCLUDED_TABLES
    }
    requested_tables = [row["table_name"] for row in payload.get("tables", [])]
    forbidden_tables = [name for name in requested_tables if name in ORG_BACKUP_EXCLUDED_TABLES]
    if forbidden_tables:
        raise OperationsValidationError(f"Backup includes forbidden non-org tables: {', '.join(forbidden_tables)}")

    missing_tables = [name for name in requested_tables if name not in table_map]
    if missing_tables:
        raise OperationsValidationError(f"Backup references unknown tables: {', '.join(missing_tables)}")

    scoped_filters = {name: _org_scope_filter_expression(table_map[name], org_id=org_id) for name in requested_tables}
    immutable_tables = set(_immutable_event_tables(requested_tables))
    mutable_tables = [name for name in requested_tables if name not in immutable_tables]

    for table_name in reversed(mutable_tables):
        db.execute(table_map[table_name].delete().where(scoped_filters[table_name]))

    restored_table_count = 0
    for table_blob in payload.get("tables", []):
        table_name = table_blob["table_name"]
        table = table_map[table_name]
        rows = table_blob.get("rows", [])
        if not rows:
            restored_table_count += 1
            continue

        decoded_rows = []
        for row in rows:
            decoded_row = {}
            for column in table.columns:
                decoded_row[column.name] = _deserialize_value(row.get(column.name), column_type=column.type)
            decoded_rows.append(decoded_row)

        if table_name in immutable_tables:
            _restore_immutable_rows(db, table=table, rows=decoded_rows, org_scope_filter=scoped_filters[table_name])
        else:
            db.execute(table.insert(), decoded_rows)
        restored_table_count += 1
    return restored_table_count


def _rotation_cutoff(now: datetime) -> datetime:
    return now - timedelta(days=get_settings().backup_rotation_days)


def _error_summary(exc: Exception | str) -> str:
    if isinstance(exc, Exception):
        raw = str(exc).strip() or exc.__class__.__name__
    else:
        raw = str(exc).strip()
    if not raw:
        raw = "unknown failure"
    return raw[:2000]


def _rotate_backup_files(root: Path, *, now: datetime) -> int:
    cutoff = _rotation_cutoff(now)
    rotated = 0
    for path in root.glob("*.tfbak"):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        if mtime >= cutoff:
            continue
        path.unlink(missing_ok=True)
        rotated += 1
    return rotated


def run_encrypted_backup(
    db: Session,
    *,
    org_id: str,
    initiated_by_user_id: str | None,
    trigger_kind: str,
    enforce_one_per_day: bool,
) -> BackupRun:
    now = utcnow()
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    if enforce_one_per_day:
        existing = (
            db.execute(
                select(BackupRun).where(
                    BackupRun.org_id == org_id,
                    BackupRun.trigger_kind == "nightly",
                    BackupRun.status == "succeeded",
                    BackupRun.started_at >= day_start,
                    BackupRun.started_at < day_end,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            return existing

    file_path: Path | None = None
    try:
        root = _backup_root()
        snapshot = _serialize_database_snapshot(db, org_id=org_id)
        serialized = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
        compressed = gzip.compress(serialized)

        cipher = _load_backup_cipher()
        encrypted = cipher.encrypt(compressed)

        timestamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        file_name = f"trailforge-{org_id[:8]}-{timestamp}.tfbak"
        file_path = root / file_name
        file_path.write_bytes(encrypted)
        file_path.chmod(0o600)

        rotated_count = _rotate_backup_files(root, now=now)

        digest = hashlib.sha256(encrypted).hexdigest()
        run = BackupRun(
            org_id=org_id,
            initiated_by_user_id=initiated_by_user_id,
            trigger_kind=trigger_kind,
            status="succeeded",
            backup_file_name=file_name,
            backup_file_path=str(file_path),
            encrypted_size_bytes=len(encrypted),
            rotated_file_count=rotated_count,
            summary=f"Encrypted backup created; sha256={digest[:12]}...",
            started_at=now,
            completed_at=utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)

        failed_run = BackupRun(
            org_id=org_id,
            initiated_by_user_id=initiated_by_user_id,
            trigger_kind=trigger_kind,
            status="failed",
            backup_file_name=file_path.name if file_path else None,
            backup_file_path=str(file_path) if file_path else None,
            encrypted_size_bytes=None,
            rotated_file_count=0,
            summary=_error_summary(exc),
            started_at=now,
            completed_at=utcnow(),
        )
        db.add(failed_run)
        db.commit()
        db.refresh(failed_run)

        if isinstance(exc, OperationsValidationError):
            raise
        raise OperationsValidationError(_error_summary(exc)) from exc


def list_backup_runs(db: Session, *, org_id: str, limit: int) -> list[BackupRun]:
    clamped_limit = max(1, min(limit, 200))
    return list(
        db.execute(
            select(BackupRun).where(BackupRun.org_id == org_id).order_by(BackupRun.started_at.desc()).limit(clamped_limit)
        )
        .scalars()
        .all()
    )


def run_nightly_backups_for_all_orgs(db: Session) -> int:
    now = utcnow()
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    org_ids = list(db.execute(select(Organization.id).order_by(Organization.created_at.asc())).scalars().all())
    created_count = 0
    for org_id in org_ids:
        already_exists = (
            db.execute(
                select(BackupRun.id).where(
                    BackupRun.org_id == org_id,
                    BackupRun.trigger_kind == "nightly",
                    BackupRun.status == "succeeded",
                    BackupRun.started_at >= day_start,
                    BackupRun.started_at < day_end,
                )
            )
            .scalars()
            .first()
        )
        if already_exists:
            continue

        run_encrypted_backup(
            db,
            org_id=org_id,
            initiated_by_user_id=None,
            trigger_kind="nightly",
            enforce_one_per_day=True,
        )
        created_count += 1

    return created_count


def run_restore_from_backup(
    db: Session,
    *,
    org_id: str,
    initiated_by_user_id: str,
    backup_file_name: str,
) -> RestoreRun:
    if "/" in backup_file_name or ".." in backup_file_name:
        raise OperationsValidationError("Invalid backup file name")

    started_at = utcnow()

    def _record_failed_run(summary: str) -> None:
        db.rollback()
        row = RestoreRun(
            org_id=org_id,
            initiated_by_user_id=initiated_by_user_id,
            status="failed",
            backup_file_name=backup_file_name,
            restored_table_count=0,
            summary=_error_summary(summary),
            started_at=started_at,
            completed_at=utcnow(),
        )
        db.add(row)
        db.commit()

    root = _backup_root()
    backup_path = (root / backup_file_name).resolve()
    if root not in backup_path.parents:
        summary = "Backup path escapes designated backup folder"
        _record_failed_run(summary)
        raise OperationsValidationError(summary)
    if not backup_path.exists():
        summary = "Backup file was not found"
        _record_failed_run(summary)
        raise OperationsValidationError(summary)

    encrypted = backup_path.read_bytes()
    cipher = _load_backup_cipher()
    try:
        compressed = cipher.decrypt(encrypted)
    except InvalidToken as exc:
        summary = "Backup file could not be decrypted with current key"
        _record_failed_run(summary)
        raise OperationsValidationError(summary) from exc

    try:
        payload = json.loads(gzip.decompress(compressed).decode("utf-8"))
    except Exception as exc:
        summary = "Backup payload is invalid or corrupted"
        _record_failed_run(summary)
        raise OperationsValidationError(summary) from exc

    try:
        restored_table_count = _restore_database_snapshot(db, payload=payload, org_id=org_id)
        run = RestoreRun(
            org_id=org_id,
            initiated_by_user_id=initiated_by_user_id,
            status="succeeded",
            backup_file_name=backup_file_name,
            restored_table_count=restored_table_count,
            summary="Restore applied successfully",
            started_at=started_at,
            completed_at=utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        summary = _error_summary(exc)
        _record_failed_run(summary)
        raise OperationsValidationError(summary) from exc


def list_restore_runs(db: Session, *, org_id: str, limit: int) -> list[RestoreRun]:
    clamped_limit = max(1, min(limit, 200))
    return list(
        db.execute(
            select(RestoreRun).where(RestoreRun.org_id == org_id).order_by(RestoreRun.started_at.desc()).limit(clamped_limit)
        )
        .scalars()
        .all()
    )


def get_or_create_retention_policy(db: Session, *, org_id: str, actor_user_id: str | None) -> RetentionPolicy:
    settings = get_settings()
    policy = db.execute(select(RetentionPolicy).where(RetentionPolicy.org_id == org_id)).scalars().first()
    if policy:
        updated = False
        if policy.audit_retention_days != settings.audit_retention_days:
            policy.audit_retention_days = settings.audit_retention_days
            updated = True
        if policy.lineage_retention_days != settings.lineage_retention_days:
            policy.lineage_retention_days = settings.lineage_retention_days
            updated = True
        if updated:
            if actor_user_id is not None:
                policy.updated_by_user_id = actor_user_id
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    policy = RetentionPolicy(
        org_id=org_id,
        itinerary_retention_days=settings.itinerary_retention_default_days,
        audit_retention_days=settings.audit_retention_days,
        lineage_retention_days=settings.lineage_retention_days,
        updated_by_user_id=actor_user_id,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_retention_policy(
    db: Session,
    *,
    org_id: str,
    actor_user: User,
    itinerary_retention_days: int,
) -> RetentionPolicy:
    settings = get_settings()
    policy = get_or_create_retention_policy(db, org_id=org_id, actor_user_id=actor_user.id)
    policy.itinerary_retention_days = itinerary_retention_days
    policy.audit_retention_days = settings.audit_retention_days
    policy.lineage_retention_days = settings.lineage_retention_days
    policy.updated_by_user_id = actor_user.id
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def run_itinerary_retention(db: Session, *, org_id: str, actor_user_id: str | None) -> RetentionRun:
    started_at = utcnow()
    try:
        policy = get_or_create_retention_policy(db, org_id=org_id, actor_user_id=actor_user_id)
        itinerary_cutoff = started_at - timedelta(days=policy.itinerary_retention_days)
        audit_cutoff = started_at - timedelta(days=policy.audit_retention_days)
        lineage_cutoff = started_at - timedelta(days=policy.lineage_retention_days)

        stale_ids = list(
            db.execute(
                select(Itinerary.id).where(
                    Itinerary.org_id == org_id,
                    Itinerary.status == "archived",
                    Itinerary.updated_at < itinerary_cutoff,
                )
            )
            .scalars()
            .all()
        )

        deleted_count = 0
        if stale_ids:
            db.execute(
                Itinerary.__table__.delete().where(
                    Itinerary.id.in_(stale_ids),
                )
            )
            deleted_count = len(stale_ids)

        with _suspend_immutable_event_guards(db, table_names=IMMUTABLE_EVENT_TABLES):
            deleted_audit_event_count = int(
                db.execute(
                    AuditEvent.__table__.delete().where(
                        AuditEvent.org_id == org_id,
                        AuditEvent.occurred_at < audit_cutoff,
                    )
                ).rowcount
                or 0
            )
            deleted_lineage_event_count = int(
                db.execute(
                    LineageEvent.__table__.delete().where(
                        LineageEvent.org_id == org_id,
                        LineageEvent.occurred_at < lineage_cutoff,
                    )
                ).rowcount
                or 0
            )

        run = RetentionRun(
            org_id=org_id,
            initiated_by_user_id=actor_user_id,
            status="succeeded",
            deleted_itinerary_count=deleted_count,
            deleted_audit_event_count=deleted_audit_event_count,
            deleted_lineage_event_count=deleted_lineage_event_count,
            summary=(
                "Applied retention policy "
                f"itinerary={policy.itinerary_retention_days}d"
                f" audit={policy.audit_retention_days}d"
                f" lineage={policy.lineage_retention_days}d;"
                f" itinerary_cutoff={itinerary_cutoff.astimezone(UTC).isoformat()}"
                f" audit_cutoff={audit_cutoff.astimezone(UTC).isoformat()}"
                f" lineage_cutoff={lineage_cutoff.astimezone(UTC).isoformat()}"
            ),
            started_at=started_at,
            completed_at=utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = RetentionRun(
            org_id=org_id,
            initiated_by_user_id=actor_user_id,
            status="failed",
            deleted_itinerary_count=0,
            deleted_audit_event_count=0,
            deleted_lineage_event_count=0,
            summary=_error_summary(exc),
            started_at=started_at,
            completed_at=utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        raise


def run_retention_for_all_orgs(db: Session) -> int:
    now = utcnow()
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    org_ids = list(db.execute(select(Organization.id).order_by(Organization.created_at.asc())).scalars().all())
    created_count = 0
    for org_id in org_ids:
        already_exists = (
            db.execute(
                select(RetentionRun.id).where(
                    RetentionRun.org_id == org_id,
                    RetentionRun.status == "succeeded",
                    RetentionRun.started_at >= day_start,
                    RetentionRun.started_at < day_end,
                )
            )
            .scalars()
            .first()
        )
        if already_exists:
            continue

        run_itinerary_retention(db, org_id=org_id, actor_user_id=None)
        created_count += 1

    return created_count


def run_asset_cleanup_cycle(db: Session, *, max_delete: int | None = None) -> tuple[int, int]:
    marked_orphaned_asset_count = mark_orphaned_assets_cleanup_eligible(db)
    deleted_asset_count = run_cleanup_eligible_assets(db, max_delete=max_delete)
    return marked_orphaned_asset_count, deleted_asset_count


def list_retention_runs(db: Session, *, org_id: str, limit: int) -> list[RetentionRun]:
    clamped_limit = max(1, min(limit, 200))
    return list(
        db.execute(
            select(RetentionRun)
            .where(RetentionRun.org_id == org_id)
            .order_by(RetentionRun.started_at.desc())
            .limit(clamped_limit)
        )
        .scalars()
        .all()
    )
