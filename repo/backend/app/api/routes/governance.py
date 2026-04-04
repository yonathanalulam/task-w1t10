from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_dep, org_admin_csrf_session_dep, org_admin_session_dep, require_recent_step_up
from app.models.auth import Session as AuthSession
from app.schemas.governance import (
    AttractionCreateRequest,
    AttractionDuplicateGroupOut,
    AttractionMergeOut,
    AttractionMergeRequest,
    AttractionOut,
    AttractionUpdateRequest,
    DatasetCreateRequest,
    DatasetOut,
    DatasetUpdateRequest,
    OrgUserOut,
    ProjectCreateRequest,
    ProjectDatasetOut,
    ProjectMemberCreateRequest,
    ProjectMemberOut,
    ProjectMemberUpdateRequest,
    ProjectOut,
    ProjectUpdateRequest,
)
from app.services.governance import (
    GovernanceConflictError,
    GovernanceMergeConflictError,
    GovernanceValidationError,
    add_project_member,
    create_attraction,
    create_dataset,
    create_project,
    get_attraction,
    get_dataset,
    get_project,
    link_dataset_to_project,
    list_attraction_duplicate_groups,
    list_attractions,
    list_datasets,
    list_org_users,
    list_project_datasets,
    list_project_members,
    list_projects,
    merge_attractions,
    remove_project_member,
    unlink_dataset_from_project,
    update_attraction,
    update_dataset,
    update_project,
    update_project_member,
)
from app.services.audit import record_audit_event
from app.services.lineage import record_lineage_event

router = APIRouter(tags=["governance"])


def _attraction_out(row) -> AttractionOut:
    return AttractionOut(
        id=row.id,
        dataset_id=row.dataset_id,
        name=row.name,
        city=row.city,
        state=row.state,
        description=row.description,
        latitude=row.latitude,
        longitude=row.longitude,
        duration_minutes=row.duration_minutes,
        status=row.status,
        normalized_dedupe_key=row.normalized_dedupe_key,
        merged_into_attraction_id=row.merged_into_attraction_id,
        merged_at=row.merged_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _duplicate_label_from_key(key: str) -> str:
    parts = key.split("|", 2)
    if len(parts) != 3:
        return key
    return f"{parts[0]} / {parts[1]}, {parts[2]}"


def _project_member_out(member) -> ProjectMemberOut:
    return ProjectMemberOut(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username,
        role_in_project=member.role_in_project,
        can_edit=member.can_edit,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


def _project_member_audit_metadata(*, project_id: str, member) -> dict:
    return {
        "project_id": project_id,
        "user_id": member.user_id,
        "username": member.user.username,
        "role_in_project": member.role_in_project,
        "can_edit": member.can_edit,
    }


@router.get("/admin/users", response_model=list[OrgUserOut])
def org_users(
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[OrgUserOut]:
    users = list_org_users(db, org_id=auth_session.user.org_id)
    return [
        OrgUserOut(
            id=user.id,
            username=user.username,
            active=user.is_active,
            roles=sorted([user_role.role.name for user_role in user.user_roles]),
        )
        for user in users
    ]


@router.get("/datasets", response_model=list[DatasetOut])
def datasets(
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[DatasetOut]:
    rows = list_datasets(db, org_id=auth_session.user.org_id)
    return [
        DatasetOut(
            id=row.id,
            name=row.name,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/datasets", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def datasets_create(
    payload: DatasetCreateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> DatasetOut:
    try:
        dataset = create_dataset(
            db,
            org_id=auth_session.user.org_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return DatasetOut(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        status=dataset.status,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.patch("/datasets/{dataset_id}", response_model=DatasetOut)
def datasets_update(
    dataset_id: str,
    payload: DatasetUpdateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> DatasetOut:
    dataset = get_dataset(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        dataset = update_dataset(
            db,
            dataset=dataset,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return DatasetOut(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        status=dataset.status,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@router.get("/datasets/{dataset_id}/attractions", response_model=list[AttractionOut])
def dataset_attractions(
    dataset_id: str,
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[AttractionOut]:
    dataset = get_dataset(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    return [
        _attraction_out(row)
        for row in list_attractions(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    ]


@router.post("/datasets/{dataset_id}/attractions", response_model=AttractionOut, status_code=status.HTTP_201_CREATED)
def dataset_attractions_create(
    dataset_id: str,
    payload: AttractionCreateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> AttractionOut:
    dataset = get_dataset(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    attraction = create_attraction(
        db,
        org_id=auth_session.user.org_id,
        dataset_id=dataset_id,
        name=payload.name,
        city=payload.city,
        state=payload.state,
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        duration_minutes=payload.duration_minutes,
        status=payload.status,
    )
    return _attraction_out(attraction)


@router.get("/datasets/{dataset_id}/attractions/duplicates", response_model=list[AttractionDuplicateGroupOut])
def dataset_attraction_duplicates(
    dataset_id: str,
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[AttractionDuplicateGroupOut]:
    dataset = get_dataset(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    groups = list_attraction_duplicate_groups(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    return [
        AttractionDuplicateGroupOut(
            duplicate_key=key,
            duplicate_label=_duplicate_label_from_key(key),
            candidate_count=len(candidates),
            candidates=[_attraction_out(candidate) for candidate in candidates],
        )
        for key, candidates in groups
    ]


@router.post("/datasets/{dataset_id}/attractions/merge", response_model=AttractionMergeOut)
def dataset_attractions_merge(
    dataset_id: str,
    payload: AttractionMergeRequest,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> AttractionMergeOut:
    dataset = get_dataset(db, org_id=auth_session.user.org_id, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    try:
        merge_event = merge_attractions(
            db,
            org_id=auth_session.user.org_id,
            dataset_id=dataset_id,
            source_attraction_id=payload.source_attraction_id,
            target_attraction_id=payload.target_attraction_id,
            merged_by_user_id=auth_session.user_id,
            merge_reason=payload.merge_reason,
        )
    except GovernanceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except GovernanceMergeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not merge_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target attraction not found in your organization",
        )

    source = get_attraction(
        db,
        org_id=auth_session.user.org_id,
        dataset_id=dataset_id,
        attraction_id=payload.source_attraction_id,
    )
    if not source or source.merged_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Merge was not persisted")

    record_lineage_event(
        db,
        org_id=auth_session.user.org_id,
        project_id=None,
        dataset_id=dataset_id,
        itinerary_id=None,
        created_by_user_id=auth_session.user_id,
        event_type="governance.attraction_merge",
        entity_type="attraction",
        entity_id=payload.target_attraction_id,
        payload={
            "source_attraction_id": payload.source_attraction_id,
            "target_attraction_id": payload.target_attraction_id,
            "merge_event_id": merge_event.id,
        },
    )
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="governance.attraction_merge",
        resource_type="attraction",
        resource_id=payload.target_attraction_id,
        request_method="POST",
        request_path=f"/api/datasets/{dataset_id}/attractions/merge",
        status_code=200,
        detail_summary="Merged duplicate attractions",
        metadata_json={
            "source_attraction_id": payload.source_attraction_id,
            "target_attraction_id": payload.target_attraction_id,
            "merge_event_id": merge_event.id,
            "dataset_id": dataset_id,
        },
    )

    return AttractionMergeOut(
        merge_event_id=merge_event.id,
        source_attraction_id=payload.source_attraction_id,
        target_attraction_id=payload.target_attraction_id,
        merged_at=source.merged_at,
    )


@router.patch("/datasets/{dataset_id}/attractions/{attraction_id}", response_model=AttractionOut)
def dataset_attractions_update(
    dataset_id: str,
    attraction_id: str,
    payload: AttractionUpdateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> AttractionOut:
    attraction = get_attraction(
        db,
        org_id=auth_session.user.org_id,
        dataset_id=dataset_id,
        attraction_id=attraction_id,
    )
    if not attraction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attraction not found")

    try:
        attraction = update_attraction(
            db,
            attraction=attraction,
            name=payload.name,
            city=payload.city,
            state=payload.state,
            description=payload.description,
            latitude=payload.latitude,
            longitude=payload.longitude,
            duration_minutes=payload.duration_minutes,
            status=payload.status,
        )
    except GovernanceMergeConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _attraction_out(attraction)


@router.get("/projects", response_model=list[ProjectOut])
def projects(
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[ProjectOut]:
    rows = list_projects(db, org_id=auth_session.user.org_id)
    return [
        ProjectOut(
            id=row.id,
            name=row.name,
            code=row.code,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def projects_create(
    payload: ProjectCreateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ProjectOut:
    try:
        project = create_project(
            db,
            org_id=auth_session.user.org_id,
            name=payload.name,
            code=payload.code,
            description=payload.description,
            status=payload.status,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ProjectOut(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def projects_update(
    project_id: str,
    payload: ProjectUpdateRequest,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ProjectOut:
    project = get_project(db, org_id=auth_session.user.org_id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        project = update_project(
            db,
            project=project,
            name=payload.name,
            code=payload.code,
            description=payload.description,
            status=payload.status,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ProjectOut(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def projects_members(
    project_id: str,
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[ProjectMemberOut]:
    project = get_project(db, org_id=auth_session.user.org_id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    members = list_project_members(db, org_id=auth_session.user.org_id, project_id=project_id)
    return [
        ProjectMemberOut(
            id=member.id,
            user_id=member.user_id,
            username=member.user.username,
            role_in_project=member.role_in_project,
            can_edit=member.can_edit,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )
        for member in members
    ]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def projects_members_create(
    project_id: str,
    payload: ProjectMemberCreateRequest,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ProjectMemberOut:
    try:
        member = add_project_member(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            user_id=payload.user_id,
            role_in_project=payload.role_in_project,
            can_edit=payload.can_edit,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or user not found in your organization",
        )

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="governance.project_member_created",
        resource_type="project_member",
        resource_id=member.id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/members",
        status_code=201,
        project_id=project_id,
        detail_summary="Added project member permissions",
        metadata_json=_project_member_audit_metadata(project_id=project_id, member=member),
    )
    return _project_member_out(member)


@router.patch("/projects/{project_id}/members/{member_id}", response_model=ProjectMemberOut)
def projects_members_update(
    project_id: str,
    member_id: str,
    payload: ProjectMemberUpdateRequest,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ProjectMemberOut:
    member = update_project_member(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        member_id=member_id,
        role_in_project=payload.role_in_project,
        can_edit=payload.can_edit,
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found")

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="governance.project_member_updated",
        resource_type="project_member",
        resource_id=member.id,
        request_method="PATCH",
        request_path=f"/api/projects/{project_id}/members/{member_id}",
        status_code=200,
        project_id=project_id,
        detail_summary="Updated project member permissions",
        metadata_json=_project_member_audit_metadata(project_id=project_id, member=member),
    )
    return _project_member_out(member)


@router.delete("/projects/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def projects_members_delete(
    project_id: str,
    member_id: str,
    _: AuthSession = Depends(require_recent_step_up),
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> None:
    existing_member = next(
        (row for row in list_project_members(db, org_id=auth_session.user.org_id, project_id=project_id) if row.id == member_id),
        None,
    )
    if not existing_member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found")

    deleted = remove_project_member(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        member_id=member_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found")

    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="governance.project_member_deleted",
        resource_type="project_member",
        resource_id=member_id,
        request_method="DELETE",
        request_path=f"/api/projects/{project_id}/members/{member_id}",
        status_code=204,
        project_id=project_id,
        detail_summary="Removed project member permissions",
        metadata_json=_project_member_audit_metadata(project_id=project_id, member=existing_member),
    )


@router.get("/projects/{project_id}/datasets", response_model=list[ProjectDatasetOut])
def projects_datasets(
    project_id: str,
    auth_session: AuthSession = Depends(org_admin_session_dep),
    db: Session = Depends(db_dep),
) -> list[ProjectDatasetOut]:
    project = get_project(db, org_id=auth_session.user.org_id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    links = list_project_datasets(db, org_id=auth_session.user.org_id, project_id=project_id)
    return [
        ProjectDatasetOut(
            id=link.id,
            dataset_id=link.dataset_id,
            dataset_name=link.dataset.name,
            created_at=link.created_at,
        )
        for link in links
    ]


@router.post("/projects/{project_id}/datasets/{dataset_id}", response_model=ProjectDatasetOut, status_code=status.HTTP_201_CREATED)
def projects_datasets_link(
    project_id: str,
    dataset_id: str,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> ProjectDatasetOut:
    try:
        link = link_dataset_to_project(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
    except GovernanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or dataset not found in your organization",
        )

    return ProjectDatasetOut(
        id=link.id,
        dataset_id=link.dataset_id,
        dataset_name=link.dataset.name,
        created_at=link.created_at,
    )


@router.delete("/projects/{project_id}/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def projects_datasets_unlink(
    project_id: str,
    dataset_id: str,
    auth_session: AuthSession = Depends(org_admin_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> None:
    removed = unlink_dataset_from_project(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        dataset_id=dataset_id,
    )
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project dataset link not found")
