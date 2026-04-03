from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_datasets_org_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    project_links: Mapped[list["ProjectDataset"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    attractions: Mapped[list["Attraction"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_projects_org_name"),
        UniqueConstraint("org_id", "code", name="uq_projects_org_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")

    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    dataset_links: Mapped[list["ProjectDataset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_in_project: Mapped[str] = mapped_column(String(60), nullable=False)
    can_edit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class ProjectDataset(Base, TimestampMixin):
    __tablename__ = "project_datasets"
    __table_args__ = (UniqueConstraint("project_id", "dataset_id", name="uq_project_datasets_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="dataset_links")
    dataset: Mapped["Dataset"] = relationship(back_populates="project_links")


class Attraction(Base, TimestampMixin):
    __tablename__ = "attractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    normalized_dedupe_key: Mapped[str] = mapped_column(String(420), nullable=False)
    merged_into_attraction_id: Mapped[str | None] = mapped_column(
        ForeignKey("attractions.id", ondelete="SET NULL"), nullable=True
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="attractions")
    merged_into_attraction: Mapped["Attraction | None"] = relationship(remote_side=[id])


class AttractionMergeEvent(Base, TimestampMixin):
    __tablename__ = "attraction_merge_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    source_attraction_id: Mapped[str] = mapped_column(
        ForeignKey("attractions.id", ondelete="CASCADE"), nullable=False
    )
    target_attraction_id: Mapped[str] = mapped_column(
        ForeignKey("attractions.id", ondelete="CASCADE"), nullable=False
    )
    merged_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    merge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    target_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
