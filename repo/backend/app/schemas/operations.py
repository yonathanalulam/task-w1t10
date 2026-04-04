from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventOut(BaseModel):
    id: str
    org_id: str
    project_id: str | None
    actor_user_id: str | None
    action_type: str
    resource_type: str
    resource_id: str | None
    request_method: str
    request_path: str
    status_code: int
    detail_summary: str | None
    metadata_json: dict | None
    occurred_at: datetime


class LineageEventOut(BaseModel):
    id: str
    org_id: str
    project_id: str | None
    dataset_id: str | None
    itinerary_id: str | None
    created_by_user_id: str | None
    event_type: str
    entity_type: str
    entity_id: str | None
    payload: dict
    occurred_at: datetime


class RetentionPolicyOut(BaseModel):
    id: str
    org_id: str
    itinerary_retention_days: int
    audit_retention_days: int
    lineage_retention_days: int
    updated_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


class RetentionPolicyUpdateRequest(BaseModel):
    itinerary_retention_days: int = Field(ge=30, le=3650)


class RetentionRunOut(BaseModel):
    id: str
    org_id: str
    initiated_by_user_id: str | None
    status: str
    deleted_itinerary_count: int
    deleted_audit_event_count: int
    deleted_lineage_event_count: int
    summary: str | None
    started_at: datetime
    completed_at: datetime | None


class BackupRunOut(BaseModel):
    id: str
    org_id: str
    initiated_by_user_id: str | None
    trigger_kind: str
    status: str
    backup_file_name: str | None
    backup_file_path: str | None
    encrypted_size_bytes: int | None
    rotated_file_count: int
    summary: str | None
    started_at: datetime
    completed_at: datetime | None


class RestoreRunOut(BaseModel):
    id: str
    org_id: str
    initiated_by_user_id: str | None
    status: str
    backup_file_name: str
    restored_table_count: int
    summary: str | None
    started_at: datetime
    completed_at: datetime | None


class RestoreRequest(BaseModel):
    backup_file_name: str = Field(min_length=1, max_length=255)
