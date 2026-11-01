"""Unit tests for stock transfer cancellation and stock restoration [BUG-07]."""

import pytest
from app.core.exceptions import ValidationError
from app.modules.inventory.models import Branch, StockBatch, StockTransfer, TransferStatus
from app.modules.inventory.stock_transfer import StockTransferService


def test_cancel_draft_transfer(db_session):
    source = Branch(id="b1", name="Main Warehouse", code="WH01", is_warehouse=True)
    dest = Branch(id="b2", name="Store 1", code="ST01", is_warehouse=False)
    batch = StockBatch(id="bat1", branch_id="b1", product_id="p1", batch_number="B001", quantity=100)
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "p1", "quantity_dispatched": 10, "unit_cost": 50.0}]

    transfer = service.create_transfer_request("b1", "b2", items)
    assert transfer.status == TransferStatus.DRAFT

    cancelled = service.cancel_transfer(transfer.id, reason="Customer canceled order")
    assert cancelled.status == TransferStatus.CANCELLED
    # Stock should remain untouched at 100
    batch_check = db_session.get(StockBatch, "bat1")
    assert batch_check.quantity == 100


def test_cancel_dispatched_transfer_restores_stock(db_session):
    source = Branch(id="b1", name="Main Warehouse", code="WH01", is_warehouse=True)
    dest = Branch(id="b2", name="Store 1", code="ST01", is_warehouse=False)
    batch = StockBatch(id="bat1", branch_id="b1", product_id="p1", batch_number="B001", quantity=100)
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "p1", "batch_number": "B001", "quantity_dispatched": 25, "unit_cost": 50.0}]

    transfer = service.create_transfer_request("b1", "b2", items)
    service.dispatch_transfer(transfer.id, vehicle_number="MH12AB1234")

    # After dispatch, quantity at source must be 75
    db_session.refresh(batch)
    assert batch.quantity == 75

    # Now cancel
    cancelled = service.cancel_transfer(transfer.id, reason="Truck breakdown")
    assert cancelled.status == TransferStatus.CANCELLED

    # Stock must be restored to 100
    db_session.refresh(batch)
    assert batch.quantity == 100


def test_cannot_cancel_received_transfer(db_session):
    source = Branch(id="b1", name="Main Warehouse", code="WH01", is_warehouse=True)
    dest = Branch(id="b2", name="Store 1", code="ST01", is_warehouse=False)
    batch = StockBatch(id="bat1", branch_id="b1", product_id="p1", batch_number="B001", quantity=100)
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "p1", "batch_number": "B001", "quantity_dispatched": 20, "unit_cost": 50.0}]

    transfer = service.create_transfer_request("b1", "b2", items)
    service.dispatch_transfer(transfer.id)
    service.start_transit(transfer.id)
    service.receive_and_record_delivery(
        transfer.id,
        received_items=[{"item_id": transfer.items[0].id, "quantity_received": 20, "quantity_damaged": 0}],
    )

    with pytest.raises(ValidationError, match="Cannot cancel a transfer with status: RECEIVED"):
        service.cancel_transfer(transfer.id)
