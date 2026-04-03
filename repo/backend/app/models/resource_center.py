from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.governance import Attraction, Project
    from app.models.planner import Itinerary
    from app.models.user import User


class ResourceAsset(Base, TimestampMixin):
    __tablename__ = "resource_assets"
    __table_args__ = (
        CheckConstraint("file_size_bytes >= 0", name="ck_resource_assets_size_non_negative"),
        CheckConstraint(
            "((attraction_id IS NOT NULL)::int + (itinerary_id IS NOT NULL)::int) <= 1",
            name="ck_resource_assets_single_reference",
        ),
        CheckConstraint(
            "(scope_type = 'attraction' AND attraction_id IS NOT NULL AND itinerary_id IS NULL)"
            " OR (scope_type = 'itinerary' AND itinerary_id IS NOT NULL AND attraction_id IS NULL)"
            " OR (attraction_id IS NULL AND itinerary_id IS NULL)",
            name="ck_resource_assets_scope_reference_alignment",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    attraction_id: Mapped[str | None] = mapped_column(ForeignKey("attractions.id", ondelete="SET NULL"), nullable=True)
    itinerary_id: Mapped[str | None] = mapped_column(ForeignKey("itineraries.id", ondelete="SET NULL"), nullable=True)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    declared_mime_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    detected_mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    preview_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    scan_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scan_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleanup_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    project: Mapped["Project"] = relationship()
    attraction: Mapped["Attraction | None"] = relationship()
    itinerary: Mapped["Itinerary | None"] = relationship()
    created_by_user: Mapped["User"] = relationship()
