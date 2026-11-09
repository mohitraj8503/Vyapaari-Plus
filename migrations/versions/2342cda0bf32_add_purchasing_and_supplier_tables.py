
"""Add purchasing and supplier tables.

Revision ID: 2342cda0bf32
Revises: 4b6a0d2c9f71
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2342cda0bf32"
down_revision: Union[str, Sequence[str], None] = "4b6a0d2c9f71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create purchasing and supplier tables."""

    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("contact_person", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column(
            "payment_terms",
            sa.Enum("NET_15", "NET_30", "NET_60", "COD", name="paymentterms"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_suppliers_name"), "suppliers", ["name"], unique=False
    )

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("current_stock", sa.Integer(), nullable=False),
        sa.Column("reorder_point", sa.Integer(), nullable=False),
        sa.Column("reorder_quantity", sa.Integer(), nullable=False),
        sa.Column("primary_supplier_id", sa.String(length=36), nullable=True),
        sa.Column("unit_cost", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["primary_supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_products_name"), "products", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_products_primary_supplier_id"),
        "products",
        ["primary_supplier_id"],
        unique=False,
    )
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("po_number", sa.String(length=40), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("order_date", sa.DateTime(), nullable=False),
        sa.Column("expected_delivery_date", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_purchase_orders_po_number"),
        "purchase_orders",
        ["po_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_purchase_orders_supplier_id"),
        "purchase_orders",
        ["supplier_id"],
        unique=False,
    )

    op.create_table(
        "supplier_invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=False),
        sa.Column("invoice_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_supplier_invoices_supplier_id"),
        "supplier_invoices",
        ["supplier_id"],
        unique=False,
    )

    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("grn_number", sa.String(length=40), nullable=False),
        sa.Column("purchase_order_id", sa.String(length=36), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_goods_receipts_grn_number"),
        "goods_receipts",
        ["grn_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_goods_receipts_purchase_order_id"),
        "goods_receipts",
        ["purchase_order_id"],
        unique=False,
    )

    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("purchase_order_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("received_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_purchase_order_items_product_id"),
        "purchase_order_items",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_order_items_purchase_order_id"),
        "purchase_order_items",
        ["purchase_order_id"],
        unique=False,
    )

    op.create_table(
        "supplier_payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_date", sa.DateTime(), nullable=False),
        sa.Column("reference", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["supplier_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_supplier_payments_invoice_id"),
        "supplier_payments",
        ["invoice_id"],
        unique=False,
    )

    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("goods_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_order_item_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goods_receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(
            ["purchase_order_item_id"], ["purchase_order_items.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_goods_receipt_lines_goods_receipt_id"),
        "goods_receipt_lines",
        ["goods_receipt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_goods_receipt_lines_purchase_order_item_id"),
        "goods_receipt_lines",
        ["purchase_order_item_id"],
        unique=False,
    )

    op.create_table(
        "supplier_credit_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=True),
        sa.Column("payment_id", sa.String(length=36), nullable=True),
        sa.Column(
            "entry_type",
            sa.Enum("INVOICE", "PAYMENT", "ADJUSTMENT", name="ledgerentrytype"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.String(length=250), nullable=False),
        sa.Column("entry_date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["supplier_invoices.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["supplier_payments.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_supplier_credit_ledger_invoice_id"),
        "supplier_credit_ledger",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_credit_ledger_payment_id"),
        "supplier_credit_ledger",
        ["payment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_credit_ledger_supplier_id"),
        "supplier_credit_ledger",
        ["supplier_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove purchasing and supplier tables."""

    op.drop_index(
        op.f("ix_supplier_credit_ledger_supplier_id"),
        table_name="supplier_credit_ledger",
    )
    op.drop_index(
        op.f("ix_supplier_credit_ledger_payment_id"),
        table_name="supplier_credit_ledger",
    )
    op.drop_index(
        op.f("ix_supplier_credit_ledger_invoice_id"),
        table_name="supplier_credit_ledger",
    )
    op.drop_table("supplier_credit_ledger")

    op.drop_index(
        op.f("ix_goods_receipt_lines_purchase_order_item_id"),
        table_name="goods_receipt_lines",
    )
    op.drop_index(
        op.f("ix_goods_receipt_lines_goods_receipt_id"),
        table_name="goods_receipt_lines",
    )
    op.drop_table("goods_receipt_lines")

    op.drop_index(
        op.f("ix_supplier_payments_invoice_id"),
        table_name="supplier_payments",
    )
    op.drop_table("supplier_payments")

    op.drop_index(
        op.f("ix_purchase_order_items_purchase_order_id"),
        table_name="purchase_order_items",
    )
    op.drop_index(
        op.f("ix_purchase_order_items_product_id"),
        table_name="purchase_order_items",
    )
    op.drop_table("purchase_order_items")

    op.drop_index(
        op.f("ix_goods_receipts_purchase_order_id"),
        table_name="goods_receipts",
    )
    op.drop_index(
        op.f("ix_goods_receipts_grn_number"),
        table_name="goods_receipts",
    )
    op.drop_table("goods_receipts")

    op.drop_index(
        op.f("ix_supplier_invoices_supplier_id"),
        table_name="supplier_invoices",
    )
    op.drop_table("supplier_invoices")

    op.drop_index(
        op.f("ix_purchase_orders_supplier_id"),
        table_name="purchase_orders",
    )
    op.drop_index(
        op.f("ix_purchase_orders_po_number"),
        table_name="purchase_orders",
    )
    op.drop_table("purchase_orders")

    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(
        op.f("ix_products_primary_supplier_id"),
        table_name="products",
    )
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_suppliers_name"), table_name="suppliers")
    op.drop_table("suppliers")

