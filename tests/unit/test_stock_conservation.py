"""Conservation-invariant test for multi-store transfers: no stock created or destroyed."""

from decimal import Decimal
import pytest
from app.modules.inventory.models import Branch, StockBatch, TransferStatus
from app.modules.inventory.stock_transfer import StockTransferService


def test_stock_conservation_invariant_across_transfer_lifecycle(db_session):
    source = Branch(id="b_src", name="Central Depo", code="DEP01", is_warehouse=True)
    dest = Branch(id="b_dst", name="Retail Store", code="RET01", is_warehouse=False)

    initial_src_qty = 500
    batch = StockBatch(
        id="batch_init",
        branch_id="b_src",
        product_id="prod_rice",
        batch_number="BATCH-RICE-01",
        quantity=initial_src_qty,
        purchase_price=Decimal("45.00"),
    )
    db_session.add_all([source, dest, batch])
    db_session.commit()

    service = StockTransferService(db_session)

    # 1. Create transfer
    transfer_qty = 150
    items = [{"product_id": "prod_rice", "quantity_dispatched": transfer_qty, "unit_cost": "45.00"}]
    transfer = service.create_transfer_request("b_src", "b_dst", items)

    # Invariant in DRAFT: All stock still at source
    src_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_src").all())
    dst_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_dst").all())
    assert src_qty == initial_src_qty
    assert dst_qty == 0

    # 2. Dispatch
    service.dispatch_transfer(transfer.id, vehicle_number="MH04XY9999")
    src_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_src").all())
    dst_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_dst").all())
    in_transit_qty = transfer_qty
    # Conservation: source + in_transit = initial
    assert src_qty + in_transit_qty == initial_src_qty
    assert dst_qty == 0

    # 3. In Transit
    service.start_transit(transfer.id)

    # 4. Receive with partial delivery (120 good, 20 damaged, 10 missing)
    good_qty = 120
    damaged_qty = 20
    missing_qty = 10
    assert good_qty + damaged_qty + missing_qty == transfer_qty

    service.receive_and_record_delivery(
        transfer.id,
        received_items=[
            {
                "item_id": transfer.items[0].id,
                "quantity_received": good_qty,
                "quantity_damaged": damaged_qty,
            }
        ],
        received_by="store_mgr",
    )

    src_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_src").all())
    dst_qty = sum(b.quantity for b in db_session.query(StockBatch).filter_by(branch_id="b_dst").all())
    damaged_accounted = transfer.items[0].quantity_damaged
    missing_accounted = (
        transfer.items[0].quantity_dispatched
        - transfer.items[0].quantity_received
        - transfer.items[0].quantity_damaged
    )

    # TOTAL CONSERVATION: source + destination + damaged + missing == initial
    total_accounted = src_qty + dst_qty + damaged_accounted + missing_accounted
    assert total_accounted == initial_src_qty
    assert dst_qty == good_qty
    assert damaged_accounted == damaged_qty
    assert missing_accounted == missing_qty
