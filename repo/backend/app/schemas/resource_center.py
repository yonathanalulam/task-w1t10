from datetime import datetime

from pydantic import BaseModel


class ResourceAssetOut(BaseModel):
    id: str
    project_id: str
    scope_type: str
    attraction_id: str | None
    itinerary_id: str | None
    original_file_name: str
    file_extension: str
    declared_mime_type: str | None
    detected_mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    preview_kind: str
    is_quarantined: bool
    quarantine_reason: str | None
    scan_status: str
    cleanup_eligible_at: datetime | None
    created_at: datetime


class ResourceAssetUploadResultOut(BaseModel):
    asset: ResourceAssetOut
    validation: dict[str, str | int | bool | None]
