from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import utcnow
from app.models.governance import Attraction, Project, ProjectDataset, ProjectMember
from app.models.planner import Itinerary
from app.models.resource_center import ResourceAsset
from app.models.user import User
from app.services.object_storage import LocalDiskObjectStorage, ObjectStorageError

ALLOWED_EXTENSIONS = {"pdf", "docx", "xlsx", "csv", "jpg", "jpeg", "png"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
EXTENSION_MIME_EXPECTATIONS = {
    "pdf": {"application/pdf"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "csv": {"text/csv"},
}


class ResourceCenterValidationError(Exception):
    """Raised when uploaded media fails controlled validation."""


class ResourceCenterAuthorizationError(Exception):
    """Raised when caller lacks required project/scope access."""


@dataclass(slots=True)
class ValidatedUpload:
    original_file_name: str
    extension: str
    declared_mime_type: str | None
    detected_mime_type: str
    preview_kind: str
    file_size_bytes: int
    bytes_payload: bytes
    sha256_checksum: str


def _role_names(user: User) -> set[str]:
    return {user_role.role.name for user_role in user.user_roles}


def _is_org_admin(user: User) -> bool:
    return "ORG_ADMIN" in _role_names(user)


def _project_membership(db: Session, *, project_id: str, user_id: str) -> ProjectMember | None:
    return (
        db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id))
        .scalars()
        .first()
    )


def _project_for_user(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    user: User,
    require_edit: bool,
) -> Project | None:
    project = db.execute(select(Project).where(Project.id == project_id, Project.org_id == org_id)).scalars().first()
    if not project:
        return None

    if _is_org_admin(user):
        return project

    membership = _project_membership(db, project_id=project_id, user_id=user.id)
    if not membership:
        return None
    if require_edit and not membership.can_edit:
        raise ResourceCenterAuthorizationError("Project membership is read-only")
    return project


def _resolve_attraction_scope(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    attraction_id: str,
) -> Attraction | None:
    return (
        db.execute(
            select(Attraction)
            .join(ProjectDataset, ProjectDataset.dataset_id == Attraction.dataset_id)
            .where(
                Attraction.id == attraction_id,
                Attraction.org_id == org_id,
                ProjectDataset.project_id == project_id,
                Attraction.merged_into_attraction_id.is_(None),
            )
        )
        .scalars()
        .first()
    )


def _resolve_itinerary_scope(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    itinerary_id: str,
    user: User,
    require_edit: bool,
) -> Itinerary | None:
    itinerary = (
        db.execute(
            select(Itinerary).where(
                Itinerary.id == itinerary_id,
                Itinerary.org_id == org_id,
                Itinerary.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )
    if not itinerary:
        return None

    if require_edit and itinerary.assigned_planner_user_id and itinerary.assigned_planner_user_id != user.id and not _is_org_admin(user):
        raise ResourceCenterAuthorizationError("Itinerary is assigned to another planner")
    return itinerary


def _read_upload_bytes(upload_file: UploadFile, *, max_bytes: int) -> bytes:
    payload = bytearray()
    while True:
        chunk = upload_file.file.read(1024 * 1024)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > max_bytes:
            raise ResourceCenterValidationError(f"File exceeds max allowed size of {max_bytes // (1024 * 1024)} MB")
    return bytes(payload)


def _extension_from_filename(file_name: str) -> str:
    parts = file_name.rsplit(".", 1)
    if len(parts) != 2:
        return ""
    return parts[1].strip().lower()


def _detect_zip_family_mime(payload: bytes) -> str | None:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return None

    if "[Content_Types].xml" not in names:
        return None
    if any(name.startswith("word/") for name in names):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if any(name.startswith("xl/") for name in names):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None


def _detect_csv_mime(payload: bytes) -> str | None:
    if b"\x00" in payload:
        return None
    try:
        decoded = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if not decoded.strip():
        return None

    if any((ord(ch) < 32 and ch not in {"\n", "\r", "\t"}) for ch in decoded[:4096]):
        return None

    sample = decoded[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample)
        if dialect.delimiter not in {",", ";", "\t", "|"}:
            return None
    except csv.Error:
        if "," not in sample and "\n" not in sample:
            return None

    return "text/csv"


def _detect_mime(payload: bytes) -> str | None:
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"PK\x03\x04"):
        zip_mime = _detect_zip_family_mime(payload)
        if zip_mime:
            return zip_mime
    return _detect_csv_mime(payload)


def _validate_upload(upload_file: UploadFile) -> ValidatedUpload:
    settings = get_settings()
    original_name = upload_file.filename or "unnamed"
    extension = _extension_from_filename(original_name)
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ResourceCenterValidationError(f"Unsupported file extension. Allowed: {allowed}")

    payload = _read_upload_bytes(upload_file, max_bytes=settings.asset_upload_max_bytes)
    if not payload:
        raise ResourceCenterValidationError("Uploaded file is empty")

    detected_mime = _detect_mime(payload)
    if not detected_mime:
        raise ResourceCenterValidationError("File signature/content could not be validated")

    expected_mime = EXTENSION_MIME_EXPECTATIONS[extension]
    if detected_mime not in expected_mime:
        raise ResourceCenterValidationError(
            f"File extension .{extension} does not match detected content type ({detected_mime})"
        )

    preview_kind = "image" if extension in IMAGE_EXTENSIONS else "document"
    return ValidatedUpload(
        original_file_name=original_name,
        extension=extension,
        declared_mime_type=upload_file.content_type,
        detected_mime_type=detected_mime,
        preview_kind=preview_kind,
        file_size_bytes=len(payload),
        bytes_payload=payload,
        sha256_checksum=hashlib.sha256(payload).hexdigest(),
    )


def _storage() -> LocalDiskObjectStorage:
    return LocalDiskObjectStorage(root_path=get_settings().asset_storage_root)


def _next_storage_key(*, org_id: str, project_id: str, scope_type: str, extension: str) -> str:
    return f"{org_id}/{project_id}/{scope_type}/{uuid4()}.{extension}"


def _enqueue_scan_hook(_: ResourceAsset) -> None:
    """Hook point for future malware scanner queueing/integration."""


def list_attraction_assets(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    attraction_id: str,
    user: User,
) -> list[ResourceAsset] | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None
    attraction = _resolve_attraction_scope(
        db,
        org_id=org_id,
        project_id=project_id,
        attraction_id=attraction_id,
    )
    if not attraction:
        return None

    return list(
        db.execute(
            select(ResourceAsset)
            .where(
                ResourceAsset.org_id == org_id,
                ResourceAsset.project_id == project_id,
                ResourceAsset.scope_type == "attraction",
                ResourceAsset.attraction_id == attraction_id,
            )
            .order_by(ResourceAsset.created_at.desc())
        )
        .scalars()
        .all()
    )


def list_itinerary_assets(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    itinerary_id: str,
    user: User,
) -> list[ResourceAsset] | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None
    itinerary = _resolve_itinerary_scope(
        db,
        org_id=org_id,
        project_id=project_id,
        itinerary_id=itinerary_id,
        user=user,
        require_edit=False,
    )
    if not itinerary:
        return None

    return list(
        db.execute(
            select(ResourceAsset)
            .where(
                ResourceAsset.org_id == org_id,
                ResourceAsset.project_id == project_id,
                ResourceAsset.scope_type == "itinerary",
                ResourceAsset.itinerary_id == itinerary_id,
            )
            .order_by(ResourceAsset.created_at.desc())
        )
        .scalars()
        .all()
    )


def upload_attraction_asset(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    attraction_id: str,
    user: User,
    upload_file: UploadFile,
) -> ResourceAsset | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None
    attraction = _resolve_attraction_scope(
        db,
        org_id=org_id,
        project_id=project_id,
        attraction_id=attraction_id,
    )
    if not attraction:
        return None

    validated = _validate_upload(upload_file)
    key = _next_storage_key(org_id=org_id, project_id=project_id, scope_type="attraction", extension=validated.extension)
    try:
        _storage().put_bytes(key=key, data=validated.bytes_payload)
    except ObjectStorageError as exc:
        raise ResourceCenterValidationError(f"Asset storage failed: {exc}") from exc

    asset = ResourceAsset(
        org_id=org_id,
        project_id=project_id,
        scope_type="attraction",
        attraction_id=attraction.id,
        original_file_name=validated.original_file_name,
        file_extension=validated.extension,
        declared_mime_type=validated.declared_mime_type,
        detected_mime_type=validated.detected_mime_type,
        file_size_bytes=validated.file_size_bytes,
        sha256_checksum=validated.sha256_checksum,
        storage_key=key,
        preview_kind=validated.preview_kind,
        is_quarantined=False,
        quarantine_reason=None,
        scan_status="pending",
        scan_requested_at=utcnow(),
        created_by_user_id=user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    _enqueue_scan_hook(asset)
    return asset


def upload_itinerary_asset(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    itinerary_id: str,
    user: User,
    upload_file: UploadFile,
) -> ResourceAsset | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None
    itinerary = _resolve_itinerary_scope(
        db,
        org_id=org_id,
        project_id=project_id,
        itinerary_id=itinerary_id,
        user=user,
        require_edit=True,
    )
    if not itinerary:
        return None

    validated = _validate_upload(upload_file)
    key = _next_storage_key(org_id=org_id, project_id=project_id, scope_type="itinerary", extension=validated.extension)
    try:
        _storage().put_bytes(key=key, data=validated.bytes_payload)
    except ObjectStorageError as exc:
        raise ResourceCenterValidationError(f"Asset storage failed: {exc}") from exc

    asset = ResourceAsset(
        org_id=org_id,
        project_id=project_id,
        scope_type="itinerary",
        itinerary_id=itinerary.id,
        original_file_name=validated.original_file_name,
        file_extension=validated.extension,
        declared_mime_type=validated.declared_mime_type,
        detected_mime_type=validated.detected_mime_type,
        file_size_bytes=validated.file_size_bytes,
        sha256_checksum=validated.sha256_checksum,
        storage_key=key,
        preview_kind=validated.preview_kind,
        is_quarantined=False,
        quarantine_reason=None,
        scan_status="pending",
        scan_requested_at=utcnow(),
        created_by_user_id=user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    _enqueue_scan_hook(asset)
    return asset


def get_asset_for_download(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    asset_id: str,
    user: User,
) -> ResourceAsset | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None
    return (
        db.execute(
            select(ResourceAsset).where(
                ResourceAsset.id == asset_id,
                ResourceAsset.org_id == org_id,
                ResourceAsset.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )


def open_asset_stream(asset: ResourceAsset):
    try:
        return _storage().open_read(key=asset.storage_key)
    except ObjectStorageError as exc:
        raise ResourceCenterValidationError(str(exc)) from exc


def unreference_asset(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    asset_id: str,
    user: User,
) -> ResourceAsset | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None

    asset = (
        db.execute(
            select(ResourceAsset).where(
                ResourceAsset.id == asset_id,
                ResourceAsset.org_id == org_id,
                ResourceAsset.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )
    if not asset:
        return None

    asset.attraction_id = None
    asset.itinerary_id = None
    asset.cleanup_eligible_at = utcnow() + timedelta(days=get_settings().asset_cleanup_grace_days)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def run_cleanup_eligible_assets(db: Session, *, max_delete: int | None = None) -> int:
    now = utcnow()
    settings = get_settings()
    clamped_limit = max(1, min(max_delete or settings.asset_cleanup_batch_size, 2000))

    candidate_ids = list(
        db.execute(
            select(ResourceAsset.id)
            .where(
                ResourceAsset.cleanup_eligible_at.is_not(None),
                ResourceAsset.cleanup_eligible_at <= now,
                ResourceAsset.attraction_id.is_(None),
                ResourceAsset.itinerary_id.is_(None),
            )
            .order_by(ResourceAsset.cleanup_eligible_at.asc())
            .limit(clamped_limit)
        )
        .scalars()
        .all()
    )

    if not candidate_ids:
        return 0

    storage = _storage()
    deleted_count = 0
    for asset_id in candidate_ids:
        row = (
            db.execute(
                select(ResourceAsset).where(
                    ResourceAsset.id == asset_id,
                    ResourceAsset.cleanup_eligible_at.is_not(None),
                    ResourceAsset.cleanup_eligible_at <= now,
                    ResourceAsset.attraction_id.is_(None),
                    ResourceAsset.itinerary_id.is_(None),
                )
            )
            .scalars()
            .first()
        )
        if not row:
            continue

        try:
            storage.delete(key=row.storage_key, missing_ok=True)
        except ObjectStorageError:
            continue

        db.delete(row)
        deleted_count += 1

    db.commit()
    return deleted_count
