from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utcnow
from app.models.operations import AuditEvent

SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "csrf",
    "csrf_token",
    "api_key",
    "secret",
    "backup_key",
    "encryption_key",
}


def _redact(value):
    if isinstance(value, Mapping):
        redacted = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def record_audit_event(
    db: Session,
    *,
    org_id: str,
    actor_user_id: str | None,
    action_type: str,
    resource_type: str,
    resource_id: str | None,
    request_method: str,
    request_path: str,
    status_code: int,
    project_id: str | None = None,
    detail_summary: str | None = None,
    metadata_json: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        org_id=org_id,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        request_method=request_method,
        request_path=request_path,
        status_code=status_code,
        detail_summary=detail_summary,
        metadata_json=_redact(metadata_json) if metadata_json else None,
        occurred_at=utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit_events(
    db: Session,
    *,
    org_id: str,
    limit: int,
    action_prefix: str | None,
    project_id: str | None,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(AuditEvent.org_id == org_id)
    if action_prefix:
        query = query.where(AuditEvent.action_type.like(f"{action_prefix}%"))
    if project_id:
        query = query.where(AuditEvent.project_id == project_id)

    clamped_limit = max(1, min(limit, 500))
    return list(db.execute(query.order_by(AuditEvent.occurred_at.desc()).limit(clamped_limit)).scalars().all())
