"""Add business, billing, and customer ledger tables.

Revision ID: 8c3d7e1a4b20
Revises: 7a2f6e1c4b90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c3d7e1a4b20"
down_revision: str | Sequence[str] | None = "7a2f6e1c4b90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("gstin", sa.String(15), unique=True),
        sa.Column("state_code", sa.String(2), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("financial_year_start_month", sa.Integer(), nullable=False),
        sa.Column("invoice_prefix", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "invoice_counters",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("next_number", sa.Integer(), nullable=False),
    )
    op.create_table(
        "sales_invoices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(36), sa.ForeignKey("business_profiles.id"), nullable=False),
        sa.Column("customer_id", sa.String(36)),
        sa.Column("invoice_number", sa.String(16), nullable=False),
        sa.Column("financial_year", sa.String(7), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("place_of_supply", sa.String(2), nullable=False),
        sa.Column("taxable_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("round_off", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("idempotency_key", sa.String(100), unique=True, nullable=False),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("business_id", "financial_year", "invoice_number"),
    )
    op.create_table(
        "sales_invoice_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("description", sa.String(150), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False),
        sa.Column("taxable_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(5, 2), nullable=False),
    )
    op.create_table(
        "sales_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(20), unique=True),
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "customer_ledger_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("invoice_id", sa.String(36)),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("entry_date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    for table in (
        "customer_ledger_entries", "customers", "sales_payments",
        "sales_invoice_lines", "sales_invoices", "invoice_counters", "business_profiles",
    ):
        op.drop_table(table)
