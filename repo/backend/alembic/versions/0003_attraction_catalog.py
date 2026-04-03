"""add governed attraction catalog and merge history

Revision ID: 0003_attraction_catalog
Revises: 0002_governance_surfaces
Create Date: 2026-04-02 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_attraction_catalog"
down_revision: Union[str, Sequence[str], None] = "0002_governance_surfaces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("normalized_dedupe_key", sa.String(length=420), nullable=False),
        sa.Column("merged_into_attraction_id", sa.String(length=36), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 720", name="ck_attractions_duration_range"),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_attractions_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_attraction_id"],
            ["attractions.id"],
            name=op.f("fk_attractions_merged_into_attraction_id_attractions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_attractions_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attractions")),
    )
    op.create_index("ix_attractions_org_dataset", "attractions", ["org_id", "dataset_id"], unique=False)
    op.create_index("ix_attractions_dedupe_key", "attractions", ["normalized_dedupe_key"], unique=False)

    op.create_table(
        "attraction_merge_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("source_attraction_id", sa.String(length=36), nullable=False),
        sa.Column("target_attraction_id", sa.String(length=36), nullable=False),
        sa.Column("merged_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("merge_reason", sa.Text(), nullable=True),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("target_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_attraction_merge_events_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merged_by_user_id"],
            ["users.id"],
            name=op.f("fk_attraction_merge_events_merged_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name=op.f("fk_attraction_merge_events_org_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_attraction_id"],
            ["attractions.id"],
            name=op.f("fk_attraction_merge_events_source_attraction_id_attractions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_attraction_id"],
            ["attractions.id"],
            name=op.f("fk_attraction_merge_events_target_attraction_id_attractions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attraction_merge_events")),
    )
    op.create_index(
        "ix_attraction_merge_events_org_dataset",
        "attraction_merge_events",
        ["org_id", "dataset_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attraction_merge_events_org_dataset", table_name="attraction_merge_events")
    op.drop_table("attraction_merge_events")
    op.drop_index("ix_attractions_dedupe_key", table_name="attractions")
    op.drop_index("ix_attractions_org_dataset", table_name="attractions")
    op.drop_table("attractions")
