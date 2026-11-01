"""Harden transfer money fields and add transfer idempotency.

Revision ID: 7a2f6e1c4b90
Revises: 4b6a0d2c9f71
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a2f6e1c4b90"
down_revision: str | Sequence[str] | None = "4b6a0d2c9f71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("stock_batches") as batch_op:
        batch_op.alter_column(
            "purchase_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "selling_price",
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )

    with op.batch_alter_table("transfer_items") as batch_op:
        batch_op.alter_column(
            "unit_cost",
            existing_type=sa.Float(),
            type_=sa.Numeric(12, 2),
            existing_nullable=False,
        )

    with op.batch_alter_table("stock_transfers") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(100), nullable=True))
        batch_op.create_index(
            "ix_stock_transfers_idempotency_key",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("stock_transfers") as batch_op:
        batch_op.drop_index("ix_stock_transfers_idempotency_key")
        batch_op.drop_column("idempotency_key")

    with op.batch_alter_table("transfer_items") as batch_op:
        batch_op.alter_column(
            "unit_cost",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Float(),
            existing_nullable=False,
        )

    with op.batch_alter_table("stock_batches") as batch_op:
        batch_op.alter_column(
            "selling_price",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Float(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "purchase_price",
            existing_type=sa.Numeric(12, 2),
            type_=sa.Float(),
            existing_nullable=False,
        )
