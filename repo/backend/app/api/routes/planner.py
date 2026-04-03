import io
import re
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PlannerActor, db_dep, planner_csrf_session_dep, planner_session_dep, planner_sync_actor_dep
from app.models.auth import Session as AuthSession
from app.models.organization import Organization
from app.schemas.planner import (
    ItineraryCreateRequest,
    ItineraryDayCreateRequest,
    ItineraryDayOut,
    ItineraryImportReceiptOut,
    SyncPackageImportReceiptOut,
    ItineraryDayUpdateRequest,
    ItineraryListOut,
    ItineraryOut,
    ItineraryStopCreateRequest,
    ItineraryStopOut,
    ItineraryStopReorderRequest,
    ItineraryStopUpdateRequest,
    ItineraryUpdateRequest,
    ItineraryVersionOut,
    ItineraryWarningOut,
    PlannerCatalogAttractionOut,
    PlannerProjectOut,
    PlannerUserOut,
)
from app.services.planner import (
    PlannerAuthorizationError,
    PlannerConflictError,
    PlannerValidationError,
    analyze_day,
    archive_itinerary,
    create_itinerary,
    create_itinerary_day,
    create_itinerary_stop,
    delete_itinerary_day,
    delete_itinerary_stop,
    export_itinerary_file,
    export_sync_package_archive,
    get_itinerary_for_user,
    import_itinerary_file,
    import_sync_package_archive,
    list_assignable_planners,
    list_itinerary_versions,
    list_planner_projects,
    list_project_catalog_attractions,
    list_project_itineraries,
    reorder_itinerary_stops,
    update_itinerary,
    update_itinerary_day,
    update_itinerary_stop,
)
from app.services.audit import record_audit_event
from app.services.lineage import record_lineage_event

router = APIRouter(tags=["planner"])


def _day_out(day, day_analysis: dict) -> ItineraryDayOut:
    return ItineraryDayOut(
        id=day.id,
        itinerary_id=day.itinerary_id,
        day_number=day.day_number,
        title=day.title,
        notes=day.notes,
        effective_urban_speed_mph=day_analysis["effective_urban_speed_mph"],
        effective_highway_speed_mph=day_analysis["effective_highway_speed_mph"],
        travel_distance_miles=day_analysis["travel_distance_miles"],
        travel_time_minutes=day_analysis["travel_time_minutes"],
        activity_minutes=day_analysis["activity_minutes"],
        warnings=[ItineraryWarningOut(**warning) for warning in day_analysis["warnings"]],
        stops=[
            ItineraryStopOut(
                id=stop.id,
                itinerary_day_id=stop.itinerary_day_id,
                attraction_id=stop.attraction_id,
                attraction_name=stop.attraction.name,
                attraction_city=stop.attraction.city,
                attraction_state=stop.attraction.state,
                latitude=stop.attraction.latitude,
                longitude=stop.attraction.longitude,
                order_index=stop.order_index,
                start_minute_of_day=stop.start_minute_of_day,
                duration_minutes=stop.duration_minutes,
                notes=stop.notes,
            )
            for stop in day_analysis["ordered_stops"]
        ],
    )


def _itinerary_out(itinerary, org: Organization) -> ItineraryOut:
    day_payload = []
    for day in sorted(itinerary.days, key=lambda row: row.day_number):
        day_analysis = analyze_day(org, itinerary, day)
        day_payload.append(_day_out(day, day_analysis))

    return ItineraryOut(
        id=itinerary.id,
        org_id=itinerary.org_id,
        project_id=itinerary.project_id,
        name=itinerary.name,
        description=itinerary.description,
        status=itinerary.status,
        assigned_planner_user_id=itinerary.assigned_planner_user_id,
        assigned_planner_username=itinerary.assigned_planner.username if itinerary.assigned_planner else None,
        urban_speed_mph_override=itinerary.urban_speed_mph_override,
        highway_speed_mph_override=itinerary.highway_speed_mph_override,
        org_default_urban_speed_mph=org.default_urban_speed_mph,
        org_default_highway_speed_mph=org.default_highway_speed_mph,
        created_at=itinerary.created_at,
        updated_at=itinerary.updated_at,
        version_counter=itinerary.version_counter,
        days=day_payload,
    )


@router.get("/planner/projects", response_model=list[PlannerProjectOut])
def planner_projects(
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[PlannerProjectOut]:
    rows = list_planner_projects(db, org_id=auth_session.user.org_id, user=auth_session.user)
    return [
        PlannerProjectOut(id=project.id, name=project.name, code=project.code, can_edit=can_edit)
        for project, can_edit in rows
    ]


@router.get("/planner/users", response_model=list[PlannerUserOut])
def planner_users(
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[PlannerUserOut]:
    rows = list_assignable_planners(db, org_id=auth_session.user.org_id, user=auth_session.user)
    return [PlannerUserOut(id=user.id, username=user.username) for user in rows]


@router.get("/projects/{project_id}/catalog/attractions", response_model=list[PlannerCatalogAttractionOut])
def planner_project_catalog(
    project_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[PlannerCatalogAttractionOut]:
    rows = list_project_catalog_attractions(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return [
        PlannerCatalogAttractionOut(
            id=attraction.id,
            dataset_id=attraction.dataset_id,
            dataset_name=dataset_name,
            name=attraction.name,
            city=attraction.city,
            state=attraction.state,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            duration_minutes=attraction.duration_minutes,
        )
        for attraction, dataset_name in rows
    ]


@router.get("/projects/{project_id}/itineraries", response_model=list[ItineraryListOut])
def project_itineraries(
    project_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[ItineraryListOut]:
    rows = list_project_itineraries(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return [
        ItineraryListOut(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            status=row.status,
            assigned_planner_user_id=row.assigned_planner_user_id,
            assigned_planner_username=row.assigned_planner.username if row.assigned_planner else None,
            updated_at=row.updated_at,
            day_count=len(row.days),
        )
        for row in rows
    ]


@router.post("/projects/{project_id}/itineraries", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
def project_itineraries_create(
    project_id: str,
    payload: ItineraryCreateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = create_itinerary(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            user=auth_session.user,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            assigned_planner_user_id=payload.assigned_planner_user_id,
            urban_speed_mph_override=payload.urban_speed_mph_override,
            highway_speed_mph_override=payload.highway_speed_mph_override,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PlannerConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.get("/projects/{project_id}/itineraries/{itinerary_id}", response_model=ItineraryOut)
def project_itinerary_get(
    project_id: str,
    itinerary_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    itinerary = get_itinerary_for_user(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        itinerary_id=itinerary_id,
        user=auth_session.user,
        require_edit=False,
    )
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.patch("/projects/{project_id}/itineraries/{itinerary_id}", response_model=ItineraryOut)
def project_itinerary_update(
    project_id: str,
    itinerary_id: str,
    payload: ItineraryUpdateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = update_itinerary(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            assigned_planner_user_id=payload.assigned_planner_user_id,
            urban_speed_mph_override=payload.urban_speed_mph_override,
            highway_speed_mph_override=payload.highway_speed_mph_override,
            provided_fields=payload.model_fields_set,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PlannerConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.delete("/projects/{project_id}/itineraries/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def project_itinerary_archive(
    project_id: str,
    itinerary_id: str,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> None:
    try:
        archived = archive_itinerary(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")


@router.post("/projects/{project_id}/itineraries/{itinerary_id}/days", response_model=ItineraryOut)
def itinerary_days_create(
    project_id: str,
    itinerary_id: str,
    payload: ItineraryDayCreateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = create_itinerary_day(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
            day_number=payload.day_number,
            title=payload.title,
            notes=payload.notes,
            urban_speed_mph_override=payload.urban_speed_mph_override,
            highway_speed_mph_override=payload.highway_speed_mph_override,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PlannerConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.patch("/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}", response_model=ItineraryOut)
def itinerary_days_update(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    payload: ItineraryDayUpdateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = update_itinerary_day(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            user=auth_session.user,
            day_number=payload.day_number,
            title=payload.title,
            notes=payload.notes,
            urban_speed_mph_override=payload.urban_speed_mph_override,
            highway_speed_mph_override=payload.highway_speed_mph_override,
            provided_fields=payload.model_fields_set,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PlannerConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.delete("/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}", response_model=ItineraryOut)
def itinerary_days_delete(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = delete_itinerary_day(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            user=auth_session.user,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.post("/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops", response_model=ItineraryOut)
def itinerary_stops_create(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    payload: ItineraryStopCreateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = create_itinerary_stop(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            user=auth_session.user,
            attraction_id=payload.attraction_id,
            start_minute_of_day=payload.start_minute_of_day,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.patch(
    "/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}",
    response_model=ItineraryOut,
)
def itinerary_stops_update(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    stop_id: str,
    payload: ItineraryStopUpdateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = update_itinerary_stop(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            stop_id=stop_id,
            user=auth_session.user,
            start_minute_of_day=payload.start_minute_of_day,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes,
            provided_fields=payload.model_fields_set,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary stop not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.delete(
    "/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/{stop_id}",
    response_model=ItineraryOut,
)
def itinerary_stops_delete(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    stop_id: str,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = delete_itinerary_stop(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            stop_id=stop_id,
            user=auth_session.user,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary stop not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


@router.post(
    "/projects/{project_id}/itineraries/{itinerary_id}/days/{day_id}/stops/reorder",
    response_model=ItineraryOut,
)
def itinerary_stops_reorder(
    project_id: str,
    itinerary_id: str,
    day_id: str,
    payload: ItineraryStopReorderRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryOut:
    try:
        itinerary = reorder_itinerary_stops(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            day_id=day_id,
            user=auth_session.user,
            ordered_stop_ids=payload.ordered_stop_ids,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary day not found")

    org = db.execute(select(Organization).where(Organization.id == itinerary.org_id)).scalars().one()
    return _itinerary_out(itinerary, org)


def _safe_download_filename(value: str, *, default: str) -> str:
    collapsed = re.sub(r"\s+", "_", value.strip())
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "", collapsed)
    return sanitized or default


@router.get("/projects/{project_id}/itineraries/{itinerary_id}/export")
def itinerary_export(
    project_id: str,
    itinerary_id: str,
    format: Literal["csv", "xlsx"] = Query(default="csv"),
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> StreamingResponse:
    try:
        exported = export_itinerary_file(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
            export_format=format,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except PlannerValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if not exported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    payload, media_type, extension, itinerary_name = exported
    safe_name = _safe_download_filename(itinerary_name, default="itinerary")
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}.{extension}"'}
    return StreamingResponse(io.BytesIO(payload), media_type=media_type, headers=headers)


@router.post("/projects/{project_id}/itineraries/{itinerary_id}/import", response_model=ItineraryImportReceiptOut)
async def itinerary_import(
    project_id: str,
    itinerary_id: str,
    file: UploadFile = File(...),
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ItineraryImportReceiptOut:
    try:
        content = await file.read()
        receipt = import_itinerary_file(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=auth_session.user,
            file_name=file.filename or "uploaded_file",
            content=content,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    record_lineage_event(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        dataset_id=None,
        itinerary_id=itinerary_id,
        created_by_user_id=auth_session.user_id,
        event_type="planner.itinerary_import",
        entity_type="itinerary",
        entity_id=itinerary_id,
        payload={
            "file_name": receipt.get("file_name"),
            "file_format": receipt.get("file_format"),
            "accepted_row_count": receipt.get("accepted_row_count"),
            "rejected_row_count": receipt.get("rejected_row_count"),
            "applied": receipt.get("applied"),
        },
    )
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="planner.itinerary_import",
        resource_type="itinerary",
        resource_id=itinerary_id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/itineraries/{itinerary_id}/import",
        status_code=200,
        project_id=project_id,
        detail_summary="Imported itinerary rows",
        metadata_json={
            "accepted_row_count": receipt.get("accepted_row_count"),
            "rejected_row_count": receipt.get("rejected_row_count"),
            "applied": receipt.get("applied"),
        },
    )
    return ItineraryImportReceiptOut(**receipt)


@router.get("/projects/{project_id}/sync-package/export")
def sync_package_export(
    project_id: str,
    actor: PlannerActor = Depends(planner_sync_actor_dep),
    db: Session = Depends(db_dep),
) -> StreamingResponse:
    try:
        exported = export_sync_package_archive(
            db,
            org_id=actor.user.org_id,
            project_id=project_id,
            user=actor.user,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not exported:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    payload, package_name = exported
    record_lineage_event(
        db,
        org_id=actor.user.org_id,
        project_id=project_id,
        dataset_id=None,
        itinerary_id=None,
        created_by_user_id=actor.user.id,
        event_type="planner.sync_package_export",
        entity_type="project",
        entity_id=project_id,
        payload={"package_name": package_name, "auth_mode": actor.auth_mode},
    )
    record_audit_event(
        db,
        org_id=actor.user.org_id,
        actor_user_id=actor.user.id,
        action_type="planner.sync_package_export",
        resource_type="project",
        resource_id=project_id,
        request_method="GET",
        request_path=f"/api/projects/{project_id}/sync-package/export",
        status_code=200,
        project_id=project_id,
        detail_summary="Exported sync package",
        metadata_json={"package_name": package_name, "auth_mode": actor.auth_mode},
    )
    safe_name = _safe_download_filename(package_name, default="sync_package")
    headers = {"Content-Disposition": f'attachment; filename="{safe_name}.zip"'}
    return StreamingResponse(io.BytesIO(payload), media_type="application/zip", headers=headers)


@router.post("/projects/{project_id}/sync-package/import", response_model=SyncPackageImportReceiptOut)
async def sync_package_import(
    project_id: str,
    file: UploadFile = File(...),
    actor: PlannerActor = Depends(planner_sync_actor_dep),
    db: Session = Depends(db_dep),
) -> SyncPackageImportReceiptOut:
    try:
        content = await file.read()
        receipt = import_sync_package_archive(
            db,
            org_id=actor.user.org_id,
            project_id=project_id,
            user=actor.user,
            file_name=file.filename or "sync_package.zip",
            content=content,
        )
    except PlannerAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    record_lineage_event(
        db,
        org_id=actor.user.org_id,
        project_id=project_id,
        dataset_id=None,
        itinerary_id=None,
        created_by_user_id=actor.user.id,
        event_type="planner.sync_package_import",
        entity_type="project",
        entity_id=project_id,
        payload={
            "file_name": receipt.get("file_name"),
            "integrity_validated": receipt.get("integrity_validated"),
            "applied_record_count": receipt.get("applied_record_count"),
            "conflict_count": receipt.get("conflict_count"),
        },
    )
    record_audit_event(
        db,
        org_id=actor.user.org_id,
        actor_user_id=actor.user.id,
        action_type="planner.sync_package_import",
        resource_type="project",
        resource_id=project_id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/sync-package/import",
        status_code=200,
        project_id=project_id,
        detail_summary="Imported sync package",
        metadata_json={
            "integrity_validated": receipt.get("integrity_validated"),
            "applied_record_count": receipt.get("applied_record_count"),
            "conflict_count": receipt.get("conflict_count"),
            "auth_mode": actor.auth_mode,
        },
    )
    return SyncPackageImportReceiptOut(**receipt)


@router.get("/projects/{project_id}/itineraries/{itinerary_id}/versions", response_model=list[ItineraryVersionOut])
def itinerary_versions(
    project_id: str,
    itinerary_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[ItineraryVersionOut]:
    rows = list_itinerary_versions(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        itinerary_id=itinerary_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    return [
        ItineraryVersionOut(
            id=row.id,
            itinerary_id=row.itinerary_id,
            version_number=row.version_number,
            change_summary=row.change_summary,
            created_by_user_id=row.created_by_user_id,
            created_by_username=row.created_by_user.username,
            created_at=row.created_at,
            snapshot=row.snapshot,
        )
        for row in rows
    ]
