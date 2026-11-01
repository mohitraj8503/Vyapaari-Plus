"""Unit tests for stock transfer idempotency [BUG-05]."""

import pytest
from app.modules.inventory.models import Branch, StockBatch, StockTransfer
from app.modules.inventory.stock_transfer import StockTransferService


def test_transfer_creation_is_idempotent(db_session):
    # Setup test branches
    source = Branch(id="b1", name="Main Warehouse", code="WH01", is_warehouse=True)
    dest = Branch(id="b2", name="Store 1", code="ST01", is_warehouse=False)
    batch = StockBatch(id="bat1", branch_id="b1", product_id="p1", batch_number="B001", quantity=100)
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "p1", "quantity_dispatched": 10, "unit_cost": 50.0}]

    idempotency_key = "req-uuid-12345"

    t1 = service.create_transfer_request(
        source_branch_id="b1",
        destination_branch_id="b2",
        items=items,
        idempotency_key=idempotency_key,
    )

    t2 = service.create_transfer_request(
        source_branch_id="b1",
        destination_branch_id="b2",
        items=items,
        idempotency_key=idempotency_key,
    )

    # Must return the same transfer without creating a second one
    assert t1.id == t2.id
    assert t1.transfer_number == t2.transfer_number
    assert db_session.query(StockTransfer).count() == 1
