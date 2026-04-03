from __future__ import annotations

import re
from datetime import UTC, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.security import utcnow
from app.models.governance import Project, ProjectMember
from app.models.message_center import MessageDeliveryAttempt, MessageDispatch, MessageTemplate
from app.models.planner import Itinerary
from app.models.user import User
from app.services.message_delivery import MessageDeliveryRequest, build_default_connector_registry

TEMPLATE_VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
SUPPORTED_TEMPLATE_VARIABLES = {
    "traveler_name",
    "departure_time",
    "project_name",
    "project_code",
    "itinerary_name",
    "sender_username",
}
SUPPORTED_TEMPLATE_CHANNELS = {"in_app", "sms", "email", "push"}

DAILY_USER_CAP = 3
HOURLY_CATEGORY_CAP = 1


class MessageCenterValidationError(Exception):
    """Raised when message center request payload is semantically invalid."""


class MessageCenterAuthorizationError(Exception):
    """Raised when caller lacks required project/itinerary authority."""


class MessageCenterConflictError(Exception):
    """Raised when unique/message-center write conflicts happen."""


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
        raise MessageCenterAuthorizationError("Project membership is read-only")
    return project


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

    if (
        require_edit
        and itinerary.assigned_planner_user_id
        and itinerary.assigned_planner_user_id != user.id
        and not _is_org_admin(user)
    ):
        raise MessageCenterAuthorizationError("Itinerary is assigned to another planner")
    return itinerary


def extract_template_variables(template_body: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in TEMPLATE_VARIABLE_PATTERN.finditer(template_body):
        variable_name = match.group(1)
        if variable_name in seen:
            continue
        seen.add(variable_name)
        ordered.append(variable_name)
    return ordered


def _validate_template_channel(channel: str) -> str:
    normalized = channel.strip().lower()
    if normalized not in SUPPORTED_TEMPLATE_CHANNELS:
        allowed = ", ".join(sorted(SUPPORTED_TEMPLATE_CHANNELS))
        raise MessageCenterValidationError(f"Unsupported channel '{channel}'. Allowed channels: {allowed}")
    return normalized


def _validate_template_variables(template_body: str) -> list[str]:
    variables = extract_template_variables(template_body)
    unsupported = [name for name in variables if name not in SUPPORTED_TEMPLATE_VARIABLES]
    if unsupported:
        supported = ", ".join(sorted(SUPPORTED_TEMPLATE_VARIABLES))
        raise MessageCenterValidationError(
            f"Unsupported template variables: {', '.join(unsupported)}. Supported variables: {supported}"
        )
    return variables


def _normalized_variables(variables: dict[str, str] | None) -> dict[str, str]:
    if not variables:
        return {}
    normalized: dict[str, str] = {}
    for key, value in variables.items():
        if key not in SUPPORTED_TEMPLATE_VARIABLES:
            continue
        normalized[key] = str(value).strip()
    return normalized


def render_template_preview(*, template_body: str, variables: dict[str, str]) -> tuple[str, list[str]]:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = variables.get(key, "").strip()
        if not value:
            missing.add(key)
            return ""
        return value

    rendered = TEMPLATE_VARIABLE_PATTERN.sub(replace, template_body)
    return rendered, sorted(missing)


def _render_template_for_send(*, template_body: str, variables: dict[str, str]) -> tuple[str, list[str]]:
    rendered, missing = render_template_preview(template_body=template_body, variables=variables)
    return rendered, missing


def list_templates(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    user: User,
) -> list[MessageTemplate] | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None

    return list(
        db.execute(
            select(MessageTemplate)
            .where(MessageTemplate.org_id == org_id, MessageTemplate.project_id == project_id)
            .order_by(MessageTemplate.name.asc())
        )
        .scalars()
        .all()
    )


def create_template(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    user: User,
    name: str,
    category: str,
    channel: str,
    body_template: str,
    is_active: bool,
) -> MessageTemplate | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None

    normalized_name = name.strip()
    normalized_category = category.strip().lower()
    normalized_body = body_template.strip()
    if not normalized_name:
        raise MessageCenterValidationError("Template name is required")
    if not normalized_category:
        raise MessageCenterValidationError("Template category is required")
    if not normalized_body:
        raise MessageCenterValidationError("Template body is required")

    normalized_channel = _validate_template_channel(channel)
    _validate_template_variables(normalized_body)

    template = MessageTemplate(
        org_id=org_id,
        project_id=project_id,
        name=normalized_name,
        category=normalized_category,
        channel=normalized_channel,
        body_template=normalized_body,
        is_active=is_active,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(template)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise MessageCenterConflictError("Template name already exists for this project") from exc
    db.refresh(template)
    return template


def update_template(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    template_id: str,
    user: User,
    name: str | None,
    category: str | None,
    channel: str | None,
    body_template: str | None,
    is_active: bool | None,
) -> MessageTemplate | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None

    template = (
        db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.org_id == org_id,
                MessageTemplate.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )
    if not template:
        return None

    if name is not None:
        normalized_name = name.strip()
        if not normalized_name:
            raise MessageCenterValidationError("Template name cannot be blank")
        template.name = normalized_name
    if category is not None:
        normalized_category = category.strip().lower()
        if not normalized_category:
            raise MessageCenterValidationError("Template category cannot be blank")
        template.category = normalized_category
    if channel is not None:
        template.channel = _validate_template_channel(channel)
    if body_template is not None:
        normalized_body = body_template.strip()
        if not normalized_body:
            raise MessageCenterValidationError("Template body cannot be blank")
        _validate_template_variables(normalized_body)
        template.body_template = normalized_body
    if is_active is not None:
        template.is_active = is_active

    template.updated_by_user_id = user.id
    db.add(template)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise MessageCenterConflictError("Template name already exists for this project") from exc
    db.refresh(template)
    return template


def get_template_preview(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    template_id: str,
    user: User,
    variables: dict[str, str] | None,
    itinerary_id: str | None,
) -> tuple[MessageTemplate, str, list[str], Itinerary | None, dict[str, str]] | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None

    template = (
        db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.org_id == org_id,
                MessageTemplate.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )
    if not template:
        return None

    itinerary: Itinerary | None = None
    if itinerary_id:
        itinerary = _resolve_itinerary_scope(
            db,
            org_id=org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=user,
            require_edit=False,
        )
        if not itinerary:
            raise MessageCenterValidationError("Itinerary scope not found for this project")

    normalized = _normalized_variables(variables)
    normalized.setdefault("project_name", project.name)
    normalized.setdefault("project_code", project.code)
    normalized.setdefault("sender_username", user.username)
    if itinerary:
        normalized.setdefault("itinerary_name", itinerary.name)

    _validate_template_variables(template.body_template)
    rendered, missing = render_template_preview(template_body=template.body_template, variables=normalized)
    return template, rendered, missing, itinerary, normalized


def _enforce_frequency_caps(
    db: Session,
    *,
    org_id: str,
    recipient_user_id: str,
    template_category: str,
    now,
) -> None:
    day_start = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    daily_count = (
        db.execute(
            select(func.count(MessageDispatch.id)).where(
                MessageDispatch.org_id == org_id,
                MessageDispatch.recipient_user_id == recipient_user_id,
                MessageDispatch.created_at >= day_start,
                MessageDispatch.created_at < day_end,
            )
        )
        .scalars()
        .one()
    )
    if daily_count >= DAILY_USER_CAP:
        raise MessageCenterValidationError("Daily frequency cap reached: max 3 messages per user per day")

    hourly_cutoff = now - timedelta(hours=1)
    hourly_count = (
        db.execute(
            select(func.count(MessageDispatch.id)).where(
                MessageDispatch.org_id == org_id,
                MessageDispatch.recipient_user_id == recipient_user_id,
                MessageDispatch.template_category == template_category,
                MessageDispatch.created_at >= hourly_cutoff,
            )
        )
        .scalars()
        .one()
    )
    if hourly_count >= HOURLY_CATEGORY_CAP:
        raise MessageCenterValidationError("Hourly category cap reached: max 1 message per hour for this template category")


def send_message(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    template_id: str,
    recipient_user_id: str,
    itinerary_id: str | None,
    variables: dict[str, str] | None,
    user: User,
) -> MessageDispatch | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=True)
    if not project:
        return None

    template = (
        db.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.org_id == org_id,
                MessageTemplate.project_id == project_id,
            )
        )
        .scalars()
        .first()
    )
    if not template:
        return None
    if not template.is_active:
        raise MessageCenterValidationError("Template is inactive")

    itinerary: Itinerary | None = None
    if itinerary_id:
        itinerary = _resolve_itinerary_scope(
            db,
            org_id=org_id,
            project_id=project_id,
            itinerary_id=itinerary_id,
            user=user,
            require_edit=True,
        )
        if not itinerary:
            raise MessageCenterValidationError("Itinerary scope not found for this project")

    normalized_recipient = recipient_user_id.strip()
    if not normalized_recipient:
        raise MessageCenterValidationError("Recipient user id is required")

    normalized = _normalized_variables(variables)
    normalized.setdefault("project_name", project.name)
    normalized.setdefault("project_code", project.code)
    normalized.setdefault("sender_username", user.username)
    if itinerary:
        normalized.setdefault("itinerary_name", itinerary.name)

    _validate_template_variables(template.body_template)
    rendered_body, missing = _render_template_for_send(template_body=template.body_template, variables=normalized)
    if missing:
        raise MessageCenterValidationError(
            f"Missing template variables for send: {', '.join(missing)}"
        )

    now = utcnow()
    _enforce_frequency_caps(
        db,
        org_id=org_id,
        recipient_user_id=normalized_recipient,
        template_category=template.category,
        now=now,
    )

    dispatch = MessageDispatch(
        org_id=org_id,
        project_id=project_id,
        itinerary_id=itinerary.id if itinerary else None,
        template_id=template.id,
        template_name=template.name,
        template_category=template.category,
        channel=template.channel,
        recipient_user_id=normalized_recipient,
        recipient_display_name=normalized.get("traveler_name") or None,
        variables_payload=normalized,
        rendered_body=rendered_body,
        send_status="pending",
        created_by_user_id=user.id,
    )
    db.add(dispatch)
    db.flush()

    connectors = build_default_connector_registry()
    connector = connectors.get(template.channel)
    if not connector:
        raise MessageCenterValidationError(f"No connector registered for channel '{template.channel}'")

    delivery_result = connector.deliver(
        MessageDeliveryRequest(
            message_dispatch_id=dispatch.id,
            channel=template.channel,
            recipient_user_id=normalized_recipient,
            rendered_body=rendered_body,
            variables=normalized,
        )
    )

    dispatch.send_status = delivery_result.status
    attempt = MessageDeliveryAttempt(
        org_id=org_id,
        project_id=project_id,
        message_dispatch_id=dispatch.id,
        connector_key=delivery_result.connector_key,
        attempt_status=delivery_result.status,
        provider_message_id=delivery_result.provider_message_id,
        detail=delivery_result.detail,
        response_payload=delivery_result.response_payload,
        attempted_at=now,
    )
    db.add(dispatch)
    db.add(attempt)
    db.commit()

    hydrated = (
        db.execute(
            select(MessageDispatch)
            .where(MessageDispatch.id == dispatch.id)
            .options(selectinload(MessageDispatch.delivery_attempts))
        )
        .scalars()
        .first()
    )
    if not hydrated:
        raise MessageCenterValidationError("Message send could not be loaded after persistence")
    return hydrated


def list_message_timeline(
    db: Session,
    *,
    org_id: str,
    project_id: str,
    user: User,
    limit: int,
) -> list[MessageDispatch] | None:
    project = _project_for_user(db, org_id=org_id, project_id=project_id, user=user, require_edit=False)
    if not project:
        return None

    clamped_limit = max(1, min(limit, 200))
    return list(
        db.execute(
            select(MessageDispatch)
            .where(MessageDispatch.org_id == org_id, MessageDispatch.project_id == project_id)
            .options(selectinload(MessageDispatch.delivery_attempts))
            .order_by(MessageDispatch.created_at.desc())
            .limit(clamped_limit)
        )
        .scalars()
        .all()
    )
