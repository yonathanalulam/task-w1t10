from datetime import datetime

from pydantic import BaseModel, Field


class MessageTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=80)
    channel: str = Field(default="in_app", min_length=1, max_length=20)
    body_template: str = Field(min_length=1, max_length=20000)
    is_active: bool = True


class MessageTemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    channel: str | None = Field(default=None, min_length=1, max_length=20)
    body_template: str | None = Field(default=None, min_length=1, max_length=20000)
    is_active: bool | None = None


class MessageTemplateOut(BaseModel):
    id: str
    project_id: str
    name: str
    category: str
    channel: str
    body_template: str
    variables: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MessagePreviewRequest(BaseModel):
    template_id: str
    itinerary_id: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)


class MessagePreviewOut(BaseModel):
    template_id: str
    rendered_body: str
    missing_variables: list[str]
    variables_used: dict[str, str]


class MessageSendRequest(BaseModel):
    template_id: str
    recipient_user_id: str = Field(min_length=1, max_length=180)
    itinerary_id: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)


class MessageDeliveryAttemptOut(BaseModel):
    id: str
    connector_key: str
    attempt_status: str
    provider_message_id: str | None
    detail: str | None
    response_payload: dict | None
    attempted_at: datetime


class MessageDispatchOut(BaseModel):
    id: str
    project_id: str
    itinerary_id: str | None
    template_id: str | None
    template_name: str
    template_category: str
    channel: str
    recipient_user_id: str
    recipient_display_name: str | None
    rendered_body: str
    send_status: str
    variables_payload: dict[str, str]
    created_by_user_id: str
    created_at: datetime
    attempts: list[MessageDeliveryAttemptOut]
