import os
import uuid
from pathlib import Path
from typing import Optional

# Keep demo data separate from the main project database.
DEMO_DIR = Path(__file__).resolve().parent
os.environ["DATABASE_URL"] = (
    f"sqlite:///{(DEMO_DIR / 'demo_inventory.db').as_posix()}"
)
os.environ["APP_DEBUG"] = "false"
os.environ["APP_ENV"] = "demo"

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.modules.inventory import models as inventory_models
from app.modules.inventory.models import Branch, StockBatch
from app.modules.inventory.stock_transfer import StockTransferService
from app.modules.inventory.reconciliation import MultiBranchReconciliationEngine

# Initialize the isolated demo database.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vyapaari+ Inventory Transfer Demo",
    description=(
        "Demo API for inter-store stock transfers, transit tracking, "
        "delivery discrepancies, and reconciliation."
    ),
    version="1.0.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_transfer_or_404(db: Session, transfer_id: str):
    transfer = (
        db.query(inventory_models.StockTransfer)
        .filter(inventory_models.StockTransfer.id == transfer_id)
        .first()
    )
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


def serialize_transfer(transfer):
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "source_branch_id": transfer.source_branch_id,
        "destination_branch_id": transfer.destination_branch_id,
        "status": (
            transfer.status.value
            if hasattr(transfer.status, "value")
            else str(transfer.status)
        ),
        "gate_pass": transfer.gate_pass_number,
        "delivery_challan": transfer.delivery_challan_number,
        "vehicle_number": transfer.vehicle_number,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "batch_number": item.batch_number,
                "quantity_dispatched": item.quantity_dispatched,
                "quantity_received": item.quantity_received,
                "quantity_damaged": item.quantity_damaged,
                "unit_cost": item.unit_cost,
            }
            for item in transfer.items
        ],
    }
class TransferItemInput(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_cost: float = Field(ge=0, allow_inf_nan=False)


class TransferInput(BaseModel):
    source_branch_id: str
    destination_branch_id: str
    items: list[TransferItemInput]
    dispatched_by: Optional[str] = "demo-user"
    notes: Optional[str] = "Created through the inventory demo"


class DispatchInput(BaseModel):
    vehicle_number: Optional[str] = "DEMO-001"
    driver_contact: Optional[str] = None


class ReceiptItemInput(BaseModel):
    transfer_item_id: str
    quantity_received: int = Field(ge=0)
    quantity_damaged: int = Field(default=0, ge=0)


class ReceiptInput(BaseModel):
    received_items: list[ReceiptItemInput]
    received_by: str = "demo-receiver"


class TrackingInput(BaseModel):
    event_type: str
    location: Optional[str] = None
    details: Optional[str] = None
    logged_by: str = "demo-user"


class ReconcileInput(BaseModel):
    reconciled_by: str = "demo-auditor"
    remarks: Optional[str] = "Demo reconciliation"


class ApprovalInput(BaseModel):
    approver: str = "demo-manager"
    decision: str
    remarks: Optional[str] = None


@app.get("/")
def home():
    return {
        "application": "Vyapaari+ Inventory Transfer Demo",
        "status": "running",
        "documentation": "/docs",
        "database": "Isolated demo_inventory.db",
        "workflow": [
            "Create transfer",
            "Dispatch stock",
            "Start transit",
            "Record tracking events",
            "Receive delivery",
            "Reconcile discrepancies",
            "Approve or reject reconciliation",
        ],
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/demo/seed")
def seed_demo_data(db: Session = Depends(get_db)):
    """Create two sample branches and stock for demonstration."""
    try:
        source = (
            db.query(Branch)
            .filter(Branch.code == "DEMO-SOURCE")
            .first()
        )
        destination = (
            db.query(Branch)
            .filter(Branch.code == "DEMO-DEST")
            .first()
        )

        if source is None:
            source = Branch(
		id=str(uuid.uuid4()),
                name="Demo Central Store",
                code="DEMO-SOURCE",
                address="Demo Location A",
                is_warehouse=True,
            )
            db.add(source)

        if destination is None:
            destination = Branch(
		id=str(uuid.uuid4()),
                name="Demo City Store",
                code="DEMO-DEST",
                address="Demo Location B",
                is_warehouse=False,
            )
            db.add(destination)

        db.flush()

        batch = (
            db.query(StockBatch)
            .filter(
                StockBatch.branch_id == source.id,
                StockBatch.product_id == "DEMO-RICE-001",
                StockBatch.batch_number == "DEMO-BATCH-001",
            )
            .first()
        )

        if batch is None:
            batch = StockBatch(
		id=str(uuid.uuid4()),
                product_id="DEMO-RICE-001",
                branch_id=source.id,
                batch_number="DEMO-BATCH-001",
                quantity=100,
                purchase_price=40.0,
                selling_price=50.0,
            )
            db.add(batch)

        db.commit()

        return {
            "message": "Demo branches and sample stock are ready",
            "source_branch_id": source.id,
            "destination_branch_id": destination.id,
            "product_id": "DEMO-RICE-001",
            "available_quantity": batch.quantity,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/demo/branches")
def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).order_by(Branch.name).all()
    return [
        {
            "id": branch.id,
            "name": branch.name,
            "code": branch.code,
            "address": branch.address,
        }
        for branch in branches
    ]


@app.get("/demo/stock")
def list_stock(db: Session = Depends(get_db)):
    batches = db.query(StockBatch).order_by(StockBatch.branch_id).all()
    return [
        {
            "id": batch.id,
            "branch_id": batch.branch_id,
            "product_id": batch.product_id,
            "batch_number": batch.batch_number,
            "quantity": batch.quantity,
            "purchase_price": batch.purchase_price,
        }
        for batch in batches
    ]
@app.post("/transfers")
def create_transfer(payload: TransferInput, db: Session = Depends(get_db)):
    try:
        service = StockTransferService(db)
        transfer = service.create_transfer_request(
            source_branch_id=payload.source_branch_id,
            destination_branch_id=payload.destination_branch_id,
            items=[
                {
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity_dispatched": item.quantity,
                    "unit_cost": item.unit_cost,
                }
                for item in payload.items
            ],
            dispatched_by=payload.dispatched_by,
            notes=payload.notes,
        )
        return serialize_transfer(transfer)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/transfers")
def list_transfers(db: Session = Depends(get_db)):
    transfers = (
        db.query(inventory_models.StockTransfer)
        .order_by(inventory_models.StockTransfer.created_at.desc())
        .all()
    )
    return [serialize_transfer(transfer) for transfer in transfers]


@app.get("/transfers/{transfer_id}")
def get_transfer(transfer_id: str, db: Session = Depends(get_db)):
    return serialize_transfer(get_transfer_or_404(db, transfer_id))


@app.post("/transfers/{transfer_id}/dispatch")
def dispatch_transfer(
    transfer_id: str,
    payload: DispatchInput,
    db: Session = Depends(get_db),
):
    try:
        service = StockTransferService(db)
        service.dispatch_transfer(
            transfer_id,
            vehicle_number=payload.vehicle_number,
            driver_contact=payload.driver_contact,
        )
        return serialize_transfer(get_transfer_or_404(db, transfer_id))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/transfers/{transfer_id}/transit")
def start_transit(transfer_id: str, db: Session = Depends(get_db)):
    try:
        StockTransferService(db).start_transit(transfer_id)
        return serialize_transfer(get_transfer_or_404(db, transfer_id))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/transfers/{transfer_id}/tracking")
def record_tracking(
    transfer_id: str,
    payload: TrackingInput,
    db: Session = Depends(get_db),
):
    try:
        service = StockTransferService(db)
        service.record_carrier_event(
            transfer_id,
            event_type=payload.event_type,
            location=payload.location,
            details=payload.details,
            logged_by=payload.logged_by,
        )
        return {"message": "Tracking event recorded"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/transfers/{transfer_id}/tracking")
def get_tracking(transfer_id: str, db: Session = Depends(get_db)):
    get_transfer_or_404(db, transfer_id)
    events = StockTransferService(db).get_tracking_history(transfer_id)
    return [
        {
            "event_type": event.event_type,
            "location": event.location,
            "details": event.details,
            "logged_by": event.logged_by,
            "logged_at": (
                event.logged_at.isoformat() if event.logged_at else None
            ),
        }
        for event in events
    ]
@app.post("/transfers/{transfer_id}/receive")
def receive_transfer(
    transfer_id: str,
    payload: ReceiptInput,
    db: Session = Depends(get_db),
):
    try:
        StockTransferService(db).receive_and_record_delivery(
            transfer_id,
            received_items=[
                {
                    "transfer_item_id": item.transfer_item_id,
                    "quantity_received": item.quantity_received,
                    "quantity_damaged": item.quantity_damaged,
                }
                for item in payload.received_items
            ],
            received_by=payload.received_by,
        )
        return serialize_transfer(get_transfer_or_404(db, transfer_id))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/transfers/{transfer_id}/reconcile")
def reconcile_transfer(
    transfer_id: str,
    payload: ReconcileInput,
    db: Session = Depends(get_db),
):
    try:
        result = MultiBranchReconciliationEngine(db).reconcile_transfer(
            transfer_id,
            reconciled_by=payload.reconciled_by,
            remarks=payload.remarks,
        )
        return {
            "message": "Reconciliation recorded",
            "result": result if isinstance(result, dict) else str(result),
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/transfers/{transfer_id}/approval")
def approve_reconciliation(
    transfer_id: str,
    payload: ApprovalInput,
    db: Session = Depends(get_db),
):
    if payload.decision not in {"APPROVED", "REJECTED"}:
        raise HTTPException(
            status_code=422,
            detail="decision must be APPROVED or REJECTED",
        )

    try:
        result = MultiBranchReconciliationEngine(db).record_approval(
            transfer_id,
            approver=payload.approver,
            decision=payload.decision,
            remarks=payload.remarks,
        )
        return {
            "message": "Approval decision recorded",
            "result": result if isinstance(result, dict) else str(result),
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))