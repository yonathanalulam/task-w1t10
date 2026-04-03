from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import db_dep, planner_csrf_session_dep, planner_session_dep
from app.models.auth import Session as AuthSession
from app.schemas.resource_center import ResourceAssetOut, ResourceAssetUploadResultOut
from app.services.resource_center import (
    ResourceCenterAuthorizationError,
    ResourceCenterValidationError,
    get_asset_for_download,
    list_attraction_assets,
    list_itinerary_assets,
    open_asset_stream,
    unreference_asset,
    upload_attraction_asset,
    upload_itinerary_asset,
)
from app.services.audit import record_audit_event

router = APIRouter(tags=["resource_center"])


def _asset_out(asset) -> ResourceAssetOut:
    return ResourceAssetOut(
        id=asset.id,
        project_id=asset.project_id,
        scope_type=asset.scope_type,
        attraction_id=asset.attraction_id,
        itinerary_id=asset.itinerary_id,
        original_file_name=asset.original_file_name,
        file_extension=asset.file_extension,
        declared_mime_type=asset.declared_mime_type,
        detected_mime_type=asset.detected_mime_type,
        file_size_bytes=asset.file_size_bytes,
        sha256_checksum=asset.sha256_checksum,
        preview_kind=asset.preview_kind,
        is_quarantined=asset.is_quarantined,
        quarantine_reason=asset.quarantine_reason,
        scan_status=asset.scan_status,
        cleanup_eligible_at=asset.cleanup_eligible_at,
        created_at=asset.created_at,
    )


@router.get("/projects/{project_id}/resources/attractions/{attraction_id}/assets", response_model=list[ResourceAssetOut])
def attraction_assets_list(
    project_id: str,
    attraction_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[ResourceAssetOut]:
    rows = list_attraction_assets(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        attraction_id=attraction_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction scope not found")
    return [_asset_out(asset) for asset in rows]


@router.post(
    "/projects/{project_id}/resources/attractions/{attraction_id}/assets",
    response_model=ResourceAssetUploadResultOut,
    status_code=status.HTTP_201_CREATED,
)
def attraction_assets_upload(
    project_id: str,
    attraction_id: str,
    file: UploadFile = File(...),
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ResourceAssetUploadResultOut:
    try:
        asset = upload_attraction_asset(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            attraction_id=attraction_id,
            user=auth_session.user,
            upload_file=file,
        )
    except ResourceCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ResourceCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction scope not found")

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="resource_center.attraction_asset_upload",
        resource_type="resource_asset",
        resource_id=asset.id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/resources/attractions/{attraction_id}/assets",
        status_code=201,
        project_id=project_id,
        detail_summary="Uploaded attraction scoped asset",
        metadata_json={"scope_type": "attraction", "detected_mime_type": asset.detected_mime_type},
    )

    return ResourceAssetUploadResultOut(
        asset=_asset_out(asset),
        validation={
            "extension": asset.file_extension,
            "declared_mime_type": asset.declared_mime_type,
            "detected_mime_type": asset.detected_mime_type,
            "size_bytes": asset.file_size_bytes,
            "checksum": asset.sha256_checksum,
            "signature_valid": True,
        },
    )


@router.get("/projects/{project_id}/resources/itineraries/{itinerary_id}/assets", response_model=list[ResourceAssetOut])
def itinerary_assets_list(
    project_id: str,
    itinerary_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[ResourceAssetOut]:
    rows = list_itinerary_assets(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        itinerary_id=itinerary_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary scope not found")
    return [_asset_out(asset) for asset in rows]


@router.post(
    "/projects/{project_id}/resources/itineraries/{itinerary_id}/assets",
    response_model=ResourceAssetUploadResultOut,
    status_code=status.HTTP_201_CREATED,
)
def itinerary_assets_upload(
    project_id: str,
    itinerary_id: str,
    file: UploadFile = File(...),
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ResourceAssetUploadResultOut:
    try:
        asset = upload_itinerary_asset(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
            upload_file=file,
        )
    except ResourceCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ResourceCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary scope not found")

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="resource_center.itinerary_asset_upload",
        resource_type="resource_asset",
        resource_id=asset.id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/resources/itineraries/{itinerary_id}/assets",
        status_code=201,
        project_id=project_id,
        detail_summary="Uploaded itinerary scoped asset",
        metadata_json={"scope_type": "itinerary", "detected_mime_type": asset.detected_mime_type},
    )

    return ResourceAssetUploadResultOut(
        asset=_asset_out(asset),
        validation={
            "extension": asset.file_extension,
            "declared_mime_type": asset.declared_mime_type,
            "detected_mime_type": asset.detected_mime_type,
            "size_bytes": asset.file_size_bytes,
            "checksum": asset.sha256_checksum,
            "signature_valid": True,
        },
    )


@router.get("/projects/{project_id}/resources/assets/{asset_id}/download")
def resource_asset_download(
    project_id: str,
    asset_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
):
    asset = get_asset_for_download(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        asset_id=asset_id,
        user=auth_session.user,
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource asset not found")

    try:
        stream = open_asset_stream(asset)
    except ResourceCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    disposition = "inline" if asset.preview_kind == "image" else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{asset.original_file_name}"'}
    return StreamingResponse(
        stream,
        media_type=asset.detected_mime_type,
        headers=headers,
        background=BackgroundTask(stream.close),
    )


@router.delete("/projects/{project_id}/resources/assets/{asset_id}", response_model=ResourceAssetOut)
def resource_asset_unreference(
    project_id: str,
    asset_id: str,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ResourceAssetOut:
    try:
        asset = unreference_asset(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            asset_id=asset_id,
            user=auth_session.user,
        )
    except ResourceCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource asset not found")
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="resource_center.asset_unreference",
        resource_type="resource_asset",
        resource_id=asset.id,
        request_method="DELETE",
        request_path=f"/api/projects/{project_id}/resources/assets/{asset_id}",
        status_code=200,
        project_id=project_id,
        detail_summary="Unreferenced resource asset",
        metadata_json={"cleanup_eligible_at": asset.cleanup_eligible_at.isoformat() if asset.cleanup_eligible_at else None},
    )
    return _asset_out(asset)
