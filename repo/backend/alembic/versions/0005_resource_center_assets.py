"""add resource center assets and metadata

Revision ID: 0005_resource_center_assets
Revises: 0004_planner_core
Create Date: 2026-04-03 11:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_resource_center_assets"
down_revision: Union[str, Sequence[str], None] = "0004_planner_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        single_reference_expr = (
            "(CASE WHEN attraction_id IS NOT NULL THEN 1 ELSE 0 END"
            " + CASE WHEN itinerary_id IS NOT NULL THEN 1 ELSE 0 END) <= 1"
        )
    else:
        single_reference_expr = "((attraction_id IS NOT NULL)::int + (itinerary_id IS NOT NULL)::int) <= 1"

    op.create_table(
        "resource_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("attraction_id", sa.String(length=36), nullable=True),
        sa.Column("itinerary_id", sa.String(length=36), nullable=True),
        sa.Column("original_file_name", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=10), nullable=False),
        sa.Column("declared_mime_type", sa.String(length=160), nullable=True),
        sa.Column("detected_mime_type", sa.String(length=160), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("preview_kind", sa.String(length=20), nullable=False),
        sa.Column("is_quarantined", sa.Boolean(), nullable=False),
        sa.Column("quarantine_reason", sa.Text(), nullable=True),
        sa.Column("scan_status", sa.String(length=30), nullable=False),
        sa.Column("scan_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleanup_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_resource_assets_size_non_negative"),
        sa.CheckConstraint(
            single_reference_expr,
            name="ck_resource_assets_single_reference",
        ),
        sa.CheckConstraint(
            "(scope_type = 'attraction' AND attraction_id IS NOT NULL AND itinerary_id IS NULL)"
            " OR (scope_type = 'itinerary' AND itinerary_id IS NOT NULL AND attraction_id IS NULL)"
            " OR (attraction_id IS NULL AND itinerary_id IS NULL)",
            name="ck_resource_assets_scope_reference_alignment",
        ),
        sa.ForeignKeyConstraint(["attraction_id"], ["attractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resource_assets")),
        sa.UniqueConstraint("storage_key", name="uq_resource_assets_storage_key"),
    )
    op.create_index("ix_resource_assets_org_project", "resource_assets", ["org_id", "project_id"], unique=False)
    op.create_index(
        "ix_resource_assets_scope_reference",
        "resource_assets",
        ["project_id", "scope_type", "attraction_id", "itinerary_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_resource_assets_scope_reference", table_name="resource_assets")
    op.drop_index("ix_resource_assets_org_project", table_name="resource_assets")
    op.drop_table("resource_assets")
