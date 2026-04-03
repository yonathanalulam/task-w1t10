from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.governance import (
    Attraction,
    AttractionMergeEvent,
    Dataset,
    Project,
    ProjectDataset,
    ProjectMember,
)
from app.models.rbac import UserRole
from app.models.user import User


class GovernanceConflictError(Exception):
    """Raised on uniqueness conflicts."""


class GovernanceValidationError(Exception):
    """Raised when a request is structurally valid but semantically invalid."""


class GovernanceMergeConflictError(Exception):
    """Raised when merge cannot proceed due to concurrent/invalid state."""


def normalize_attraction_key(name: str, city: str, state: str) -> str:
    def _normalize(value: str) -> str:
        sanitized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
        return re.sub(r"\s+", " ", sanitized).strip()

    return "|".join([_normalize(name), _normalize(city), _normalize(state)])


def list_org_users(db: Session, *, org_id: str) -> list[User]:
    return list(
        db.execute(
            select(User)
            .where(User.org_id == org_id)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.username.asc())
        )
        .scalars()
        .all()
    )


def list_datasets(db: Session, *, org_id: str) -> list[Dataset]:
    return list(
        db.execute(select(Dataset).where(Dataset.org_id == org_id).order_by(Dataset.name.asc()))
        .scalars()
        .all()
    )


def create_dataset(
    db: Session,
    *,
    org_id: str,
    name: str,
    description: str | None,
    status: str,
) -> Dataset:
    dataset = Dataset(org_id=org_id, name=name.strip(), description=description, status=status.strip())
    db.add(dataset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("Dataset name must be unique within organization") from exc
    db.refresh(dataset)
    return dataset


def get_dataset(db: Session, *, org_id: str, dataset_id: str) -> Dataset | None:
    return (
        db.execute(select(Dataset).where(Dataset.id == dataset_id, Dataset.org_id == org_id)).scalars().first()
    )


def update_dataset(
    db: Session,
    *,
    dataset: Dataset,
    name: str | None,
    description: str | None,
    status: str | None,
) -> Dataset:
    if name is not None:
        dataset.name = name.strip()
    if description is not None:
        dataset.description = description
    if status is not None:
        dataset.status = status.strip()

    db.add(dataset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("Dataset name must be unique within organization") from exc
    db.refresh(dataset)
    return dataset


def list_projects(db: Session, *, org_id: str) -> list[Project]:
    return list(
        db.execute(select(Project).where(Project.org_id == org_id).order_by(Project.name.asc()))
        .scalars()
        .all()
    )


def create_project(
    db: Session,
    *,
    org_id: str,
    name: str,
    code: str,
    description: str | None,
    status: str,
) -> Project:
    project = Project(
        org_id=org_id,
        name=name.strip(),
        code=code.strip(),
        description=description,
        status=status.strip(),
    )
    db.add(project)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("Project name/code must be unique within organization") from exc
    db.refresh(project)
    return project


def get_project(db: Session, *, org_id: str, project_id: str) -> Project | None:
    return (
        db.execute(select(Project).where(Project.id == project_id, Project.org_id == org_id)).scalars().first()
    )


def update_project(
    db: Session,
    *,
    project: Project,
    name: str | None,
    code: str | None,
    description: str | None,
    status: str | None,
) -> Project:
    if name is not None:
        project.name = name.strip()
    if code is not None:
        project.code = code.strip()
    if description is not None:
        project.description = description
    if status is not None:
        project.status = status.strip()

    db.add(project)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("Project name/code must be unique within organization") from exc
    db.refresh(project)
    return project


def list_project_members(db: Session, *, org_id: str, project_id: str) -> list[ProjectMember]:
    return list(
        db.execute(
            select(ProjectMember)
            .join(Project, ProjectMember.project_id == Project.id)
            .where(Project.id == project_id, Project.org_id == org_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.created_at.asc())
        )
        .scalars()
        .all()
    )


def add_project_member(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    user_id: str,
    role_in_project: str,
    can_edit: bool,
) -> ProjectMember | None:
    project = get_project(db, org_id=org_id, project_id=project_id)
    if not project:
        return None

    user = db.execute(select(User).where(User.id == user_id, User.org_id == org_id)).scalars().first()
    if not user:
        return None

    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role_in_project=role_in_project.strip(),
        can_edit=can_edit,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("User is already a member of this project") from exc

    db.refresh(member)
    return member


def update_project_member(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    member_id: str,
    role_in_project: str | None,
    can_edit: bool | None,
) -> ProjectMember | None:
    member = (
        db.execute(
            select(ProjectMember)
            .join(Project, ProjectMember.project_id == Project.id)
            .where(ProjectMember.id == member_id, ProjectMember.project_id == project_id, Project.org_id == org_id)
            .options(selectinload(ProjectMember.user))
        )
        .scalars()
        .first()
    )
    if not member:
        return None

    if role_in_project is not None:
        member.role_in_project = role_in_project.strip()
    if can_edit is not None:
        member.can_edit = can_edit

    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_project_member(db: Session, *, org_id: str, project_id: str, member_id: str) -> bool:
    member = (
        db.execute(
            select(ProjectMember)
            .join(Project, ProjectMember.project_id == Project.id)
            .where(ProjectMember.id == member_id, ProjectMember.project_id == project_id, Project.org_id == org_id)
        )
        .scalars()
        .first()
    )
    if not member:
        return False

    db.delete(member)
    db.commit()
    return True


def list_project_datasets(db: Session, *, org_id: str, project_id: str) -> list[ProjectDataset]:
    return list(
        db.execute(
            select(ProjectDataset)
            .join(Project, ProjectDataset.project_id == Project.id)
            .join(Dataset, ProjectDataset.dataset_id == Dataset.id)
            .where(Project.id == project_id, Project.org_id == org_id)
            .options(selectinload(ProjectDataset.dataset))
            .order_by(ProjectDataset.created_at.asc())
        )
        .scalars()
        .all()
    )


def link_dataset_to_project(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    dataset_id: str,
) -> ProjectDataset | None:
    project = get_project(db, org_id=org_id, project_id=project_id)
    dataset = get_dataset(db, org_id=org_id, dataset_id=dataset_id)
    if not project or not dataset:
        return None

    link = ProjectDataset(project_id=project_id, dataset_id=dataset_id)
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GovernanceConflictError("Dataset is already linked to this project") from exc

    db.refresh(link)
    return (
        db.execute(select(ProjectDataset).where(ProjectDataset.id == link.id).options(selectinload(ProjectDataset.dataset)))
        .scalars()
        .one()
    )


def unlink_dataset_from_project(db: Session, *, org_id: str, project_id: str, dataset_id: str) -> bool:
    link = (
        db.execute(
            select(ProjectDataset)
            .join(Project, ProjectDataset.project_id == Project.id)
            .join(Dataset, ProjectDataset.dataset_id == Dataset.id)
            .where(
                Project.id == project_id,
                Project.org_id == org_id,
                Dataset.id == dataset_id,
                Dataset.org_id == org_id,
            )
        )
        .scalars()
        .first()
    )
    if not link:
        return False

    db.delete(link)
    db.commit()
    return True


def list_attractions(db: Session, *, org_id: str, dataset_id: str) -> list[Attraction]:
    return list(
        db.execute(
            select(Attraction)
            .where(Attraction.org_id == org_id, Attraction.dataset_id == dataset_id)
            .order_by(Attraction.name.asc(), Attraction.city.asc(), Attraction.state.asc())
        )
        .scalars()
        .all()
    )


def get_attraction(db: Session, *, org_id: str, dataset_id: str, attraction_id: str) -> Attraction | None:
    return (
        db.execute(
            select(Attraction).where(
                Attraction.id == attraction_id,
                Attraction.org_id == org_id,
                Attraction.dataset_id == dataset_id,
            )
        )
        .scalars()
        .first()
    )


def create_attraction(
    db: Session,
    *,
    org_id: str,
    dataset_id: str,
    name: str,
    city: str,
    state: str,
    description: str | None,
    latitude: float,
    longitude: float,
    duration_minutes: int,
    status: str,
) -> Attraction:
    attraction = Attraction(
        org_id=org_id,
        dataset_id=dataset_id,
        name=name.strip(),
        city=city.strip(),
        state=state.strip(),
        description=description,
        latitude=latitude,
        longitude=longitude,
        duration_minutes=duration_minutes,
        status=status.strip(),
        normalized_dedupe_key=normalize_attraction_key(name=name, city=city, state=state),
    )
    db.add(attraction)
    db.commit()
    db.refresh(attraction)
    return attraction


def update_attraction(
    db: Session,
    *,
    attraction: Attraction,
    name: str | None,
    city: str | None,
    state: str | None,
    description: str | None,
    latitude: float | None,
    longitude: float | None,
    duration_minutes: int | None,
    status: str | None,
) -> Attraction:
    if attraction.merged_into_attraction_id:
        raise GovernanceMergeConflictError("Merged attractions cannot be edited")

    if name is not None:
        attraction.name = name.strip()
    if city is not None:
        attraction.city = city.strip()
    if state is not None:
        attraction.state = state.strip()
    if description is not None:
        attraction.description = description
    if latitude is not None:
        attraction.latitude = latitude
    if longitude is not None:
        attraction.longitude = longitude
    if duration_minutes is not None:
        attraction.duration_minutes = duration_minutes
    if status is not None:
        attraction.status = status.strip()

    attraction.normalized_dedupe_key = normalize_attraction_key(
        name=attraction.name,
        city=attraction.city,
        state=attraction.state,
    )
    db.add(attraction)
    db.commit()
    db.refresh(attraction)
    return attraction


def list_attraction_duplicate_groups(
    db: Session,
    *,
    org_id: str,
    dataset_id: str,
) -> list[tuple[str, list[Attraction]]]:
    duplicate_keys = [
        row[0]
        for row in db.execute(
            select(Attraction.normalized_dedupe_key)
            .where(
                Attraction.org_id == org_id,
                Attraction.dataset_id == dataset_id,
                Attraction.merged_into_attraction_id.is_(None),
            )
            .group_by(Attraction.normalized_dedupe_key)
            .having(func.count(Attraction.id) > 1)
        )
        .all()
    ]
    if not duplicate_keys:
        return []

    rows = list(
        db.execute(
            select(Attraction)
            .where(
                Attraction.org_id == org_id,
                Attraction.dataset_id == dataset_id,
                Attraction.merged_into_attraction_id.is_(None),
                Attraction.normalized_dedupe_key.in_(duplicate_keys),
            )
            .order_by(Attraction.normalized_dedupe_key.asc(), Attraction.created_at.asc())
        )
        .scalars()
        .all()
    )

    grouped: dict[str, list[Attraction]] = defaultdict(list)
    for row in rows:
        grouped[row.normalized_dedupe_key].append(row)

    return [(key, grouped[key]) for key in sorted(grouped.keys())]


def merge_attractions(
    db: Session,
    *,
    org_id: str,
    dataset_id: str,
    source_attraction_id: str,
    target_attraction_id: str,
    merged_by_user_id: str,
    merge_reason: str | None,
) -> AttractionMergeEvent | None:
    if source_attraction_id == target_attraction_id:
        raise GovernanceValidationError("Source and target attractions must differ")

    source = get_attraction(
        db,
        org_id=org_id,
        dataset_id=dataset_id,
        attraction_id=source_attraction_id,
    )
    target = get_attraction(
        db,
        org_id=org_id,
        dataset_id=dataset_id,
        attraction_id=target_attraction_id,
    )
    if not source or not target:
        return None

    if source.merged_into_attraction_id:
        raise GovernanceMergeConflictError("Source attraction was already merged")
    if target.merged_into_attraction_id:
        raise GovernanceMergeConflictError("Target attraction is already merged")

    if source.normalized_dedupe_key != target.normalized_dedupe_key:
        raise GovernanceValidationError("Attractions do not share the same deterministic duplicate key")

    source_snapshot = {
        "id": source.id,
        "name": source.name,
        "city": source.city,
        "state": source.state,
        "description": source.description,
        "latitude": source.latitude,
        "longitude": source.longitude,
        "duration_minutes": source.duration_minutes,
        "status": source.status,
        "normalized_dedupe_key": source.normalized_dedupe_key,
    }
    target_snapshot = {
        "id": target.id,
        "name": target.name,
        "city": target.city,
        "state": target.state,
        "description": target.description,
        "latitude": target.latitude,
        "longitude": target.longitude,
        "duration_minutes": target.duration_minutes,
        "status": target.status,
        "normalized_dedupe_key": target.normalized_dedupe_key,
    }

    merged_at = datetime.now(tz=UTC)
    source.merged_into_attraction_id = target.id
    source.merged_at = merged_at
    source.status = "merged"

    merge_event = AttractionMergeEvent(
        org_id=org_id,
        dataset_id=dataset_id,
        source_attraction_id=source.id,
        target_attraction_id=target.id,
        merged_by_user_id=merged_by_user_id,
        merge_reason=merge_reason,
        source_snapshot=source_snapshot,
        target_snapshot=target_snapshot,
    )
    db.add(source)
    db.add(merge_event)
    db.commit()
    db.refresh(merge_event)
    return merge_event
