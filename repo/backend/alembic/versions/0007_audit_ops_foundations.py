"""add audit lineage retention backup restore foundations

Revision ID: 0007_audit_ops_foundations
Revises: 0006_message_center
Create Date: 2026-04-03 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_audit_ops_foundations"
down_revision: Union[str, Sequence[str], None] = "0006_message_center"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=180), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("detail_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index("ix_audit_events_org_time", "audit_events", ["org_id", "occurred_at"], unique=False)
    op.create_index("ix_audit_events_action", "audit_events", ["org_id", "action_type", "occurred_at"], unique=False)

    op.create_table(
        "lineage_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("dataset_id", sa.String(length=36), nullable=True),
        sa.Column("itinerary_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=180), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lineage_events")),
    )
    op.create_index("ix_lineage_events_org_time", "lineage_events", ["org_id", "occurred_at"], unique=False)
    op.create_index(
        "ix_lineage_events_org_scope",
        "lineage_events",
        ["org_id", "project_id", "dataset_id", "itinerary_id", "event_type", "occurred_at"],
        unique=False,
    )

    op.create_table(
        "retention_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("itinerary_retention_days", sa.Integer(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("itinerary_retention_days >= 30", name="ck_retention_policy_days_minimum"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_policies")),
        sa.UniqueConstraint("org_id", name="uq_retention_policies_org_id"),
    )

    op.create_table(
        "retention_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("initiated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("deleted_itinerary_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_runs")),
    )
    op.create_index("ix_retention_runs_org_started", "retention_runs", ["org_id", "started_at"], unique=False)

    op.create_table(
        "backup_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("initiated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("trigger_kind", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("backup_file_name", sa.String(length=255), nullable=True),
        sa.Column("backup_file_path", sa.String(length=500), nullable=True),
        sa.Column("encrypted_size_bytes", sa.Integer(), nullable=True),
        sa.Column("rotated_file_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backup_runs")),
    )
    op.create_index("ix_backup_runs_org_started", "backup_runs", ["org_id", "started_at"], unique=False)

    op.create_table(
        "restore_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("initiated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("backup_file_name", sa.String(length=255), nullable=False),
        sa.Column("restored_table_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restore_runs")),
    )
    op.create_index("ix_restore_runs_org_started", "restore_runs", ["org_id", "started_at"], unique=False)

    bind = op.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_immutable_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Immutable table % cannot be %', TG_TABLE_NAME, TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_events_immutable
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_immutable_mutation();
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_lineage_events_immutable
            BEFORE UPDATE OR DELETE ON lineage_events
            FOR EACH ROW EXECUTE FUNCTION prevent_immutable_mutation();
            """
        )
    elif dialect_name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_audit_events_immutable_update
            BEFORE UPDATE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table audit_events cannot be UPDATE');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_events_immutable_delete
            BEFORE DELETE ON audit_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table audit_events cannot be DELETE');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_lineage_events_immutable_update
            BEFORE UPDATE ON lineage_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be UPDATE');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_lineage_events_immutable_delete
            BEFORE DELETE ON lineage_events
            BEGIN
                SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be DELETE');
            END;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable ON lineage_events")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events")
        op.execute("DROP FUNCTION IF EXISTS prevent_immutable_mutation")
    elif dialect_name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_update")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable_update")

    op.drop_index("ix_restore_runs_org_started", table_name="restore_runs")
    op.drop_table("restore_runs")

    op.drop_index("ix_backup_runs_org_started", table_name="backup_runs")
    op.drop_table("backup_runs")

    op.drop_index("ix_retention_runs_org_started", table_name="retention_runs")
    op.drop_table("retention_runs")

    op.drop_table("retention_policies")

    op.drop_index("ix_lineage_events_org_scope", table_name="lineage_events")
    op.drop_index("ix_lineage_events_org_time", table_name="lineage_events")
    op.drop_table("lineage_events")

    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_org_time", table_name="audit_events")
    op.drop_table("audit_events")
