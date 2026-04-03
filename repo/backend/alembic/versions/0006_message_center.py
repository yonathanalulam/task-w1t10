"""add message center templates dispatches and attempts

Revision ID: 0006_message_center
Revises: 0005_resource_center_assets
Create Date: 2026-04-03 14:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_message_center"
down_revision: Union[str, Sequence[str], None] = "0005_resource_center_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_templates")),
        sa.UniqueConstraint("project_id", "name", name="uq_message_templates_project_name"),
    )
    op.create_index(
        "ix_message_templates_project_active",
        "message_templates",
        ["project_id", "is_active", "name"],
        unique=False,
    )

    op.create_table(
        "message_dispatches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("itinerary_id", sa.String(length=36), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("template_name", sa.String(length=180), nullable=False),
        sa.Column("template_category", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=180), nullable=False),
        sa.Column("recipient_display_name", sa.String(length=180), nullable=True),
        sa.Column("variables_payload", sa.JSON(), nullable=False),
        sa.Column("rendered_body", sa.Text(), nullable=False),
        sa.Column("send_status", sa.String(length=30), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["message_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_dispatches")),
    )
    op.create_index(
        "ix_message_dispatches_recipient_window",
        "message_dispatches",
        ["org_id", "recipient_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_message_dispatches_category_window",
        "message_dispatches",
        ["org_id", "recipient_user_id", "template_category", "created_at"],
        unique=False,
    )

    op.create_table(
        "message_delivery_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("message_dispatch_id", sa.String(length=36), nullable=False),
        sa.Column("connector_key", sa.String(length=30), nullable=False),
        sa.Column("attempt_status", sa.String(length=30), nullable=False),
        sa.Column("provider_message_id", sa.String(length=180), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_dispatch_id"], ["message_dispatches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_message_delivery_attempts")),
    )
    op.create_index(
        "ix_message_delivery_attempts_message",
        "message_delivery_attempts",
        ["message_dispatch_id", "attempted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_message_delivery_attempts_message", table_name="message_delivery_attempts")
    op.drop_table("message_delivery_attempts")

    op.drop_index("ix_message_dispatches_category_window", table_name="message_dispatches")
    op.drop_index("ix_message_dispatches_recipient_window", table_name="message_dispatches")
    op.drop_table("message_dispatches")

    op.drop_index("ix_message_templates_project_active", table_name="message_templates")
    op.drop_table("message_templates")
