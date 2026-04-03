from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.governance import Project
    from app.models.planner import Itinerary
    from app.models.user import User


class MessageTemplate(Base, TimestampMixin):
    __tablename__ = "message_templates"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_message_templates_project_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    updated_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    project: Mapped["Project"] = relationship()
    created_by_user: Mapped["User"] = relationship(foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User"] = relationship(foreign_keys=[updated_by_user_id])


class MessageDispatch(Base, TimestampMixin):
    __tablename__ = "message_dispatches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    itinerary_id: Mapped[str | None] = mapped_column(ForeignKey("itineraries.id", ondelete="SET NULL"), nullable=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True)
    template_name: Mapped[str] = mapped_column(String(180), nullable=False)
    template_category: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_user_id: Mapped[str] = mapped_column(String(180), nullable=False)
    recipient_display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    variables_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    rendered_body: Mapped[str] = mapped_column(Text, nullable=False)
    send_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    project: Mapped["Project"] = relationship()
    itinerary: Mapped["Itinerary | None"] = relationship()
    template: Mapped["MessageTemplate | None"] = relationship()
    created_by_user: Mapped["User"] = relationship()

    delivery_attempts: Mapped[list["MessageDeliveryAttempt"]] = relationship(
        back_populates="message_dispatch", cascade="all, delete-orphan", order_by="MessageDeliveryAttempt.attempted_at.desc()"
    )


class MessageDeliveryAttempt(Base, TimestampMixin):
    __tablename__ = "message_delivery_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    message_dispatch_id: Mapped[str] = mapped_column(
        ForeignKey("message_dispatches.id", ondelete="CASCADE"), nullable=False
    )
    connector_key: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt_status: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    message_dispatch: Mapped["MessageDispatch"] = relationship(back_populates="delivery_attempts")
