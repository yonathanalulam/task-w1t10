"""add planner core itinerary workflow tables

Revision ID: 0004_planner_core
Revises: 0003_attraction_catalog
Create Date: 2026-04-03 00:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_planner_core"
down_revision: Union[str, Sequence[str], None] = "0003_attraction_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("default_urban_speed_mph", sa.Float(), nullable=False, server_default=sa.text("25")),
    )
    op.add_column(
        "organizations",
        sa.Column("default_highway_speed_mph", sa.Float(), nullable=False, server_default=sa.text("55")),
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.alter_column("default_urban_speed_mph", server_default=None)
            batch_op.alter_column("default_highway_speed_mph", server_default=None)
    else:
        op.alter_column("organizations", "default_urban_speed_mph", server_default=None)
        op.alter_column("organizations", "default_highway_speed_mph", server_default=None)

    op.create_table(
        "itineraries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("assigned_planner_user_id", sa.String(length=36), nullable=True),
        sa.Column("urban_speed_mph_override", sa.Float(), nullable=True),
        sa.Column("highway_speed_mph_override", sa.Float(), nullable=True),
        sa.Column("version_counter", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "urban_speed_mph_override IS NULL OR urban_speed_mph_override > 0",
            name="ck_itineraries_urban_speed_positive",
        ),
        sa.CheckConstraint(
            "highway_speed_mph_override IS NULL OR highway_speed_mph_override > 0",
            name="ck_itineraries_highway_speed_positive",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_planner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_itineraries")),
        sa.UniqueConstraint("project_id", "name", name="uq_itineraries_project_name"),
    )
    op.create_index("ix_itineraries_org_project", "itineraries", ["org_id", "project_id"], unique=False)

    op.create_table(
        "itinerary_days",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("itinerary_id", sa.String(length=36), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("urban_speed_mph_override", sa.Float(), nullable=True),
        sa.Column("highway_speed_mph_override", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "urban_speed_mph_override IS NULL OR urban_speed_mph_override > 0",
            name="ck_itinerary_days_urban_speed_positive",
        ),
        sa.CheckConstraint(
            "highway_speed_mph_override IS NULL OR highway_speed_mph_override > 0",
            name="ck_itinerary_days_highway_speed_positive",
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_itinerary_days")),
        sa.UniqueConstraint("itinerary_id", "day_number", name="uq_itinerary_days_day_number"),
    )

    op.create_table(
        "itinerary_stops",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("itinerary_day_id", sa.String(length=36), nullable=False),
        sa.Column("attraction_id", sa.String(length=36), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("start_minute_of_day", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "start_minute_of_day >= 0 AND start_minute_of_day <= 1439",
            name="ck_itinerary_stops_start_range",
        ),
        sa.CheckConstraint(
            "duration_minutes >= 5 AND duration_minutes <= 720",
            name="ck_itinerary_stops_duration_range",
        ),
        sa.ForeignKeyConstraint(["itinerary_day_id"], ["itinerary_days.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attraction_id"], ["attractions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_itinerary_stops")),
        sa.UniqueConstraint("itinerary_day_id", "order_index", name="uq_itinerary_stops_order_index"),
    )

    op.create_table(
        "itinerary_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("itinerary_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.String(length=255), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_itinerary_versions")),
        sa.UniqueConstraint("itinerary_id", "version_number", name="uq_itinerary_versions_number"),
    )
    op.create_index(
        "ix_itinerary_versions_itinerary_number",
        "itinerary_versions",
        ["itinerary_id", "version_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_itinerary_versions_itinerary_number", table_name="itinerary_versions")
    op.drop_table("itinerary_versions")
    op.drop_table("itinerary_stops")
    op.drop_table("itinerary_days")
    op.drop_index("ix_itineraries_org_project", table_name="itineraries")
    op.drop_table("itineraries")

    op.drop_column("organizations", "default_highway_speed_mph")
    op.drop_column("organizations", "default_urban_speed_mph")
