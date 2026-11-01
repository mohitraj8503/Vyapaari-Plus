from datetime import datetime, timedelta

from app.modules.customers.models import CustomerEntryType, CustomerLedgerEntry
from app.modules.inventory.models import StockTransfer, TransferStatus
from app.modules.products.models import Product
from app.modules.suppliers.models import SupplierInvoice


class AlertService:
    def __init__(self, db):
        self.db = db

    def low_stock(self):
        return self.db.query(Product).filter(
            Product.is_active.is_(True),
            Product.current_stock <= Product.reorder_point,
        ).all()

    def overdue_udhaar(self):
        cutoff = datetime.now() - timedelta(days=30)
        return self.db.query(CustomerLedgerEntry).filter(
            CustomerLedgerEntry.entry_type == CustomerEntryType.SALE,
            CustomerLedgerEntry.entry_date < cutoff,
        ).all()

    def overdue_payables(self):
        return self.db.query(SupplierInvoice).filter(
            SupplierInvoice.due_date < datetime.now(),
            SupplierInvoice.amount_paid < SupplierInvoice.total_amount,
        ).all()

    def pending_transfers(self):
        return self.db.query(StockTransfer).filter(
            StockTransfer.status.in_([TransferStatus.DRAFT, TransferStatus.DISPATCHED, TransferStatus.IN_TRANSIT])
        ).all()
