"""Failure-injection tests: assert atomic transaction rollback on mid-operation errors."""

from decimal import Decimal
import pytest
from unittest.mock import patch

from app.core.exceptions import ValidationError
from app.modules.inventory.models import Branch, StockBatch, TransferStatus
from app.modules.inventory.stock_transfer import StockTransferService


def test_dispatch_failure_rolls_back_stock_deduction(db_session):
    source = Branch(id="b_src", name="Central", code="SRC01", is_warehouse=True)
    dest = Branch(id="b_dst", name="Branch", code="DST01", is_warehouse=False)
    batch = StockBatch(
        id="bat_01",
        branch_id="b_src",
        product_id="prod_1",
        batch_number="B1",
        quantity=50,
        purchase_price=Decimal("10.00"),
    )
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "prod_1", "quantity_dispatched": 20, "unit_cost": "10.00"}]
    transfer = service.create_transfer_request("b_src", "b_dst", items)

    # Inject failure right during commit
    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated DB Disk Failure")):
        with pytest.raises(RuntimeError, match="Simulated DB Disk Failure"):
            service.dispatch_transfer(transfer.id)

    # Rollback must leave transfer as DRAFT and stock as 50
    db_session.rollback()
    t_after = service._get_transfer(transfer.id)
    assert t_after.status == TransferStatus.DRAFT
    b_after = db_session.get(StockBatch, "bat_01")
    assert b_after.quantity == 50


def test_receive_failure_rolls_back_destination_stock(db_session):
    source = Branch(id="b_src", name="Central", code="SRC01", is_warehouse=True)
    dest = Branch(id="b_dst", name="Branch", code="DST01", is_warehouse=False)
    batch = StockBatch(
        id="bat_01",
        branch_id="b_src",
        product_id="prod_1",
        batch_number="B1",
        quantity=50,
        purchase_price=Decimal("10.00"),
    )
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)
    items = [{"product_id": "prod_1", "quantity_dispatched": 20, "unit_cost": "10.00"}]
    transfer = service.create_transfer_request("b_src", "b_dst", items)
    service.dispatch_transfer(transfer.id)
    service.start_transit(transfer.id)

    # Inject failure when saving receipt
    with patch.object(db_session, "commit", side_effect=RuntimeError("Network Timeout")):
        with pytest.raises(RuntimeError, match="Network Timeout"):
            service.receive_and_record_delivery(
                transfer.id,
                received_items=[{"item_id": transfer.items[0].id, "quantity_received": 20, "quantity_damaged": 0}],
            )

    db_session.rollback()
    t_after = service._get_transfer(transfer.id)
    assert t_after.status == TransferStatus.IN_TRANSIT
    # Destination must have 0 batches
    dst_batches = db_session.query(StockBatch).filter_by(branch_id="b_dst").all()
    assert len(dst_batches) == 0
