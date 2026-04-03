from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utcnow
from app.models.operations import LineageEvent


def record_lineage_event(
    db: Session,
    *,
    org_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    payload: dict,
    created_by_user_id: str | None,
    project_id: str | None = None,
    dataset_id: str | None = None,
    itinerary_id: str | None = None,
) -> LineageEvent:
    row = LineageEvent(
        org_id=org_id,
        project_id=project_id,
        dataset_id=dataset_id,
        itinerary_id=itinerary_id,
        created_by_user_id=created_by_user_id,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        occurred_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_lineage_events(
    db: Session,
    *,
    org_id: str,
    limit: int,
    project_id: str | None,
    dataset_id: str | None,
    itinerary_id: str | None,
    event_type: str | None,
) -> list[LineageEvent]:
    query = select(LineageEvent).where(LineageEvent.org_id == org_id)
    if project_id:
        query = query.where(LineageEvent.project_id == project_id)
    if dataset_id:
        query = query.where(LineageEvent.dataset_id == dataset_id)
    if itinerary_id:
        query = query.where(LineageEvent.itinerary_id == itinerary_id)
    if event_type:
        query = query.where(LineageEvent.event_type == event_type)

    clamped_limit = max(1, min(limit, 500))
    return list(db.execute(query.order_by(LineageEvent.occurred_at.desc()).limit(clamped_limit)).scalars().all())
