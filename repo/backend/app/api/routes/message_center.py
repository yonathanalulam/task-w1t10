from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_dep, planner_csrf_session_dep, planner_session_dep
from app.models.auth import Session as AuthSession
from app.schemas.message_center import (
    MessageDispatchOut,
    MessageDeliveryAttemptOut,
    MessagePreviewOut,
    MessagePreviewRequest,
    MessageSendRequest,
    MessageTemplateCreateRequest,
    MessageTemplateOut,
    MessageTemplateUpdateRequest,
)
from app.services.message_center import (
    MessageCenterAuthorizationError,
    MessageCenterConflictError,
    MessageCenterValidationError,
    create_template,
    extract_template_variables,
    get_template_preview,
    list_message_timeline,
    list_templates,
    send_message,
    update_template,
)
from app.services.audit import record_audit_event

router = APIRouter(tags=["message_center"])


def _template_out(row) -> MessageTemplateOut:
    return MessageTemplateOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        category=row.category,
        channel=row.channel,
        body_template=row.body_template,
        variables=extract_template_variables(row.body_template),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _dispatch_out(row) -> MessageDispatchOut:
    return MessageDispatchOut(
        id=row.id,
        project_id=row.project_id,
        itinerary_id=row.itinerary_id,
        template_id=row.template_id,
        template_name=row.template_name,
        template_category=row.template_category,
        channel=row.channel,
        recipient_user_id=row.recipient_user_id,
        recipient_display_name=row.recipient_display_name,
        rendered_body=row.rendered_body,
        send_status=row.send_status,
        variables_payload=row.variables_payload,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        attempts=[
            MessageDeliveryAttemptOut(
                id=attempt.id,
                connector_key=attempt.connector_key,
                attempt_status=attempt.attempt_status,
                provider_message_id=attempt.provider_message_id,
                detail=attempt.detail,
                response_payload=attempt.response_payload,
                attempted_at=attempt.attempted_at,
            )
            for attempt in row.delivery_attempts
        ],
    )


@router.get("/projects/{project_id}/message-center/templates", response_model=list[MessageTemplateOut])
def project_message_templates(
    project_id: str,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[MessageTemplateOut]:
    rows = list_templates(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        user=auth_session.user,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [_template_out(row) for row in rows]


@router.post("/projects/{project_id}/message-center/templates", response_model=MessageTemplateOut, status_code=status.HTTP_201_CREATED)
def project_message_templates_create(
    project_id: str,
    payload: MessageTemplateCreateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> MessageTemplateOut:
    try:
        row = create_template(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            user=auth_session.user,
            name=payload.name,
            category=payload.category,
            channel=payload.channel,
            body_template=payload.body_template,
            is_active=payload.is_active,
        )
    except MessageCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MessageCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MessageCenterConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="message_center.template_create",
        resource_type="message_template",
        resource_id=row.id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/message-center/templates",
        status_code=201,
        project_id=project_id,
        detail_summary="Created message template",
        metadata_json={"channel": row.channel, "category": row.category},
    )
    return _template_out(row)


@router.patch("/projects/{project_id}/message-center/templates/{template_id}", response_model=MessageTemplateOut)
def project_message_templates_update(
    project_id: str,
    template_id: str,
    payload: MessageTemplateUpdateRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> MessageTemplateOut:
    try:
        row = update_template(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            template_id=template_id,
            user=auth_session.user,
            name=payload.name,
            category=payload.category,
            channel=payload.channel,
            body_template=payload.body_template,
            is_active=payload.is_active,
        )
    except MessageCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MessageCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MessageCenterConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="message_center.template_update",
        resource_type="message_template",
        resource_id=row.id,
        request_method="PATCH",
        request_path=f"/api/projects/{project_id}/message-center/templates/{template_id}",
        status_code=200,
        project_id=project_id,
        detail_summary="Updated message template",
        metadata_json={"channel": row.channel, "category": row.category, "is_active": row.is_active},
    )
    return _template_out(row)


@router.post("/projects/{project_id}/message-center/preview", response_model=MessagePreviewOut)
def project_message_preview(
    project_id: str,
    payload: MessagePreviewRequest,
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> MessagePreviewOut:
    try:
        rendered = get_template_preview(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            template_id=payload.template_id,
            user=auth_session.user,
            variables=payload.variables,
            itinerary_id=payload.itinerary_id,
        )
    except MessageCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MessageCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if rendered is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template scope not found")
    template, preview_body, missing, _itinerary, variables_used = rendered

    return MessagePreviewOut(
        template_id=template.id,
        rendered_body=preview_body,
        missing_variables=missing,
        variables_used=variables_used,
    )


@router.post("/projects/{project_id}/message-center/send", response_model=MessageDispatchOut)
def project_message_send(
    project_id: str,
    payload: MessageSendRequest,
    auth_session: AuthSession = Depends(planner_csrf_session_dep),
    db: Session = Depends(db_dep),
) -> MessageDispatchOut:
    try:
        row = send_message(
            db,
            org_id=auth_session.user.org_id,
            project_id=project_id,
            template_id=payload.template_id,
            recipient_user_id=payload.recipient_user_id,
            itinerary_id=payload.itinerary_id,
            variables=payload.variables,
            user=auth_session.user,
        )
    except MessageCenterAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except MessageCenterValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template scope not found")
    record_audit_event(
        db,
        org_id=auth_session.user.org_id,
        actor_user_id=auth_session.user_id,
        action_type="message_center.message_send",
        resource_type="message_dispatch",
        resource_id=row.id,
        request_method="POST",
        request_path=f"/api/projects/{project_id}/message-center/send",
        status_code=200,
        project_id=project_id,
        detail_summary="Dispatched message from template",
        metadata_json={
            "template_id": row.template_id,
            "template_category": row.template_category,
            "send_status": row.send_status,
            "recipient_user_id": row.recipient_user_id,
        },
    )
    return _dispatch_out(row)


@router.get("/projects/{project_id}/message-center/timeline", response_model=list[MessageDispatchOut])
def project_message_timeline(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    auth_session: AuthSession = Depends(planner_session_dep),
    db: Session = Depends(db_dep),
) -> list[MessageDispatchOut]:
    rows = list_message_timeline(
        db,
        org_id=auth_session.user.org_id,
        project_id=project_id,
        user=auth_session.user,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return [_dispatch_out(row) for row in rows]
