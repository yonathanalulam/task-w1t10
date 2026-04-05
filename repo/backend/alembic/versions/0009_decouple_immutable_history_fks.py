"""remove mutable parent foreign keys from immutable history tables

Revision ID: 0009_history_fk_free
Revises: 0008_retention_event_lifecycle
Create Date: 2026-04-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_history_fk_free"
down_revision: Union[str, Sequence[str], None] = "0008_retention_event_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_immutable_triggers(dialect_name: str) -> None:
    if dialect_name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable ON lineage_events")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events")
    elif dialect_name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_update")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable_update")


def _create_immutable_triggers(dialect_name: str) -> None:
    if dialect_name == "postgresql":
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


def _rebuild_history_tables(*, with_mutable_foreign_keys: bool) -> None:
    dialect_name = op.get_bind().dialect.name
    _drop_immutable_triggers(dialect_name)

    def _mutable_reference_column(name: str, target: str):
        if with_mutable_foreign_keys:
            return sa.Column(name, sa.String(length=36), sa.ForeignKey(target, ondelete="SET NULL"), nullable=True)
        return sa.Column(name, sa.String(length=36), nullable=True)

    op.create_table(
        "audit_events_rebuilt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        _mutable_reference_column("project_id", "projects.id"),
        _mutable_reference_column("actor_user_id", "users.id"),
        sa.Column("action_type", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=180), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("detail_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lineage_events_rebuilt",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("org_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        _mutable_reference_column("project_id", "projects.id"),
        _mutable_reference_column("dataset_id", "datasets.id"),
        _mutable_reference_column("itinerary_id", "itineraries.id"),
        _mutable_reference_column("created_by_user_id", "users.id"),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=180), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO audit_events_rebuilt (
            id, org_id, project_id, actor_user_id, action_type, resource_type, resource_id,
            request_method, request_path, status_code, detail_summary, metadata_json, occurred_at
        )
        SELECT
            id, org_id, project_id, actor_user_id, action_type, resource_type, resource_id,
            request_method, request_path, status_code, detail_summary, metadata_json, occurred_at
        FROM audit_events
        """
    )
    op.execute(
        """
        INSERT INTO lineage_events_rebuilt (
            id, org_id, project_id, dataset_id, itinerary_id, created_by_user_id,
            event_type, entity_type, entity_id, payload, occurred_at
        )
        SELECT
            id, org_id, project_id, dataset_id, itinerary_id, created_by_user_id,
            event_type, entity_type, entity_id, payload, occurred_at
        FROM lineage_events
        """
    )

    op.drop_table("audit_events")
    op.drop_table("lineage_events")
    op.rename_table("audit_events_rebuilt", "audit_events")
    op.rename_table("lineage_events_rebuilt", "lineage_events")
    _create_immutable_triggers(dialect_name)


def upgrade() -> None:
    _rebuild_history_tables(with_mutable_foreign_keys=False)


def downgrade() -> None:
    _rebuild_history_tables(with_mutable_foreign_keys=True)
