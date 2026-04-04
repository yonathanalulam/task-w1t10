"""add explicit audit and lineage retention columns

Revision ID: 0008_retention_event_lifecycle
Revises: 0007_audit_ops_foundations
Create Date: 2026-04-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_retention_event_lifecycle"
down_revision: Union[str, Sequence[str], None] = "0007_audit_ops_foundations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("retention_policies") as batch_op:
        batch_op.add_column(sa.Column("audit_retention_days", sa.Integer(), nullable=False, server_default="365"))
        batch_op.add_column(sa.Column("lineage_retention_days", sa.Integer(), nullable=False, server_default="365"))

    with op.batch_alter_table("retention_runs") as batch_op:
        batch_op.add_column(sa.Column("deleted_audit_event_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("deleted_lineage_event_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("retention_runs") as batch_op:
        batch_op.drop_column("deleted_lineage_event_count")
        batch_op.drop_column("deleted_audit_event_count")

    with op.batch_alter_table("retention_policies") as batch_op:
        batch_op.drop_column("lineage_retention_days")
        batch_op.drop_column("audit_retention_days")
