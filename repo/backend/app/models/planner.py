from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.governance import Attraction, Project
    from app.models.user import User


class Itinerary(Base, TimestampMixin):
    __tablename__ = "itineraries"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_itineraries_project_name"),
        CheckConstraint(
            "urban_speed_mph_override IS NULL OR urban_speed_mph_override > 0",
            name="ck_itineraries_urban_speed_positive",
        ),
        CheckConstraint(
            "highway_speed_mph_override IS NULL OR highway_speed_mph_override > 0",
            name="ck_itineraries_highway_speed_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    assigned_planner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    urban_speed_mph_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    highway_speed_mph_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    version_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    updated_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    project: Mapped["Project"] = relationship()
    assigned_planner: Mapped["User | None"] = relationship(foreign_keys=[assigned_planner_user_id])
    created_by_user: Mapped["User"] = relationship(foreign_keys=[created_by_user_id])
    updated_by_user: Mapped["User"] = relationship(foreign_keys=[updated_by_user_id])

    days: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="itinerary", cascade="all, delete-orphan", order_by="ItineraryDay.day_number"
    )
    versions: Mapped[list["ItineraryVersion"]] = relationship(
        back_populates="itinerary", cascade="all, delete-orphan", order_by="ItineraryVersion.version_number"
    )


class ItineraryDay(Base, TimestampMixin):
    __tablename__ = "itinerary_days"
    __table_args__ = (
        UniqueConstraint("itinerary_id", "day_number", name="uq_itinerary_days_day_number"),
        CheckConstraint(
            "urban_speed_mph_override IS NULL OR urban_speed_mph_override > 0",
            name="ck_itinerary_days_urban_speed_positive",
        ),
        CheckConstraint(
            "highway_speed_mph_override IS NULL OR highway_speed_mph_override > 0",
            name="ck_itinerary_days_highway_speed_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    itinerary_id: Mapped[str] = mapped_column(ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    urban_speed_mph_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    highway_speed_mph_override: Mapped[float | None] = mapped_column(Float, nullable=True)

    itinerary: Mapped["Itinerary"] = relationship(back_populates="days")
    stops: Mapped[list["ItineraryStop"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="ItineraryStop.order_index"
    )


class ItineraryStop(Base, TimestampMixin):
    __tablename__ = "itinerary_stops"
    __table_args__ = (
        UniqueConstraint("itinerary_day_id", "order_index", name="uq_itinerary_stops_order_index"),
        CheckConstraint(
            "start_minute_of_day >= 0 AND start_minute_of_day <= 1439",
            name="ck_itinerary_stops_start_range",
        ),
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 720", name="ck_itinerary_stops_duration_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    itinerary_day_id: Mapped[str] = mapped_column(
        ForeignKey("itinerary_days.id", ondelete="CASCADE"), nullable=False
    )
    attraction_id: Mapped[str] = mapped_column(ForeignKey("attractions.id", ondelete="RESTRICT"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_minute_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    day: Mapped["ItineraryDay"] = relationship(back_populates="stops")
    attraction: Mapped["Attraction"] = relationship()


class ItineraryVersion(Base, TimestampMixin):
    __tablename__ = "itinerary_versions"
    __table_args__ = (UniqueConstraint("itinerary_id", "version_number", name="uq_itinerary_versions_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    itinerary_id: Mapped[str] = mapped_column(ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    itinerary: Mapped["Itinerary"] = relationship(back_populates="versions")
    created_by_user: Mapped["User"] = relationship()
