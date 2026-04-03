from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import auditor_session_dep, db_dep, org_admin_csrf_session_dep, require_recent_step_up
from app.models.auth import Session as AuthSession
from app.schemas.operations import (
    AuditEventOut,
    BackupRunOut,
    LineageEventOut,
    RestoreRequest,
    RestoreRunOut,
    RetentionPolicyOut,
    RetentionPolicyUpdateRequest,
    RetentionRunOut,
)
from app.services.audit import list_audit_events, record_audit_event
from app.services.lineage import list_lineage_events
from app.services.operations import (
    OperationsValidationError,
    get_or_create_retention_policy,
    list_backup_runs,
    list_restore_runs,
    list_retention_runs,
    run_encrypted_backup,
    run_itinerary_retention,
    run_restore_from_backup,
    update_retention_policy,
)

router = APIRouter(prefix="/ops", tags=["operations"])


def _retention_policy_out(row) -> RetentionPolicyOut:
    return RetentionPolicyOut(
        id=row.id,
        org_id=row.org_id,
        itinerary_retention_days=row.itinerary_retention_days,
        updated_by_user_id=row.updated_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _retention_run_out(row) -> RetentionRunOut:
    return RetentionRunOut(
        id=row.id,
        org_id=row.org_id,
        initiated_by_user_id=row.initiated_by_user_id,
        status=row.status,
        deleted_itinerary_count=row.deleted_itinerary_count,
        summary=row.summary,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def _backup_run_out(row) -> BackupRunOut:
    return BackupRunOut(
        id=row.id,
        org_id=row.org_id,
        initiated_by_user_id=row.initiated_by_user_id,
        trigger_kind=row.trigger_kind,
        status=row.status,
        backup_file_name=row.backup_file_name,
        backup_file_path=row.backup_file_path,
        encrypted_size_bytes=row.encrypted_size_bytes,
        rotated_file_count=row.rotated_file_count,
        summary=row.summary,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def _restore_run_out(row) -> RestoreRunOut:
    return RestoreRunOut(
        id=row.id,
        org_id=row.org_id,
        initiated_by_user_id=row.initiated_by_user_id,
        status=row.status,
        backup_file_name=row.backup_file_name,
        restored_table_count=row.restored_table_count,
        summary=row.summary,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def _audit_event_out(row) -> AuditEventOut:
    return AuditEventOut(
        id=row.id,
        org_id=row.org_id,
        project_id=row.project_id,
        actor_user_id=row.actor_user_id,
        action_type=row.action_type,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        request_method=row.request_method,
        request_path=row.request_path,
        status_code=row.status_code,
        detail_summary=row.detail_summary,
        metadata_json=row.metadata_json,
        occurred_at=row.occurred_at,
    )


def _lineage_event_out(row) -> LineageEventOut:
    return LineageEventOut(
        id=row.id,
        org_id=row.org_id,
        project_id=row.project_id,
        dataset_id=row.dataset_id,
        itinerary_id=row.itinerary_id,
        created_by_user_id=row.created_by_user_id,
        event_type=row.event_type,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        payload=row.payload,
        occurred_at=row.occurred_at,
    )


@router.get("/retention-policy", response_model=RetentionPolicyOut)
def retention_policy_get(
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> RetentionPolicyOut:
    row = get_or_create_retention_policy(db, org_id=auth_session.user.org_id, actor_user_id=auth_session.user_id)
    return _retention_policy_out(row)


@router.patch("/retention-policy", response_model=RetentionPolicyOut)
def retention_policy_update(
    payload: RetentionPolicyUpdateRequest,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> RetentionPolicyOut:
    row = update_retention_policy(
        db,
        org_id=auth_session.user.org_id,
        actor_user=auth_session.user,
        itinerary_retention_days=payload.itinerary_retention_days,
    )
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="operations.retention_policy_updated",
        resource_type="retention_policy",
        resource_id=row.id,
        request_method="PATCH",
        request_path="/api/ops/retention-policy",
        status_code=200,
        detail_summary="Updated itinerary retention policy",
        metadata_json={"itinerary_retention_days": row.itinerary_retention_days},
    )
    return _retention_policy_out(row)


@router.post("/retention/run", response_model=RetentionRunOut)
def retention_run(
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> RetentionRunOut:
    row = run_itinerary_retention(db, org_id=auth_session.user.org_id, actor_user_id=auth_session.user_id)
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="operations.retention_run",
        resource_type="retention_run",
        resource_id=row.id,
        request_method="POST",
        request_path="/api/ops/retention/run",
        status_code=200,
        detail_summary="Executed itinerary retention run",
        metadata_json={"deleted_itinerary_count": row.deleted_itinerary_count},
    )
    return _retention_run_out(row)


@router.get("/retention/runs", response_model=list[RetentionRunOut])
def retention_runs_list(
    limit: int = Query(default=30, ge=1, le=200),
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> list[RetentionRunOut]:
    return [_retention_run_out(row) for row in list_retention_runs(db, org_id=auth_session.user.org_id, limit=limit)]


@router.post("/backups/run", response_model=BackupRunOut)
def backups_run_manual(
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> BackupRunOut:
    try:
        row = run_encrypted_backup(
            db,
            org_id=auth_session.user.org_id,
            initiated_by_user_id=auth_session.user_id,
            trigger_kind="manual",
            enforce_one_per_day=False,
        )
    except OperationsValidationError as exc:
        record_audit_event(
            db,
            org_id=auth_session.user.org_id,
            actor_user_id=auth_session.user_id,
            action_type="operations.backup_run_failed",
            resource_type="backup_run",
            resource_id=None,
            request_method="POST",
            request_path="/api/ops/backups/run",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail_summary="Encrypted backup run failed",
            metadata_json={"error": str(exc)},
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="operations.backup_run",
        resource_type="backup_run",
        resource_id=row.id,
        request_method="POST",
        request_path="/api/ops/backups/run",
        status_code=200,
        detail_summary="Executed encrypted backup",
        metadata_json={
            "backup_file_name": row.backup_file_name,
            "encrypted_size_bytes": row.encrypted_size_bytes,
            "rotated_file_count": row.rotated_file_count,
        },
    )
    return _backup_run_out(row)


@router.get("/backups/runs", response_model=list[BackupRunOut])
def backups_runs_list(
    limit: int = Query(default=30, ge=1, le=200),
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> list[BackupRunOut]:
    return [_backup_run_out(row) for row in list_backup_runs(db, org_id=auth_session.user.org_id, limit=limit)]


@router.post("/restore", response_model=RestoreRunOut)
def restore_apply(
    payload: RestoreRequest,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> RestoreRunOut:
    try:
        row = run_restore_from_backup(
            db,
            org_id=auth_session.user.org_id,
            initiated_by_user_id=auth_session.user_id,
            backup_file_name=payload.backup_file_name,
        )
    except OperationsValidationError as exc:
        record_audit_event(
            db,
            org_id=auth_session.user.org_id,
            actor_user_id=auth_session.user_id,
            action_type="operations.restore_run_failed",
            resource_type="restore_run",
            resource_id=None,
            request_method="POST",
            request_path="/api/ops/restore",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail_summary="Restore from encrypted backup failed",
            metadata_json={"backup_file_name": payload.backup_file_name, "error": str(exc)},
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="operations.restore_run",
        resource_type="restore_run",
        resource_id=row.id,
        request_method="POST",
        request_path="/api/ops/restore",
        status_code=200,
        detail_summary="Executed restore from encrypted backup",
        metadata_json={"backup_file_name": row.backup_file_name, "restored_table_count": row.restored_table_count},
    )
    return _restore_run_out(row)


@router.get("/restore/runs", response_model=list[RestoreRunOut])
def restore_runs_list(
    limit: int = Query(default=30, ge=1, le=200),
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> list[RestoreRunOut]:
    return [_restore_run_out(row) for row in list_restore_runs(db, org_id=auth_session.user.org_id, limit=limit)]


@router.get("/audit/events", response_model=list[AuditEventOut])
def audit_events_list(
    limit: int = Query(default=100, ge=1, le=500),
    action_prefix: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> list[AuditEventOut]:
    rows = list_audit_events(
        db,
        org_id=auth_session.user.org_id,
        limit=limit,
        action_prefix=action_prefix,
        project_id=project_id,
    )
    return [_audit_event_out(row) for row in rows]


@router.get("/lineage/events", response_model=list[LineageEventOut])
def lineage_events_list(
    limit: int = Query(default=100, ge=1, le=500),
    project_id: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    itinerary_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    auth_session: AuthSession = Depends(auditor_session_dep),
    db: Session = Depends(db_dep),
) -> list[LineageEventOut]:
    rows = list_lineage_events(
        db,
        org_id=auth_session.user.org_id,
        limit=limit,
        project_id=project_id,
        dataset_id=dataset_id,
        itinerary_id=itinerary_id,
        event_type=event_type,
    )
    return [_lineage_event_out(row) for row in rows]
